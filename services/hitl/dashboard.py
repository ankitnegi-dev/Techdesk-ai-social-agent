
import json, logging
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from shared.config import get_settings
from shared.db.models import init_db


import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    import os
    password = os.getenv("HITL_PASSWORD", "techdesk2024")
    correct = secrets.compare_digest(credentials.password.encode(), password.encode())
    if not correct:
        raise HTTPException(status_code=401, detail="Incorrect password",
                           headers={"WWW-Authenticate": "Basic"})
    return credentials.username

settings = get_settings()
log = logging.getLogger("hitl")
app = FastAPI(title="Social Agent HITL Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
connected_clients = []

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def dashboard(user: str = Depends(verify_password)):
    return HTMLResponse(get_html())

@app.get("/api/queue")
async def get_queue():
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    items = await r.lrange("queue:hitl_review", 0, -1)
    parsed = []
    for item in items:
        try:
            parsed.append(json.loads(item))
        except:
            pass
    await r.aclose()
    return {"items": parsed, "count": len(parsed)}

@app.post("/api/approve/{action_id}")
async def approve_action(action_id: str, request: Request):
    body = await request.json()
    final_content = body.get("final_content", "")
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    items = await r.lrange("queue:hitl_review", 0, -1)
    for item in items:
        data = json.loads(item)
        if data.get("id") == action_id:
            data["review_status"] = "approved"
            data["final_content"] = final_content or data.get("draft_content", "")
            await r.lrem("queue:hitl_review", 1, item)
            await r.lpush("queue:approved", json.dumps(data))
            break
    await r.aclose()
    await broadcast({"type": "approved", "action_id": action_id})
    return {"status": "approved"}

@app.post("/api/reject/{action_id}")
async def reject_action(action_id: str, request: Request):
    body = await request.json()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    items = await r.lrange("queue:hitl_review", 0, -1)
    for item in items:
        data = json.loads(item)
        if data.get("id") == action_id:
            await r.lrem("queue:hitl_review", 1, item)
            break
    await r.aclose()
    await broadcast({"type": "rejected", "action_id": action_id})
    return {"status": "rejected"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

async def broadcast(message: dict):
    for client in connected_clients.copy():
        try:
            await client.send_json(message)
        except:
            if client in connected_clients:
                connected_clients.remove(client)

def get_html():
    return open("services/hitl/dashboard.html").read()

from services.rlhf.collector import record_preference
from services.rlhf.strategy_tracker import record_outcome, get_strategy_leaderboard
from services.rlhf.dashboard_routes import router as rlhf_router
app.include_router(rlhf_router)

@app.get("/api/leaderboard")
async def leaderboard():
    return get_strategy_leaderboard()
