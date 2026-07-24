from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI


def make_client(base_dir: Path | None = None, timeout: float = 60) -> tuple[OpenAI, str]:
    """读 .env，返回 (OpenAI 客户端, model 名)。"""
    root = base_dir or Path(__file__).resolve().parent
    load_dotenv(root / ".env")
    api_key = (os.getenv("API_KEY") or "").strip()
    base_url = (os.getenv("BASE_URL") or "").strip()
    model = (os.getenv("MODEL_NAME") or "deepseek-chat").strip()
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout), model