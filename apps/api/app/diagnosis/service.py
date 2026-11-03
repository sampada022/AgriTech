"""Cache, provider call and fallback for leaf diagnosis (TRD 6.6). This never raises.

Order: cache hit, then the live provider, then on failure a canned reply in demo mode or the
"choose a cause yourself" card otherwise. A failure here must never leave a blank screen.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import lru_cache

from app.config import get_settings
from app.diagnosis.guidance import (
    ADVISORY,
    BLURRY_MESSAGE,
    CANDIDATE_TO_LABEL,
    FALLBACK_MESSAGE,
    label_options,
)
from app.diagnosis.providers import (
    CannedProvider,
    DiagnosisContext,
    DiagnosisProvider,
    DiagnosisUnavailable,
    build_provider,
)
from app.diagnosis.schema import LeafDiagnosis
from app.errors import ApiError
from app.services.demo_settings import demo_settings
from app.storage import diagnosis_cache_dir

log = logging.getLogger("aeroscout.diagnosis")

SOURCE_LIVE = "live"
SOURCE_CACHE = "cache"
SOURCE_CANNED = "canned"
SOURCE_FALLBACK = "fallback"


@dataclass
class DiagnosisOutcome:
    source: str
    diagnosis: LeafDiagnosis | None
    reason: str | None = None
    seconds: float = 0.0
    extra: dict = field(default_factory=dict)


@lru_cache
def _provider() -> DiagnosisProvider | None:
    return build_provider(get_settings())


def reset_provider() -> None:
    _provider.cache_clear()


def _cache_path(image_hash: str, language: str):
    return diagnosis_cache_dir() / f"{image_hash}_{language}.json"


def demo_replies_dir():
    """Replies kept for the demo kit. A demo reset leaves this alone, unlike everything else.

    Resetting just before judging must not throw away the replies that protect the demo if the API
    goes down. It holds only replies keyed by a hash, with no photos and no location.
    """
    return get_settings().demo_assets_dir / "leaf_replies"


def _demo_reply_path(image_hash: str, language: str):
    return demo_replies_dir() / f"{image_hash}_{language}.json"


def read_cache(image_hash: str, language: str) -> LeafDiagnosis | None:
    for path in (_cache_path(image_hash, language), _demo_reply_path(image_hash, language)):
        if not path.exists():
            continue
        try:
            return LeafDiagnosis.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            log.warning("diagnosis_cache_corrupt path=%s", path)
    return None


def _write_reply(path, diagnosis: LeafDiagnosis) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diagnosis.model_dump(), ensure_ascii=False), encoding="utf-8")


def write_demo_reply(image_hash: str, language: str, diagnosis: LeafDiagnosis) -> None:
    _write_reply(_demo_reply_path(image_hash, language), diagnosis)


def write_cache(image_hash: str, language: str, diagnosis: LeafDiagnosis) -> None:
    _write_reply(_cache_path(image_hash, language), diagnosis)
    if get_settings().demo_mode:
        # So running each demo photo once during rehearsal is enough to protect it.
        write_demo_reply(image_hash, language, diagnosis)


def run_diagnosis(image: bytes, image_hash: str, context: DiagnosisContext) -> DiagnosisOutcome:
    started = time.perf_counter()
    settings = get_settings()

    def done(source: str, diagnosis: LeafDiagnosis | None, reason: str | None = None):
        seconds = round(time.perf_counter() - started, 3)
        log.info(
            "diagnosis source=%s reason=%s seconds=%.3f language=%s",
            source, reason, seconds, context.language,
        )
        return DiagnosisOutcome(source, diagnosis, reason, seconds)

    cached = read_cache(image_hash, context.language)
    if cached is not None:
        return done(SOURCE_CACHE, cached)

    if settings.demo_mode and demo_settings.force_cached_ai:
        return done(SOURCE_CANNED, CannedProvider().diagnose(image, context), "forced")

    reason = "not_configured"
    provider = _provider()
    if provider is not None:
        try:
            diagnosis = provider.diagnose(image, context)
            write_cache(image_hash, context.language, diagnosis)
            return done(SOURCE_LIVE, diagnosis)
        except DiagnosisUnavailable as exc:
            reason = exc.reason
        except Exception:  # noqa: BLE001  (a diagnosis failure must never become a blank screen)
            log.exception("diagnosis_unexpected_error")
            reason = "unexpected_error"

    if settings.demo_mode:
        return done(SOURCE_CANNED, CannedProvider().diagnose(image, context), reason)
    return done(SOURCE_FALLBACK, None, reason)


def outcome_payload(outcome: DiagnosisOutcome, language: str, blurry: bool) -> dict:
    """The diagnosis block of an observation, including what the Result screen needs on failure."""
    lang = language if language in ADVISORY else "en"
    diagnosis = outcome.diagnosis
    suggested = None
    if diagnosis is not None and diagnosis.candidates:
        suggested = CANDIDATE_TO_LABEL.get(diagnosis.candidates[0].type)
    return {
        "source": outcome.source,
        "result": diagnosis.model_dump() if diagnosis is not None else None,
        "suggested_label": suggested,
        "message": None if diagnosis is not None else FALLBACK_MESSAGE[lang],
        "photo_warning": BLURRY_MESSAGE[lang] if blurry else None,
        "advisory": ADVISORY[lang],
        "label_options": label_options(lang),
    }


class RateLimiter:
    """Sliding one-minute window per client IP, protecting the API key during judging (TRD 8.5)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, client: str, limit: int) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= limit:
                raise ApiError(
                    429,
                    "rate_limited",
                    "Too many photos in the last minute.",
                    "Wait a moment and try again.",
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()
