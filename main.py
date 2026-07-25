from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3, json, os, time, secrets, asyncio
from concurrent.futures import ThreadPoolExecutor
_backup_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="backup")
from pathlib import Path

app = FastAPI(docs_url=None, redoc_url=None)

# CORS: restrict to configured site origin(s) when provided, else allow all.
# ALLOWED_ORIGINS = "https://your-shop.com,https://www.your-shop.com"
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])

ADMIN_PASS   = os.getenv("ADMIN_PASS", "admin2025")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_ID      = os.getenv("GIST_ID", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "sashanazarenko2051-source/nice-shopping")
# Committing products.json back to the git repo triggers a Render auto-deploy,
# which wipes the ephemeral SQLite DB (losing orders/reviews). Off by default —
# persistence goes through the Gist instead. Set AUTO_COMMIT=1 to re-enable.
AUTO_COMMIT  = os.getenv("AUTO_COMMIT", "").lower() in ("1", "true", "yes")
TOKEN_TTL    = int(os.getenv("TOKEN_TTL", str(7 * 24 * 3600)))   # admin session lifetime
MAX_BODY     = int(os.getenv("MAX_BODY", str(32 * 1024 * 1024)))  # 32 MB request cap (base64 photos)
_tokens: dict = {}                # token -> issued_ts
_login_attempts: dict = {}        # ip -> (count, window_start_ts)
security = HTTPBearer(auto_error=False)

if ADMIN_PASS == "admin2025":
    print("[SECURITY] WARNING: ADMIN_PASS is still the default 'admin2025'. "
          "Set a strong ADMIN_PASS env var in the Render dashboard.")


@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl:
        try:
            if int(cl) > MAX_BODY:
                return JSONResponse({"detail": "Payload too large"}, status_code=413)
        except ValueError:
            pass
    return await call_next(request)

