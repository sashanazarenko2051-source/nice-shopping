from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3, json, os, time, secrets
from pathlib import Path

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = os.getenv("DB_PATH", "shop.db")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin2025")
_tokens: set = set()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            created_at REAL DEFAULT (julianday('now'))
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            created_at REAL DEFAULT (julianday('now'))
        );
    """)
    conn.commit()
    conn.close()

init_db()

security = HTTPBearer(auto_error=False)

def require_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds or creds.credentials not in _tokens:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return creds.credentials

# ── Auth ────────────────────────────────────────────────
@app.post("/api/admin/login")
async def admin_login(req: Request):
    body = await req.json()
    if body.get("password") == ADMIN_PASS:
        token = secrets.token_urlsafe(32)
        _tokens.add(token)
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid password")

# ── Products ─────────────────────────────────────────────
@app.get("/api/products")
def get_products():
    conn = get_db()
    rows = conn.execute("SELECT data FROM products ORDER BY id ASC").fetchall()
    conn.close()
    return [json.loads(r["data"]) for r in rows]

@app.put("/api/products")
async def set_all_products(req: Request, token: str = Depends(require_admin)):
    products = await req.json()
    conn = get_db()
    conn.execute("DELETE FROM products")
    for p in products:
        pid = int(p.get("id") or int(time.time() * 1000))
        p["id"] = pid
        conn.execute("INSERT INTO products (id, data) VALUES (?, ?)", (pid, json.dumps(p)))
    conn.commit()
    conn.close()
    return {"ok": True, "count": len(products)}

@app.delete("/api/products/{pid}")
def delete_product(pid: int, token: str = Depends(require_admin)):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ── Orders ───────────────────────────────────────────────
@app.get("/api/orders")
def get_orders(token: str = Depends(require_admin)):
    conn = get_db()
    rows = conn.execute("SELECT id, data FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = json.loads(r["data"])
        d["_id"] = r["id"]
        result.append(d)
    return result

@app.post("/api/orders")
async def create_order(req: Request):
    body = await req.json()
    conn = get_db()
    conn.execute("INSERT INTO orders (data) VALUES (?)", (json.dumps(body),))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/api/orders/{oid}")
def delete_order_api(oid: int, token: str = Depends(require_admin)):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ── Reviews ──────────────────────────────────────────────
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
    conn.commit()
    conn.close()
    return {"ok": True}

# ── Block sensitive files ─────────────────────────────────
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
