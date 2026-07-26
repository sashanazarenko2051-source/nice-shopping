from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3, json, os, time, secrets, asyncio, hmac, hashlib
from concurrent.futures import ThreadPoolExecutor
_backup_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="backup")
from pathlib import Path

app = FastAPI(docs_url=None, redoc_url=None)

# CORS: restrict to configured site origin(s) when provided, else allow all.
# ALLOWED_ORIGINS = "https://your-shop.com,https://www.your-shop.com"
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

ADMIN_PASS   = os.getenv("ADMIN_PASS", "admin2025")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_ID      = os.getenv("GIST_ID", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "sashanazarenko2051-source/nice-shopping")
# Committing products.json back to the git repo triggers a Render auto-deploy,
# which wipes the ephemeral SQLite DB (losing orders/reviews). Off by default —
# persistence goes through the Gist instead. Set AUTO_COMMIT=1 to re-enable.
AUTO_COMMIT  = os.getenv("AUTO_COMMIT", "").lower() in ("1", "true", "yes")
MAX_BODY     = int(os.getenv("MAX_BODY", str(32 * 1024 * 1024)))  # 32 MB request cap (base64 photos)
_login_attempts: dict = {}        # ip -> (count, window_start_ts)
# Stateless HMAC token — derived from password, survives restarts without DB
_ADMIN_TOKEN = hmac.new(
    hashlib.sha256(ADMIN_PASS.encode()).digest(),
    b"ns-admin-session-v1", hashlib.sha256
).hexdigest()
_rate_store: dict = {}            # key -> (count, window_start_ts)
security = HTTPBearer(auto_error=False)

def _rate_check(key: str, max_count: int, window_sec: int) -> bool:
    """Generic sliding-window rate limiter. Returns False when limit exceeded."""
    now = time.time()
    count, start = _rate_store.get(key, (0, now))
    if now - start > window_sec:
        _rate_store[key] = (1, now)
        return True
    if count >= max_count:
        return False
    _rate_store[key] = (count + 1, start)
    return True

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

@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https://translate.googleapis.com; "
        "frame-ancestors 'none';"
    )
    return response

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

init_db()

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

def _gist_fetch_file(filename, retries=3):
    """Fetch and parse a single file from the Gist. Retries up to `retries` times."""
    if not (GITHUB_TOKEN and GIST_ID):
        return None
    import urllib.request
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}", headers=_gist_headers())
            meta = json.loads(urllib.request.urlopen(req, timeout=15).read())
            info = meta.get("files", {}).get(filename, {})
            raw_url = info.get("raw_url", "")
            if not raw_url:
                return None
            raw_req = urllib.request.Request(raw_url, headers={"User-Agent": "nice-shopping"})
            return json.loads(urllib.request.urlopen(raw_req, timeout=15).read())
        except Exception as e:
            print(f"[Gist] fetch {filename} attempt {attempt} error: {e}")
            if attempt < retries:
                time.sleep(2)
    return None


def _github_fetch_raw(filename):
    """Read a file from the public GitHub repo without authentication."""
    if not GITHUB_REPO:
        return None
    import urllib.request
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/{filename}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nice-shopping"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        print(f"[GitHub raw] Loaded {filename}")
        return data
    except Exception as e:
        print(f"[GitHub raw] fetch {filename} error: {e}")
        return None


