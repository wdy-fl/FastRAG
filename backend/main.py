from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.deps import get_llm_provider, get_embedding_provider, get_redis_cache
from backend.api.routers import chat, conversation, knowledge, ingestion, intent, trace, mapping


@asynccontextmanager
async def lifespan(app: FastAPI):
    _tmp_dir = Path(__file__).parent / "temp"
    if _tmp_dir.exists():
        for f in _tmp_dir.iterdir():
            if f.is_file():
                f.unlink(missing_ok=True)
    yield
    # Graceful shutdown
    await get_llm_provider().close()
    await get_embedding_provider().close()
    await get_redis_cache().close()


app = FastAPI(
    title="FastRAG",
    version="0.1.0",
    root_path="/api/fastrag",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(conversation.router, prefix="/conversations", tags=["conversation"])
app.include_router(knowledge.router, prefix="/knowledge-bases", tags=["knowledge"])
app.include_router(ingestion.router, tags=["ingestion"])
app.include_router(intent.router, prefix="/intent-trees", tags=["intent"])
app.include_router(trace.router, prefix="/traces", tags=["trace"])
app.include_router(mapping.router, prefix="/query-term-mappings", tags=["mapping"])
