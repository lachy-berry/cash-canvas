"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from server.db import init_db, get_connection
from server.categories import load_categories
from server.routes.import_csv import router as import_router
from server.routes.transactions import router as transactions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cash Canvas", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router)
app.include_router(transactions_router)


@app.get("/api/categories")
def get_categories() -> dict:
    """Return all category layers from the YAML config."""
    return load_categories()


@app.delete("/api/test/reset")
def test_reset() -> dict:
    """Wipe all transactions and batches. Only available when CASH_CANVAS_TEST_MODE=1."""
    if os.environ.get("CASH_CANVAS_TEST_MODE") != "1":
        raise HTTPException(status_code=403, detail="Test reset is not enabled.")
    with get_connection() as conn:
        conn.execute("DELETE FROM transaction_labels")
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM import_batches")
        conn.commit()
    return {"ok": True}