def _github_commit_file(filename, content_str):
    """Commit any data file to the GitHub repo (must be in render.yaml ignoredFiles)."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    try:
        import urllib.request, base64 as b64
        encoded = b64.b64encode(content_str.encode()).decode()
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        headers = {**_gist_headers(), "Content-Type": "application/json"}
        sha = ""
        try:
            req = urllib.request.Request(api_url, headers=headers)
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            sha = resp.get("sha", "")
        except Exception:
            pass
        body = json.dumps({
            "message": f"chore: update {filename}",
            "content": encoded,
            **({"sha": sha} if sha else {}),
            "committer": {"name": "Shop Bot", "email": "bot@shop.local"}
        }).encode()
        req = urllib.request.Request(api_url, data=body, headers=headers, method="PUT")
        urllib.request.urlopen(req, timeout=20)
        print(f"[GitHub] Committed {filename}")
    except Exception as e:
        print(f"[GitHub] Commit {filename} error: {e}")


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
    """Snapshot orders to Gist + GitHub repo."""
    conn = get_db()
    rows = conn.execute("SELECT data FROM orders ORDER BY id ASC").fetchall()
    conn.close()
    data = [json.loads(r["data"]) for r in rows]
    content = json.dumps(data, ensure_ascii=False, indent=2)
    _gist_patch_files({"orders.json": content})
    _github_commit_file("orders.json", content)


def _backup_reviews():
    """Snapshot reviews to Gist + GitHub repo."""
    conn = get_db()
    rows = conn.execute("SELECT data FROM reviews ORDER BY id ASC").fetchall()
    conn.close()
    data = [json.loads(r["data"]) for r in rows]
    content = json.dumps(data, ensure_ascii=False, indent=2)
    _gist_patch_files({"reviews.json": content})
    _github_commit_file("reviews.json", content)


def _fetch_with_fallback(filename):
    """Try Gist → GitHub repo raw → local file."""
    # 1. Gist
    data = _gist_fetch_file(filename)
    if isinstance(data, list):
        return data
    # 2. GitHub raw (no auth needed for public repo)
    data = _github_fetch_raw(filename)
    if isinstance(data, list):
        return data
    # 3. Local file
    try:
        fb = Path(filename)
        if fb.exists():
            data = json.loads(fb.read_text(encoding="utf-8"))
            if isinstance(data, list):
                print(f"[Local] Loaded {filename}")
                return data
    except Exception as e:
        print(f"[Local] {filename} error: {e}")
    return None


def _restore_orders_reviews():
    """On start: restore orders/reviews from Gist → GitHub repo → local file."""
    conn = get_db()
    o_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    r_count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    conn.close()

    if o_count == 0:
        orders = _fetch_with_fallback("orders.json")
        if orders:
            conn = get_db()
            for o in orders:
                conn.execute("INSERT INTO orders (data) VALUES (?)", (json.dumps(o, ensure_ascii=False),))
            conn.commit(); conn.close()
            print(f"[Restore] {len(orders)} orders")

    if r_count == 0:
        reviews = _fetch_with_fallback("reviews.json")
        if reviews:
            conn = get_db()
            for rv in reviews:
                conn.execute("INSERT INTO reviews (data) VALUES (?)", (json.dumps(rv, ensure_ascii=False),))
            conn.commit(); conn.close()
            print(f"[Restore] {len(reviews)} reviews")


def _gist_load():
    """На старті: завантажити товари з Gist → GitHub repo → local file."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    if count > 0:
        return

    products = _fetch_with_fallback("products.json")
    if products:
        _insert_products(products)
        print(f"[Startup] Loaded {len(products)} products")

def _slim_products(products):
    """Strip sensitive/heavy fields before committing to the public git repo."""
    result = []
    for p in products:
        s = dict(p)
        # Remove base64 images (too large for git, use URL instead)
        if s.get("imageUrl", "").startswith("data:"):
            s["imageUrl"] = ""
        if "images" in s:
            s["images"] = [i for i in s.get("images", []) if not str(i).startswith("data:")]
        # Remove purchase price — internal business data, must not be public
        s.pop("pPurchase", None)
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

def _gist_save_fast(products):
    """Save products to local file + Gist only (fast, ~1-3s). No GitHub commit."""
    try:
        Path("products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[File] Save error: {e}")

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


def _gist_save(products):
    """Зберегти товари: локальний файл + Gist + git repo (три шари надійності)."""
    _gist_save_fast(products)
    _github_commit(products)


