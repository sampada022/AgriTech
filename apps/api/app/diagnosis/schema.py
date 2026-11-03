"""The structured reply a leaf diagnosis must match (TRD 6.6)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

CandidateType = Literal["pest", "disease", "nutrient", "water", "weeds_other", "healthy", "unsure"]

MAX_CANDIDATES = 3
_PROBABILITY_TOLERANCE = 0.01

# Last line of defence for "no doses". The prompt forbids them; this catches what slips through.
_DOSE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:ml|l|g|gm|kg|mg|litres?|liters?|grams?|ppm|%)(?:\b|/|\s|$)",
    re.IGNORECASE,
)


class Candidate(BaseModel):
    name: str
    type: CandidateType
    probability: float

    @field_validator("probability")
    @classmethod
    def _in_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("probability must be between 0 and 1")
        return value


class LeafDiagnosis(BaseModel):
    plant_visible: bool
    image_quality: Literal["good", "fair", "poor"]
    observed_symptoms: list[str]
    candidates: list[Candidate]
    confirm_by: list[str]
    actions_ipm: list[str]
    needs_expert: bool
    language: Literal["en", "kn"]

    @model_validator(mode="after")
    def _enforce_rules(self) -> "LeafDiagnosis":
        self.candidates = sorted(self.candidates, key=lambda c: -c.probability)[:MAX_CANDIDATES]
        total = sum(c.probability for c in self.candidates)
        if total > 1.0 + _PROBABILITY_TOLERANCE:
            raise ValueError("candidate probabilities must sum to 1 or less")
        self.actions_ipm = [a for a in self.actions_ipm if not _DOSE_PATTERN.search(a)]
        return self
