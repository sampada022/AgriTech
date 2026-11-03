"""Settings from the environment or .env. API keys stay server-side."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]  # apps/api/app/config.py -> repo root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # Legacy server knobs kept for anything that still reads them directly.
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = True

    data_dir: Path = REPO_ROOT / "data"
    demo_assets_dir: Path = REPO_ROOT / "demo" / "assets"
    benchmark_results: Path = REPO_ROOT / "apps" / "api" / "benchmarks" / "results.json"
    real_pixel_results: Path = REPO_ROOT / "apps" / "api" / "benchmarks" / "real_pixels.json"
    demo_mode: bool = True
    # healthy, pest or mixed. Loaded at startup when demo_mode is on.
    demo_autoload: str | None = None
    demo_force_cached_ai: bool = True

    # Known origins only. The regex exists for tunnel URLs, which change on each start.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )
    cors_origin_regex: str | None = None

    max_field_image_mb: int = 50
    max_field_pixels: int = 120_000_000
    max_photo_mb: int = 15
    max_photo_pixels: int = 50_000_000
    max_field_diagonal_m: float = 5000.0  # the flat-earth approximation degrades beyond this

    diagnosis_provider: str = "anthropic"  # anthropic | none
    diagnosis_model: str = "claude-opus-5-5"
    diagnosis_effort: str = "low"
    diagnosis_timeout_s: float = 12.0
    diagnosis_retries: int = 1
    anthropic_api_key: str | None = None
    diagnosis_rate_limit_per_min: int = 10
    # Behind cloudflared every request appears to come from localhost, so read the real client IP
    # from the tunnel's header. Only enable this when the API is reachable through the tunnel only.
    trust_proxy_headers: bool = False

    basemap_url: str = "https://tile.openstreetmap.org/0/0/0.png"
    health_cache_s: float = 30.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Back-compat singleton for any code still importing `settings` directly.
settings = get_settings()
