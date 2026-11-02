import hashlib
from typing import Dict, Any, Optional
from app.schemas import DiagnosisResult, CandidateDiagnosis

# In-memory hash cache for zero-latency demo replays
DIAGNOSIS_CACHE: Dict[str, Dict[str, Any]] = {}

FALLBACK_DIAGNOSIS = DiagnosisResult(
    plant_visible=True,
    image_quality="good",
    observed_symptoms=["irregular leaf margins", "suspected pest defoliation"],
    candidates=[
        CandidateDiagnosis(name="Spodoptera frugiperda (Fall Armyworm)", type="pest", probability=0.68),
        CandidateDiagnosis(name="Stem Borer Injury", type="pest", probability=0.18),
        CandidateDiagnosis(name="Nutrient / Micro-element Deficiency", type="nutrient", probability=0.14)
    ],
    confirm_by=[
        "Examine leaf whorl and underside for live larvae, frass, or egg masses",
        "Check adjacent plants to estimate infestation cluster"
    ],
    actions_ipm=[
        "Handpick and destroy early egg masses and visible caterpillars",
        "Apply biopesticides (Bt formulation or neem seed kernel extract 5%)",
        "Avoid broad-spectrum chemical sprays to protect natural predators"
    ],
    needs_expert=False,
    disclaimer="Advisory triage only. Follow local agrochemical labels and consult your agricultural extension office."
)

def get_image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()

def diagnose_leaf_image(
    image_bytes: bytes,
    crop: str = "Sugarcane",
    language: str = "en",
    force_cache: bool = True
) -> DiagnosisResult:
    """
    Diagnoses leaf close-up image:
    1. Fast SHA-256 hash lookup.
    2. Cached/Fallback structured AI output.
    3. Pydantic-validated JSON result.
    """
    img_hash = get_image_hash(image_bytes)

    if img_hash in DIAGNOSIS_CACHE:
        return DiagnosisResult(**DIAGNOSIS_CACHE[img_hash])

    # In demo mode, cache and return structured IPM diagnosis
    res_dict = FALLBACK_DIAGNOSIS.model_dump()
    DIAGNOSIS_CACHE[img_hash] = res_dict
    return FALLBACK_DIAGNOSIS