def _backup_all():
    """Save products + orders + reviews to Gist in ONE API call. Fast, atomic."""
    conn = get_db()
    prod_rows = conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()
    ord_rows  = conn.execute("SELECT data FROM orders  ORDER BY id ASC").fetchall()
    rev_rows  = conn.execute("SELECT data FROM reviews ORDER BY id ASC").fetchall()
    conn.close()
    products = [json.loads(r["data"]) for r in prod_rows]
    orders   = [json.loads(r["data"]) for r in ord_rows]
    reviews  = [json.loads(r["data"]) for r in rev_rows]
    # local file backup
    try:
        Path("products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[File] Save error: {e}")
    # single Gist PATCH — 3 files at once, much faster than 3 separate calls
    _gist_patch_files({
        "products.json": json.dumps(products, ensure_ascii=False, indent=2),
        "orders.json":   json.dumps(orders,   ensure_ascii=False, indent=2),
        "reviews.json":  json.dumps(reviews,  ensure_ascii=False, indent=2),
    })
    print(f"[Gist] Backup all: {len(products)} products, {len(orders)} orders, {len(reviews)} reviews")

_gist_load()
_restore_orders_reviews()


@app.on_event("shutdown")
def _on_shutdown():
    """Flush all data in ONE Gist API call when Render sends SIGTERM before redeploy."""
    print("[Shutdown] Flushing all data to Gist (single call)...")
    try:
        _backup_all()
    except Exception as e:
        print(f"[Shutdown] Backup error: {e}")
    print("[Shutdown] Done.")


# ── Auth ──────────────────────────────────────────────────
def require_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds or not hmac.compare_digest(creds.credentials, _ADMIN_TOKEN):
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
        # Return stateless HMAC token — same token every time, survives server restarts
        return {"token": _ADMIN_TOKEN}
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
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_backup_executor, _gist_save_fast, products), timeout=15)
    except Exception as e:
        print(f"[Backup] Products backup error: {e}")
    background_tasks.add_task(_github_commit, products)
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
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_backup_executor, _gist_save_fast, products), timeout=15)
    except Exception as e:
        print(f"[Backup] Products backup error: {e}")
    background_tasks.add_task(_github_commit, products)
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
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_backup_executor, _gist_save_fast, products), timeout=15)
    except Exception as e:
        print(f"[Backup] Products backup error: {e}")
    background_tasks.add_task(_github_commit, products)
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
async def delete_product(pid: int, background_tasks: BackgroundTasks,
                         token: str = Depends(require_admin)):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    products = [json.loads(r["data"]) for r in
                conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()]
    conn.close()
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_backup_executor, _gist_save_fast, products), timeout=15)
    except Exception as e:
        print(f"[Backup] Products backup error: {e}")
    background_tasks.add_task(_github_commit, products)
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
    ip = _client_ip(req)
    if not _rate_check(f"order:{ip}", 10, 3600):
        raise HTTPException(status_code=429, detail="Забагато запитів. Спробуйте пізніше.")
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid order")
    # Sanitise string fields to prevent oversized payloads slipping past content-length check
    for field in ("firstName", "lastName", "phone", "city", "branch", "comment", "payment", "delivery"):
        if field in body:
            body[field] = str(body[field] or "")[:200]
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
            background_tasks.add_task(_gist_save_fast, all_products)

    conn.commit()
    conn.close()
    # Backup synchronously in thread pool — waits up to 8s before returning success.
    # This guarantees the order survives a Render free-tier spin-down restart.
    loop = asyncio.get_running_loop()
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
                background_tasks.add_task(_gist_save_fast, all_products)
    conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
    conn.commit(); conn.close()
    background_tasks.add_task(_backup_orders)  # fire-and-forget is fine for delete
    return {"ok": True}

# ── Reviews ───────────────────────────────────────────────
@app.get("/api/reviews")
def get_reviews():
    conn = get_db()
    rows = conn.execute("SELECT id, data FROM reviews ORDER BY id DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = json.loads(r["data"]); d["_id"] = r["id"]; result.append(d)
    return result

@app.post("/api/reviews")
async def create_review(req: Request, background_tasks: BackgroundTasks):
    ip = _client_ip(req)
    if not _rate_check(f"review:{ip}", 5, 3600):
        raise HTTPException(status_code=429, detail="Забагато відгуків. Спробуйте пізніше.")
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
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_backup_executor, _backup_reviews), timeout=8)
    except Exception as e:
        print(f"[Backup] Reviews backup error (review saved to DB): {e}")
    return {"ok": True}

