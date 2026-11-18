import os
from pathlib import Path

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


def model(slug: str | None = None, temperature: float = 0.1) -> OpenAIModel:
    """Modelo de OpenRouter vía API compatible con OpenAI."""
    return OpenAIModel(
        client_args={"api_key": os.environ["OPENROUTER_API_KEY"], "base_url": "https://openrouter.ai/api/v1"},
        model_id=slug or os.getenv("TABI_LLM", "anthropic/claude-haiku-4.5"),
        params={"temperature": temperature},
    )


def judge_model() -> OpenAIModel:
    return model(os.getenv("TABI_JUDGE_LLM", "anthropic/claude-sonnet-4.5"), temperature=0)
