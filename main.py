from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3, json, os, time, secrets
from pathlib import Path

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ADMIN_PASS   = os.getenv("ADMIN_PASS", "admin2025")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_ID      = os.getenv("GIST_ID", "")
_tokens: set = set()
security = HTTPBearer(auto_error=False)

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
    rows = conn.execute("SELECT token FROM tokens").fetchall()
    conn.close()
    for r in rows:
        _tokens.add(r["token"])

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

def _gist_load():
    """На старті: якщо SQLite порожній — завантажити товари з Gist, потім з products.json"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    if count > 0:
        return

    # 1) Try Gist via raw_url (avoids content-field truncation for large files)
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
                if products:
                    _insert_products(products)
                    print(f"[Gist] Loaded {len(products)} products")
                    return
        except Exception as e:
            print(f"[Gist] Load error: {e}")

    # 2) Permanent fallback: products.json committed to git repo (always present after deploy)
    try:
        fb = Path("products.json")
        if fb.exists():
            products = json.loads(fb.read_text(encoding="utf-8"))
            if products:
                _insert_products(products)
                print(f"[Fallback] Loaded {len(products)} products from products.json")
    except Exception as e:
        print(f"[Fallback] Load error: {e}")

def _gist_save(products):
    """Зберегти товари в Gist (фоново) + оновити products.json на диску"""
    # Always update the local file so it's current until next deploy
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

_gist_load()

# ── Auth ──────────────────────────────────────────────────
def require_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds or creds.credentials not in _tokens:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return creds.credentials

@app.post("/api/admin/login")
async def admin_login(req: Request):
    body = await req.json()
    if body.get("password") == ADMIN_PASS:
        token = secrets.token_urlsafe(32)
        _tokens.add(token)
        conn = get_db()
        conn.execute("INSERT OR REPLACE INTO tokens (token, ts) VALUES (?, ?)", (token, int(time.time())))
        conn.commit(); conn.close()
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid password")

# ── Products ──────────────────────────────────────────────
@app.get("/api/products")
def get_products():
    conn = get_db()
    rows = conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()
    conn.close()
    return [json.loads(r["data"]) for r in rows]

@app.put("/api/products")
async def set_all_products(req: Request, background_tasks: BackgroundTasks,
                           token: str = Depends(require_admin)):
    products = await req.json()
    conn = get_db()
    conn.execute("DELETE FROM products")
    for i, p in enumerate(products):
        pid = int(p.get("id") or int(time.time() * 1000) + i)
        p["id"] = pid
        conn.execute("INSERT INTO products (id, data) VALUES (?, ?)", (pid, json.dumps(p)))
    conn.commit(); conn.close()
    background_tasks.add_task(_gist_save, products)
    return {"ok": True, "count": len(products)}

@app.post("/api/products/one")
async def add_one_product(req: Request, background_tasks: BackgroundTasks,
                          token: str = Depends(require_admin)):
    data = await req.json()
    pid = int(data.get("id") or int(time.time() * 1000))
    data["id"] = pid
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO products (id, data) VALUES (?, ?)", (pid, json.dumps(data)))
    conn.commit()
    products = [json.loads(r["data"]) for r in
                conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()]
    conn.close()
    background_tasks.add_task(_gist_save, products)
    return {"ok": True, "id": pid}

@app.put("/api/products/{pid}")
async def update_one_product(pid: int, req: Request, background_tasks: BackgroundTasks,
                             token: str = Depends(require_admin)):
    data = await req.json()
    data["id"] = pid
    conn = get_db()
    row = conn.execute("SELECT id FROM products WHERE id = ?", (pid,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    conn.execute("UPDATE products SET data = ? WHERE id = ?", (json.dumps(data), pid))
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
def get_orders(token: str = Depends(require_admin)):
    conn = get_db()
    rows = conn.execute("SELECT id, data FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = json.loads(r["data"]); d["_id"] = r["id"]; result.append(d)
    return result

@app.post("/api/orders")
async def create_order(req: Request):
    body = await req.json()
    conn = get_db()
    conn.execute("INSERT INTO orders (data) VALUES (?)", (json.dumps(body),))
    conn.commit(); conn.close()
    return {"ok": True}

@app.delete("/api/orders/{oid}")
def delete_order_api(oid: int, token: str = Depends(require_admin)):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
    conn.commit(); conn.close()
    return {"ok": True}

# ── Reviews ───────────────────────────────────────────────
@app.get("/api/reviews")
def get_reviews():
    conn = get_db()
    rows = conn.execute("SELECT data FROM reviews ORDER BY id DESC").fetchall()
    conn.close()
    return [json.loads(r["data"]) for r in rows]

@app.post("/api/reviews")
async def create_review(req: Request):
    body = await req.json()
    conn = get_db()
    conn.execute("INSERT INTO reviews (data) VALUES (?)", (json.dumps(body),))
    conn.commit(); conn.close()
    return {"ok": True}

# ── Static files ──────────────────────────────────────────
BLOCKED = {"main.py", "shop.db", "requirements.txt"}

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    name = Path(full_path).name
    if name in BLOCKED:
        raise HTTPException(status_code=404)
    path = Path(full_path) if full_path else Path("index.html")
    if path.exists() and path.is_file():
        return FileResponse(path)
    return FileResponse("index.html")
