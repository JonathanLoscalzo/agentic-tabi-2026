import os
from functools import lru_cache
from pathlib import Path

import httpx
from dotenv import load_dotenv
from strands.models.openai import OpenAIModel

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DATA_DIR = ROOT / "data"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION = "tabi_docs"
CHUNK_SIZE, CHUNK_OVERLAP = 1000, 200
K = 4  # chunks de contexto por consulta
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080")
EMBEDDING = os.getenv("TABI_EMBEDDING", "embeddinggemma:latest")


DEFAULT_LLM = "anthropic/claude-haiku-5.5"


def use_llm(slug: str) -> None:
    """Elige el modelo de OpenRouter para todas las técnicas (lo lee model())."""
    os.environ["TABI_LLM"] = slug


@lru_cache
def list_models() -> list[str]:
    """Catálogo público de OpenRouter (no requiere key)."""
    r = httpx.get("https://openrouter.ai/api/v1/models", timeout=20)
    r.raise_for_status()
    return sorted(m["id"] for m in r.json()["data"])


def model(slug: str | None = None, temperature: float = 0.1) -> OpenAIModel:
    """Modelo de OpenRouter vía API compatible con OpenAI."""
    return OpenAIModel(
        client_args={"api_key": os.environ["OPENROUTER_API_KEY"], "base_url": "https://openrouter.ai/api/v1"},
        model_id=slug or os.getenv("TABI_LLM", DEFAULT_LLM),
        params={"temperature": temperature},
    )


def judge_model() -> OpenAIModel:
    return model(os.getenv("TABI_JUDGE_LLM", DEFAULT_LLM), temperature=0)