# ── SQLite ────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "shop.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders   (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews  (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tokens   (token TEXT PRIMARY KEY, ts INTEGER NOT NULL);
    """)
    conn.commit(); conn.close()

def _load_tokens():
    conn = get_db()
    rows = conn.execute("SELECT token, ts FROM tokens").fetchall()
    now = int(time.time())
    expired = []
    for r in rows:
        if now - r["ts"] < TOKEN_TTL:
            _tokens[r["token"]] = r["ts"]
        else:
            expired.append(r["token"])
    for t in expired:
        conn.execute("DELETE FROM tokens WHERE token = ?", (t,))
    if expired:
        conn.commit()
    conn.close()

init_db()
_load_tokens()

# ── Gist backup ───────────────────────────────────────────
def _gist_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "nice-shopping"}

def _insert_products(products):
    conn = get_db()
    conn.execute("DELETE FROM products")
    for i, p in enumerate(products):
        pid = int(p.get("id") or int(time.time() * 1000) + i)
        p["id"] = pid
        conn.execute("INSERT INTO products (id, data) VALUES (?, ?)", (pid, json.dumps(p)))
    conn.commit(); conn.close()

def _gist_fetch_file(filename):
    """Fetch and parse a single file from the configured Gist (via raw_url to avoid truncation)."""
    if not (GITHUB_TOKEN and GIST_ID):
        return None
    try:
        import urllib.request
        req = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}", headers=_gist_headers())
        meta = json.loads(urllib.request.urlopen(req, timeout=15).read())
        info = meta.get("files", {}).get(filename, {})
        raw_url = info.get("raw_url", "")
        if not raw_url:
            return None
        raw_req = urllib.request.Request(raw_url, headers={"User-Agent": "nice-shopping"})
        return json.loads(urllib.request.urlopen(raw_req, timeout=15).read())
    except Exception as e:
        print(f"[Gist] fetch {filename} error: {e}")
        return None


def _gist_patch_files(files: dict):
    """PATCH one or more files into the Gist. files = {filename: content_str}"""
    if not (GITHUB_TOKEN and GIST_ID):
        return
    try:
        import urllib.request
        body = json.dumps({"files": {n: {"content": c} for n, c in files.items()}}).encode()
        req = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}",
                                     data=body, headers=_gist_headers(), method="PATCH")
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"[Gist] patch error: {e}")


def _backup_orders():
    """Snapshot all orders to the Gist so they survive DB resets on redeploy/spin-down."""
    conn = get_db()
    rows = conn.execute("SELECT data FROM orders ORDER BY id ASC").fetchall()
    conn.close()
    data = [json.loads(r["data"]) for r in rows]
    _gist_patch_files({"orders.json": json.dumps(data, ensure_ascii=False, indent=2)})


def _backup_reviews():
    """Snapshot all reviews to the Gist so they survive DB resets on redeploy/spin-down."""
    conn = get_db()
    rows = conn.execute("SELECT data FROM reviews ORDER BY id ASC").fetchall()
    conn.close()
    data = [json.loads(r["data"]) for r in rows]
    _gist_patch_files({"reviews.json": json.dumps(data, ensure_ascii=False, indent=2)})


def _restore_orders_reviews():
    """On start: if the (ephemeral) SQLite tables are empty, restore from the Gist backup."""
    conn = get_db()
    o_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    r_count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    conn.close()

    if o_count == 0:
        orders = _gist_fetch_file("orders.json")
        if orders:
            conn = get_db()
            for o in orders:
                conn.execute("INSERT INTO orders (data) VALUES (?)", (json.dumps(o, ensure_ascii=False),))
            conn.commit(); conn.close()
            print(f"[Gist] Restored {len(orders)} orders")

    if r_count == 0:
        reviews = _gist_fetch_file("reviews.json")
        if reviews:
            conn = get_db()
            for rv in reviews:
                conn.execute("INSERT INTO reviews (data) VALUES (?)", (json.dumps(rv, ensure_ascii=False),))
            conn.commit(); conn.close()
            print(f"[Gist] Restored {len(reviews)} reviews")


def _gist_load():
    """На старті: якщо SQLite порожній — завантажити товари з Gist, потім з products.json"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    if count > 0:
        return

    # 1) Try Gist — if it responds (even with []), trust it and skip fallback
    if GITHUB_TOKEN and GIST_ID:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://api.github.com/gists/{GIST_ID}",
                headers=_gist_headers()
            )
            meta = json.loads(urllib.request.urlopen(req, timeout=15).read())
            file_info = meta.get("files", {}).get("products.json", {})
            raw_url = file_info.get("raw_url", "")
            if raw_url:
                raw_req = urllib.request.Request(raw_url, headers={"User-Agent": "nice-shopping"})
                products = json.loads(urllib.request.urlopen(raw_req, timeout=15).read())
                if isinstance(products, list):
                    if products:
                        _insert_products(products)
                        print(f"[Gist] Loaded {len(products)} products")
                    else:
                        print("[Gist] products.json is empty — no products loaded")
                    return  # Gist responded successfully, do not fall through to file fallback
        except Exception as e:
            print(f"[Gist] Load error: {e}")

    # 2) Fallback: products.json in git repo (only used when Gist is unavailable)
    try:
        fb = Path("products.json")
        if fb.exists():
            products = json.loads(fb.read_text(encoding="utf-8"))
            if products:
                _insert_products(products)
                print(f"[Fallback] Loaded {len(products)} products from products.json")
    except Exception as e:
        print(f"[Fallback] Load error: {e}")

def _slim_products(products):
    """Strip base64 images (keep only URL images) to keep git file small"""
    result = []
    for p in products:
        s = dict(p)
        if s.get("imageUrl", "").startswith("data:"):
            s["imageUrl"] = ""
        result.append(s)
    return result

