from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.agents_core import router as agents_core_router
from app.api.routers.agents_invoke_and_logs import router as agents_invoke_router
from app.api.routers.agents_instructions_a2a import router as agents_instr_router
from app.api.routers.agents_keys import router as agents_keys_router
from app.api.routers.billing import router as billing_router
from app.api.routers.runs import router as runs_router
from app.middleware.auth_middleware import AuthMiddleware
from app.mcp import router as mcp_router

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
app.include_router(agents_core_router, prefix="/v1")
app.include_router(agents_invoke_router, prefix="/v1")
app.include_router(agents_instr_router, prefix="/v1")
app.include_router(agents_keys_router, prefix="/v1")
app.include_router(billing_router, prefix="/v1")
app.include_router(runs_router, prefix="/v1")
app.include_router(mcp_router)