@app.delete("/api/reviews/{rid}")
async def delete_review(rid: int, background_tasks: BackgroundTasks,
                        token: str = Depends(require_admin)):
    conn = get_db()
    row = conn.execute("SELECT id FROM reviews WHERE id = ?", (rid,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Review not found")
    conn.execute("DELETE FROM reviews WHERE id = ?", (rid,))
    conn.commit(); conn.close()
    background_tasks.add_task(_backup_reviews)
    return {"ok": True}

@app.post("/api/admin/restore")
async def admin_restore(token: str = Depends(require_admin)):
    """Force-restore products, orders and reviews from Gist into SQLite."""
    result = {}

    products = _gist_fetch_file("products.json")
    if isinstance(products, list):
        _insert_products(products)
        result["products"] = len(products)
    else:
        result["products"] = -1

    orders = _gist_fetch_file("orders.json")
    if isinstance(orders, list):
        conn = get_db()
        conn.execute("DELETE FROM orders")
        for o in orders:
            conn.execute("INSERT INTO orders (data) VALUES (?)", (json.dumps(o, ensure_ascii=False),))
        conn.commit(); conn.close()
        result["orders"] = len(orders)
    else:
        result["orders"] = -1

    reviews = _gist_fetch_file("reviews.json")
    if isinstance(reviews, list):
        conn = get_db()
        conn.execute("DELETE FROM reviews")
        for rv in reviews:
            conn.execute("INSERT INTO reviews (data) VALUES (?)", (json.dumps(rv, ensure_ascii=False),))
        conn.commit(); conn.close()
        result["reviews"] = len(reviews)
    else:
        result["reviews"] = -1

    print(f"[Restore] products={result['products']} orders={result['orders']} reviews={result['reviews']}")
    return {"ok": True, **result}


@app.post("/api/admin/logout")
def admin_logout():
    # Token is stateless (HMAC) — logout is handled client-side by clearing localStorage
    return {"ok": True}

@app.get("/api/admin/debug")
async def admin_debug(token: str = Depends(require_admin)):
    """Show system state: SQLite counts + Gist reachability."""
    conn = get_db()
    db_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    db_orders   = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    db_reviews  = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    conn.close()

    gist_ok = False; gist_products = -1; gist_error = ""
    if GITHUB_TOKEN and GIST_ID:
        try:
            import urllib.request
            req = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}", headers=_gist_headers())
            meta = json.loads(urllib.request.urlopen(req, timeout=10).read())
            files = meta.get("files", {})
            gist_ok = True
            raw_url = files.get("products.json", {}).get("raw_url", "")
            if raw_url:
                r2 = urllib.request.Request(raw_url, headers={"User-Agent": "nice-shopping"})
                data = json.loads(urllib.request.urlopen(r2, timeout=10).read())
                gist_products = len(data) if isinstance(data, list) else -1
            else:
                gist_products = 0
        except Exception as e:
            gist_error = str(e)
    else:
        gist_error = "GITHUB_TOKEN or GIST_ID not configured"

    # Check which GitHub account the token belongs to
    token_user = ""
    try:
        import urllib.request
        req = urllib.request.Request("https://api.github.com/user", headers=_gist_headers())
        user_data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        token_user = user_data.get("login", "unknown")
    except Exception as e:
        token_user = f"error: {e}"

    return {
        "sqlite": {"products": db_products, "orders": db_orders, "reviews": db_reviews},
        "gist": {"ok": gist_ok, "products": gist_products, "error": gist_error},
        "config": {"has_token": bool(GITHUB_TOKEN), "has_gist_id": bool(GIST_ID)},
        "token_owner": token_user,
        "gist_owner": GIST_ID and f"sashanazarenko2051-source/{GIST_ID[:8]}...",
    }

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