def _github_commit(products):
    """Commit products.json directly to git repo so it survives every deploy"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    try:
        import urllib.request, base64 as b64
        slim = _slim_products(products)
        content = json.dumps(slim, ensure_ascii=False, indent=2)
        encoded = b64.b64encode(content.encode()).decode()
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/products.json"
        headers = {**_gist_headers(), "Content-Type": "application/json"}
        # Get current file SHA
        sha = ""
        try:
            req = urllib.request.Request(api_url, headers=headers)
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            sha = resp.get("sha", "")
        except Exception:
            pass
        body = json.dumps({
            "message": f"chore: update products ({len(slim)} items)",
            "content": encoded,
            **({"sha": sha} if sha else {}),
            "committer": {"name": "Shop Bot", "email": "bot@shop.local"}
        }).encode()
        req = urllib.request.Request(api_url, data=body, headers=headers, method="PUT")
        urllib.request.urlopen(req, timeout=30)
        print(f"[GitHub] Committed {len(slim)} products to repo")
    except Exception as e:
        print(f"[GitHub] Commit error: {e}")

def _gist_save(products):
    """Зберегти товари в Gist + комітити products.json в git-репо"""
    # 1) Always update local file
    try:
        Path("products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[File] Save error: {e}")

    # 2) Optionally commit slim version to git repo. Disabled by default because a repo
    #    commit triggers a Render auto-deploy that wipes the DB (and thus orders/reviews).
    #    Product persistence is handled by the Gist backup below instead.
    if AUTO_COMMIT:
        _github_commit(products)

    if not GITHUB_TOKEN or not GIST_ID:
        return
    try:
        import urllib.request
        body = json.dumps({
            "files": {"products.json": {"content": json.dumps(products, ensure_ascii=False, indent=2)}}
        }).encode()
        req = urllib.request.Request(
            f"https://api.github.com/gists/{GIST_ID}",
            data=body, headers=_gist_headers(), method="PATCH"
        )
        urllib.request.urlopen(req, timeout=12)
        print(f"[Gist] Saved {len(products)} products")
    except Exception as e:
        print(f"[Gist] Save error: {e}")

_gist_load()
_restore_orders_reviews()

# ── Auth ──────────────────────────────────────────────────
def require_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(status_code=401, detail="Unauthorized")
    issued = _tokens.get(creds.credentials)
    if issued is None or int(time.time()) - issued > TOKEN_TTL:
        # expired or unknown → drop it
        if creds.credentials in _tokens:
            _tokens.pop(creds.credentials, None)
            conn = get_db()
            conn.execute("DELETE FROM tokens WHERE token = ?", (creds.credentials,))
            conn.commit(); conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    return creds.credentials


def _client_ip(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def _login_allowed(ip: str) -> bool:
    """Simple 5-minute sliding window: max 8 failed attempts per IP."""
    now = time.time()
    count, start = _login_attempts.get(ip, (0, now))
    if now - start > 300:
        return True
    return count < 8


def _record_login_fail(ip: str):
    now = time.time()
    count, start = _login_attempts.get(ip, (0, now))
    if now - start > 300:
        count, start = 0, now
    _login_attempts[ip] = (count + 1, start)


@app.post("/api/admin/login")
async def admin_login(req: Request):
    ip = _client_ip(req)
    if not _login_allowed(ip):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")
    password = str(body.get("password") or "")
    if secrets.compare_digest(password, ADMIN_PASS):
        _login_attempts.pop(ip, None)
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        _tokens[token] = now
        conn = get_db()
        conn.execute("INSERT OR REPLACE INTO tokens (token, ts) VALUES (?, ?)", (token, now))
        conn.commit(); conn.close()
        return {"token": token}
    _record_login_fail(ip)
    raise HTTPException(status_code=401, detail="Invalid password")

# ── Products ──────────────────────────────────────────────
@app.get("/api/products")
def get_products():
    conn = get_db()
    rows = conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()
    conn.close()
    return [json.loads(r["data"]) for r in rows]

async def _json_body(req: Request):
    try:
        return await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

@app.put("/api/products")
async def set_all_products(req: Request, background_tasks: BackgroundTasks,
                           token: str = Depends(require_admin)):
    products = await _json_body(req)
    if not isinstance(products, list):
        raise HTTPException(status_code=400, detail="Expected a list of products")
    conn = get_db()
    conn.execute("DELETE FROM products")
    for i, p in enumerate(products):
        if not isinstance(p, dict):
            continue
        pid = int(p.get("id") or int(time.time() * 1000) + i)
        p["id"] = pid
        conn.execute("INSERT INTO products (id, data) VALUES (?, ?)", (pid, json.dumps(p, ensure_ascii=False)))
    conn.commit(); conn.close()
    background_tasks.add_task(_gist_save, products)
    return {"ok": True, "count": len(products)}

@app.post("/api/products/one")
async def add_one_product(req: Request, background_tasks: BackgroundTasks,
                          token: str = Depends(require_admin)):
    data = await _json_body(req)
    if not isinstance(data, dict) or not str(data.get("name") or "").strip():
        raise HTTPException(status_code=400, detail="Product name required")
    pid = int(data.get("id") or int(time.time() * 1000))
    data["id"] = pid
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO products (id, data) VALUES (?, ?)", (pid, json.dumps(data, ensure_ascii=False)))
    conn.commit()
    products = [json.loads(r["data"]) for r in
                conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()]
    conn.close()
    background_tasks.add_task(_gist_save, products)
    return {"ok": True, "id": pid}

@app.put("/api/products/{pid}")
async def update_one_product(pid: int, req: Request, background_tasks: BackgroundTasks,
                             token: str = Depends(require_admin)):
    data = await _json_body(req)
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Invalid product")
    data["id"] = pid
    conn = get_db()
    row = conn.execute("SELECT id FROM products WHERE id = ?", (pid,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    conn.execute("UPDATE products SET data = ? WHERE id = ?", (json.dumps(data, ensure_ascii=False), pid))
    conn.commit()
    products = [json.loads(r["data"]) for r in
                conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()]
    conn.close()
    background_tasks.add_task(_gist_save, products)
    return {"ok": True}

@app.post("/api/products/sync-file")
async def sync_products_file(token: str = Depends(require_admin)):
    """Write current SQLite products to products.json on disk (survives until next deploy)"""
    conn = get_db()
    rows = conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()
    conn.close()
    products = [json.loads(r["data"]) for r in rows]
    Path("products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "count": len(products)}

@app.delete("/api/products/{pid}")
def delete_product(pid: int, background_tasks: BackgroundTasks,
                   token: str = Depends(require_admin)):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    products = [json.loads(r["data"]) for r in
                conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()]
    conn.close()
    background_tasks.add_task(_gist_save, products)
    return {"ok": True}

# ── Orders ────────────────────────────────────────────────
@app.get("/api/orders")
def get_orders(background_tasks: BackgroundTasks, token: str = Depends(require_admin)):
    conn = get_db()
    rows = conn.execute("SELECT id, data FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = json.loads(r["data"]); d["_id"] = r["id"]; result.append(d)
    background_tasks.add_task(_backup_orders)  # keep Gist in sync on every admin fetch
    return result

@app.post("/api/orders")
async def create_order(req: Request, background_tasks: BackgroundTasks):
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid order")
    items = body.get("items", [])
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="Empty order")
    if len(items) > 200:
        raise HTTPException(status_code=400, detail="Too many items")
    conn = get_db()
    conn.execute("INSERT INTO orders (data) VALUES (?)", (json.dumps(body, ensure_ascii=False),))

    # Decrement stock for each ordered item
    if items:
        prod_rows = conn.execute("SELECT id, data FROM products").fetchall()
        updated = False
        for item in items:
            item_name = item.get("name", "")
            try:
                item_qty = max(1, int(item.get("qty", 1)))
            except (ValueError, TypeError):
                item_qty = 1
            for row in prod_rows:
                p = json.loads(row["data"])
                if p.get("name") == item_name:
                    p["stock"] = max(0, int(p.get("stock") or 0) - item_qty)
                    conn.execute("UPDATE products SET data = ? WHERE id = ?",
                                 (json.dumps(p), row["id"]))
                    updated = True
                    break
        if updated:
            all_products = [json.loads(r["data"]) for r in
                            conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()]
            background_tasks.add_task(_gist_save, all_products)

    conn.commit()
    conn.close()
    # Backup synchronously in thread pool — waits up to 8s before returning success.
    # This guarantees the order survives a Render free-tier spin-down restart.
    loop = asyncio.get_event_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_backup_executor, _backup_orders), timeout=8)
    except Exception as e:
        print(f"[Backup] Orders backup error (order saved to DB): {e}")
    return {"ok": True}

@app.delete("/api/orders/{oid}")
def delete_order_api(oid: int, background_tasks: BackgroundTasks,
                     token: str = Depends(require_admin)):
    conn = get_db()
    # Restore stock before deleting
    row = conn.execute("SELECT data FROM orders WHERE id = ?", (oid,)).fetchone()
    if row:
        order = json.loads(row["data"])
        items = order.get("items", [])
        if items:
            prod_rows = conn.execute("SELECT id, data FROM products").fetchall()
            updated = False
            for item in items:
                item_name = item.get("name", "")
                try:
                    item_qty = max(1, int(item.get("qty", 1)))
                except (ValueError, TypeError):
                    item_qty = 1
                for pr in prod_rows:
                    p = json.loads(pr["data"])
                    if p.get("name") == item_name:
                        p["stock"] = int(p.get("stock") or 0) + item_qty
                        conn.execute("UPDATE products SET data = ? WHERE id = ?",
                                     (json.dumps(p), pr["id"]))
                        updated = True
                        break
            if updated:
                all_products = [json.loads(r["data"]) for r in
                                conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()]
                background_tasks.add_task(_gist_save, all_products)
    conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
    conn.commit(); conn.close()
    background_tasks.add_task(_backup_orders)  # fire-and-forget is fine for delete
    return {"ok": True}

# ── Reviews ───────────────────────────────────────────────
@app.get("/api/reviews")
def get_reviews():
    conn = get_db()
    rows = conn.execute("SELECT data FROM reviews ORDER BY id DESC").fetchall()
    conn.close()
    return [json.loads(r["data"]) for r in rows]

@app.post("/api/reviews")
async def create_review(req: Request, background_tasks: BackgroundTasks):
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid review")
    # Sanitise / bound the customer-supplied fields
    name = str(body.get("name") or "").strip()[:60]
    text = str(body.get("text") or "").strip()[:1000]
    try:
        rating = int(body.get("rating") or 0)
    except (TypeError, ValueError):
        rating = 0
    rating = max(1, min(5, rating))
    if not name or not text:
        raise HTTPException(status_code=400, detail="Name and text required")
    try:
        ts = int(body.get("ts") or int(time.time() * 1000))
    except (TypeError, ValueError):
        ts = int(time.time() * 1000)
    review = {"name": name, "rating": rating, "text": text, "ts": ts}
    conn = get_db()
    conn.execute("INSERT INTO reviews (data) VALUES (?)", (json.dumps(review, ensure_ascii=False),))
    conn.commit(); conn.close()
    loop = asyncio.get_event_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_backup_executor, _backup_reviews), timeout=8)
    except Exception as e:
        print(f"[Backup] Reviews backup error (review saved to DB): {e}")
    return {"ok": True}

# ── Static files ──────────────────────────────────────────
BLOCKED = {"main.py", "shop.db", "requirements.txt", "render.yaml", "products.json"}
BLOCKED_SUFFIXES = (".py", ".db", ".db-wal", ".db-shm")
_BASE_DIR = Path.cwd().resolve()

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    if not full_path:
        return FileResponse("index.html")

    # Resolve and confine to the app directory (blocks ../ traversal)
    candidate = (_BASE_DIR / full_path).resolve()
    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        return FileResponse("index.html")

    name = candidate.name
    if name in BLOCKED or name.startswith(".") or name.endswith(BLOCKED_SUFFIXES):
        raise HTTPException(status_code=404)

    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse("index.html")
