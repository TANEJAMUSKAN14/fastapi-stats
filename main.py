import os
import time
import uuid
import httpx
import json
import re
from collections import defaultdict, deque
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter, generate_latest
import redis
import jwt
from pydantic import BaseModel, Field

import config

LLM_MODEL = "qwen2.5:0.5b"
START_TIME = time.time()

app = FastAPI()

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

http_requests_total = Counter("http_requests_total", "Total HTTP Requests")
logs_queue = deque(maxlen=100)


# ---------------- RATE LIMIT ----------------
def is_rate_limited(client_id: str, limit: int, prefix: str) -> bool:
    key = f"ratelimit:{prefix}:{client_id}"
    now = time.time()
    try:
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - 10)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 12)
        res = pipe.execute()
        return res[2] > limit
    except Exception:
        return False


# ---------------- SAFE JSON ----------------
def safe_extract_json(s: str) -> dict:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        s = s.rstrip("```")
    try:
        return json.loads(s)
    except Exception:
        match = re.search(r'(\{.*\})', s, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
    return {}


# ---------------- MIDDLEWARE (FIXED CORS) ----------------
@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    start_time = time.time()
    http_requests_total.inc()

    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.req_id = req_id

    origin = request.headers.get("Origin")
    path = request.url.path.rstrip("/") or "/"

    # ✅ HANDLE PREFLIGHT (MOST IMPORTANT)
    if request.method == "OPTIONS":
        response = Response(status_code=200)

        if path == "/stats":
            if origin == config.Q1_ALLOWED_ORIGIN:
                response.headers["Access-Control-Allow-Origin"] = origin

        if path == "/ping":
            if origin == config.Q10_ALLOWED_ORIGIN:
                response.headers["Access-Control-Allow-Origin"] = origin

        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"

        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time"] = "0.0"

        return response

    # ---------------- NORMAL FLOW ----------------
    try:
        response = await call_next(request)
    except Exception:
        response = Response(status_code=500, content="Internal Server Error")

    # ✅ STRICT CORS
    if path == "/stats":
        if origin == config.Q1_ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = origin

    elif path == "/ping":
        if origin == config.Q10_ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = origin

    # ❌ NO wildcard allowed → DO NOTHING for others

    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}"

    return response


# ---------------- Q1 ----------------
@app.get("/stats")
async def stats(values: str = ""):
    nums = [int(x) for x in values.split(",") if x.strip()]
    if not nums:
        return JSONResponse(content={"error": "no values"}, status_code=400)

    return {
        "email": config.EMAIL,
        "count": len(nums),
        "sum": sum(nums),
        "min": min(nums),
        "max": max(nums),
        "mean": round(sum(nums) / len(nums), 2)
    }


# ---------------- Q2 ----------------
@app.post("/verify")
async def verify_token(request: Request):
    try:
        body = await request.json()
        token = body.get("token")

        claims = jwt.decode(
            token,
            config.PUBLIC_KEY_PEM.strip(),
            algorithms=["RS256"],
            issuer=config.ISSUER,
            audience=config.AUDIENCE
        )

        return {
            "valid": True,
            "email": claims.get("email", ""),
            "sub": claims.get("sub", ""),
            "aud": claims.get("aud", "")
        }

    except Exception:
        return JSONResponse(status_code=401, content={"valid": False})


# ---------------- Q3 ----------------
@app.get("/effective-config")
async def get_config(request: Request):
    cfg = {
        "port": config.Q3_PORT,
        "workers": config.Q3_WORKERS,
        "debug": config.Q3_DEBUG,
        "log_level": config.Q3_LOG_LEVEL,
        "api_key": "****"
    }

    for k, value in request.query_params.multi_items():
        if k == "set":
            key, val = value.split("=", 1)
            if key in ["port", "workers"]:
                cfg[key] = int(val)
            elif key == "debug":
                cfg[key] = str(val).lower() in ["true", "1"]
            else:
                cfg[key] = val

    return cfg


# ---------------- Q4/Q6 ----------------
@app.post("/hit/{key}")
async def hit(key: str):
    return {"key": key, "count": redis_client.incr(key)}


@app.get("/count/{key}")
async def get_count(key: str):
    val = redis_client.get(key)
    return {"key": key, "count": int(val) if val else 0}


# ---------------- HEALTH ----------------
@app.get("/healthz")
async def healthz():
    try:
        redis_client.ping()
        return {"status": "ok"}
    except Exception:
        return {"status": "error"}


@app.get("/work")
async def do_work(n: int = 1):
    return {"email": config.EMAIL, "done": n}


@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.get("/logs/tail")
async def logs_tail(limit: int = 10):
    return list(logs_queue)[-limit:]


# ---------------- Q5 ----------------
@app.post("/analytics")
async def analytics(request: Request):
    if request.headers.get("X-API-Key") != config.Q5_API_KEY:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    body = await request.json()
    events = body.get("events", [])

    users = set()
    revenue = 0
    user_rev = defaultdict(float)

    for e in events:
        u = e.get("user")
        amt = e.get("amount", 0)
        if u:
            users.add(u)
        if amt > 0:
            revenue += amt
            if u:
                user_rev[u] += amt

    return {
        "email": config.EMAIL,
        "total_events": len(events),
        "unique_users": len(users),
        "revenue": revenue,
        "top_user": max(user_rev, key=user_rev.get) if user_rev else None
    }
