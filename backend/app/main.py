from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.agents import router as agents_router
from app.api.routers.billing import router as billing_router
from app.api.routers.runs import router as runs_router
from app.middleware.auth_middleware import AuthMiddleware

app = FastAPI(title="Collexa API", version="0.1.0")

# CORS: adjust allowed origins for your UI host(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Coarse auth middleware for /v1/*
app.add_middleware(AuthMiddleware)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Mount routers (v1)
app.include_router(agents_router, prefix="/v1")
app.include_router(billing_router, prefix="/v1")
app.include_router(runs_router, prefix="/v1")

