from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json, os, time, secrets
from pathlib import Path

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ADMIN_PASS = os.getenv("ADMIN_PASS", "admin2025")
DATABASE_URL = os.getenv("DATABASE_URL", "")
_tokens: set = set()
security = HTTPBearer(auto_error=False)

PG = bool(DATABASE_URL)
P = "%s" if PG else "?"

if PG:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def _connect():
        return psycopg2.connect(DATABASE_URL)

    def init_db():
        conn = _connect()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS products (id BIGINT PRIMARY KEY, data TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS orders (id BIGSERIAL PRIMARY KEY, data TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS reviews (id BIGSERIAL PRIMARY KEY, data TEXT NOT NULL)")
        conn.commit(); cur.close(); conn.close()

    def db_fetchall(sql, params=()):
        conn = _connect()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows

else:
    import sqlite3
    DB_PATH = os.getenv("DB_PATH", "shop.db")

    def _connect():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        conn = _connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL);
        """)
        conn.close()

    def db_fetchall(sql, params=()):
        conn = _connect()
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        conn.close()
        return rows

def db_exec(statements):
    conn = _connect()
    if PG:
        cur = conn.cursor()
        for sql, params in statements:
            cur.execute(sql, params)
        conn.commit(); cur.close(); conn.close()
    else:
        for sql, params in statements:
            conn.execute(sql, params)
        conn.commit(); conn.close()

init_db()

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
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid password")

# ── Products ──────────────────────────────────────────────
@app.get("/api/products")
def get_products():
    return [json.loads(r["data"]) for r in db_fetchall("SELECT data FROM products ORDER BY id ASC")]

@app.put("/api/products")
async def set_all_products(req: Request, token: str = Depends(require_admin)):
    products = await req.json()
    stmts = [("DELETE FROM products", ())]
    for p in products:
        pid = int(p.get("id") or int(time.time() * 1000))
        p["id"] = pid
        stmts.append((f"INSERT INTO products (id, data) VALUES ({P}, {P})", (pid, json.dumps(p))))
    db_exec(stmts)
    return {"ok": True, "count": len(products)}

@app.delete("/api/products/{pid}")
def delete_product(pid: int, token: str = Depends(require_admin)):
    db_exec([(f"DELETE FROM products WHERE id = {P}", (pid,))])
    return {"ok": True}

# ── Orders ────────────────────────────────────────────────
@app.get("/api/orders")
def get_orders(token: str = Depends(require_admin)):
    rows = db_fetchall("SELECT id, data FROM orders ORDER BY id DESC")
    result = []
    for r in rows:
        d = json.loads(r["data"])
        d["_id"] = r["id"]
        result.append(d)
    return result

@app.post("/api/orders")
async def create_order(req: Request):
    body = await req.json()
    db_exec([(f"INSERT INTO orders (data) VALUES ({P})", (json.dumps(body),))])
    return {"ok": True}

@app.delete("/api/orders/{oid}")
def delete_order_api(oid: int, token: str = Depends(require_admin)):
    db_exec([(f"DELETE FROM orders WHERE id = {P}", (oid,))])
    return {"ok": True}

# ── Reviews ───────────────────────────────────────────────
@app.get("/api/reviews")
def get_reviews():
    return [json.loads(r["data"]) for r in db_fetchall("SELECT data FROM reviews ORDER BY id DESC")]

@app.post("/api/reviews")
async def create_review(req: Request):
    body = await req.json()
    db_exec([(f"INSERT INTO reviews (data) VALUES ({P})", (json.dumps(body),))])
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
