from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    upstage_api_key: str = getenv("UPSTAGE_API_KEY", "")
    llm_model: str = getenv("LLM_MODEL", "solar-pro3")


settings = Settings()
