"""Ground-truth labels and IPM-first guidance (PRD 4 taxonomy, F24).

No products and no doses, ever. The Kannada strings have not been reviewed by a native speaker;
the demo kit in TRD 8.6 lists that check, so do it before showing them.
"""

from __future__ import annotations

LABEL_PEST = "pest"
LABEL_DISEASE = "disease"
LABEL_NUTRIENT = "nutrient"
LABEL_WATER = "water"
LABEL_WEEDS = "weeds_other"
LABEL_FALSE_ALARM = "false_alarm"

LABELS = (LABEL_PEST, LABEL_DISEASE, LABEL_NUTRIENT, LABEL_WATER, LABEL_WEEDS, LABEL_FALSE_ALARM)
BIOTIC_LABELS = {LABEL_PEST, LABEL_DISEASE}
ABIOTIC_LABELS = {LABEL_NUTRIENT, LABEL_WATER, LABEL_WEEDS}

LABEL_NAMES = {
    "en": {
        LABEL_PEST: "Pest damage",
        LABEL_DISEASE: "Disease",
        LABEL_NUTRIENT: "Nutrient deficiency",
        LABEL_WATER: "Water stress",
        LABEL_WEEDS: "Weeds or other",
        LABEL_FALSE_ALARM: "False alarm (healthy)",
    },
    "kn": {
        LABEL_PEST: "ಕೀಟ ಹಾನಿ",
        LABEL_DISEASE: "ರೋಗ",
        LABEL_NUTRIENT: "ಪೋಷಕಾಂಶ ಕೊರತೆ",
        LABEL_WATER: "ನೀರಿನ ಒತ್ತಡ",
        LABEL_WEEDS: "ಕಳೆ ಅಥವಾ ಇತರೆ",
        LABEL_FALSE_ALARM: "ತಪ್ಪು ಎಚ್ಚರಿಕೆ (ಆರೋಗ್ಯಕರ)",
    },
}

ADVISORY = {
    "en": "This is advisory only. Follow the product label and consult your local agriculture "
    "extension office before treating.",
    "kn": "ಇದು ಸಲಹೆ ಮಾತ್ರ. ಚಿಕಿತ್ಸೆ ನೀಡುವ ಮೊದಲು ಉತ್ಪನ್ನದ ಲೇಬಲ್ ಅನುಸರಿಸಿ ಮತ್ತು ನಿಮ್ಮ ಸ್ಥಳೀಯ ಕೃಷಿ "
    "ವಿಸ್ತರಣಾ ಕಚೇರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
}

FALLBACK_MESSAGE = {
    "en": "Could not analyse, choose a cause yourself.",
    "kn": "ವಿಶ್ಲೇಷಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ, ಕಾರಣವನ್ನು ನೀವೇ ಆಯ್ಕೆಮಾಡಿ.",
}

BLURRY_MESSAGE = {
    "en": "This photo looks blurry. Retake it if you can.",
    "kn": "ಈ ಫೋಟೋ ಮಸುಕಾಗಿದೆ. ಸಾಧ್ಯವಾದರೆ ಮತ್ತೆ ತೆಗೆಯಿರಿ.",
}

_GUIDANCE = {
    "en": {
        LABEL_PEST: [
            "Remove and destroy badly affected leaves or plants.",
            "Scout the plants around this spot before deciding on any treatment.",
            "Encourage natural enemies by avoiding broad-spectrum sprays where you can.",
            "Treat only the affected area if local advice says treatment is needed.",
        ],
        LABEL_DISEASE: [
            "Remove infected leaves and take them out of the field.",
            "Avoid working in the crop while the leaves are wet.",
            "Improve airflow and avoid overhead watering where you can.",
            "Ask a local expert to confirm the disease before treating.",
        ],
        LABEL_NUTRIENT: [
            "Get a soil test before adding any fertiliser.",
            "Check whether the pattern follows spreader or irrigation lines.",
            "Correct the cause evenly across the affected band.",
        ],
        LABEL_WATER: [
            "Check irrigation lines and emitters in this zone for blockages.",
            "Press the soil at root depth to confirm it is dry.",
            "Mulch to hold moisture if this zone keeps drying out.",
        ],
        LABEL_WEEDS: [
            "Remove weeds by hand or by hoeing before they set seed.",
            "Note the cause in the field record, so the next scan can be read in context.",
        ],
        LABEL_FALSE_ALARM: [
            "No action needed here.",
            "Move on to the next stop.",
        ],
    },
    "kn": {
        LABEL_PEST: [
            "ಹೆಚ್ಚು ಹಾನಿಗೊಳಗಾದ ಎಲೆಗಳು ಅಥವಾ ಗಿಡಗಳನ್ನು ತೆಗೆದು ನಾಶಮಾಡಿ.",
            "ಯಾವುದೇ ಚಿಕಿತ್ಸೆ ನಿರ್ಧರಿಸುವ ಮೊದಲು ಸುತ್ತಲಿನ ಗಿಡಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
            "ಸಾಧ್ಯವಾದಲ್ಲಿ ವ್ಯಾಪಕ ಸಿಂಪಡಣೆ ತಪ್ಪಿಸಿ ನೈಸರ್ಗಿಕ ಶತ್ರುಗಳನ್ನು ಉಳಿಸಿ.",
            "ಸ್ಥಳೀಯ ಸಲಹೆಯಂತೆ ಚಿಕಿತ್ಸೆ ಅಗತ್ಯವಿದ್ದರೆ ಹಾನಿಗೊಳಗಾದ ಭಾಗಕ್ಕೆ ಮಾತ್ರ ನೀಡಿ.",
        ],
        LABEL_DISEASE: [
            "ಸೋಂಕಿತ ಎಲೆಗಳನ್ನು ತೆಗೆದು ಹೊಲದಿಂದ ಹೊರಗೆ ಹಾಕಿ.",
            "ಎಲೆಗಳು ಒದ್ದೆಯಾಗಿರುವಾಗ ಬೆಳೆಯಲ್ಲಿ ಕೆಲಸ ಮಾಡಬೇಡಿ.",
            "ಸಾಧ್ಯವಾದಲ್ಲಿ ಗಾಳಿಯ ಸಂಚಾರ ಹೆಚ್ಚಿಸಿ ಮತ್ತು ಮೇಲಿನಿಂದ ನೀರು ಹಾಯಿಸುವುದನ್ನು ತಪ್ಪಿಸಿ.",
            "ಚಿಕಿತ್ಸೆಗೆ ಮೊದಲು ರೋಗವನ್ನು ಸ್ಥಳೀಯ ತಜ್ಞರಿಂದ ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ.",
        ],
        LABEL_NUTRIENT: [
            "ಗೊಬ್ಬರ ಹಾಕುವ ಮೊದಲು ಮಣ್ಣು ಪರೀಕ್ಷೆ ಮಾಡಿಸಿ.",
            "ಈ ಮಾದರಿ ಗೊಬ್ಬರ ಹರಡುವ ಅಥವಾ ನೀರಾವರಿ ಸಾಲುಗಳನ್ನು ಅನುಸರಿಸುತ್ತಿದೆಯೇ ನೋಡಿ.",
            "ಹಾನಿಗೊಳಗಾದ ಪಟ್ಟಿಯಲ್ಲಿ ಕಾರಣವನ್ನು ಸಮವಾಗಿ ಸರಿಪಡಿಸಿ.",
        ],
        LABEL_WATER: [
            "ಈ ಭಾಗದ ನೀರಾವರಿ ಸಾಲುಗಳು ಕಟ್ಟಿಕೊಂಡಿವೆಯೇ ಪರಿಶೀಲಿಸಿ.",
            "ಬೇರಿನ ಆಳದಲ್ಲಿ ಮಣ್ಣು ಒಣಗಿದೆಯೇ ಎಂದು ಒತ್ತಿ ನೋಡಿ.",
            "ಈ ಭಾಗ ಪದೇ ಪದೇ ಒಣಗಿದರೆ ತೇವಾಂಶ ಉಳಿಸಲು ಹೊದಿಕೆ ಹಾಕಿ.",
        ],
        LABEL_WEEDS: [
            "ಕಳೆಗಳು ಬೀಜ ಬಿಡುವ ಮೊದಲು ಕೈಯಿಂದ ಅಥವಾ ಗುದ್ದಲಿಯಿಂದ ತೆಗೆಯಿರಿ.",
            "ಮುಂದಿನ ಸ್ಕ್ಯಾನ್ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಕಾರಣವನ್ನು ಹೊಲದ ದಾಖಲೆಯಲ್ಲಿ ಬರೆಯಿರಿ.",
        ],
        LABEL_FALSE_ALARM: [
            "ಇಲ್ಲಿ ಯಾವುದೇ ಕ್ರಮದ ಅಗತ್ಯವಿಲ್ಲ.",
            "ಮುಂದಿನ ಸ್ಥಳಕ್ಕೆ ಹೋಗಿ.",
        ],
    },
}


def guidance_for(label: str, language: str = "en") -> dict:
    lang = language if language in _GUIDANCE else "en"
    return {
        "label": label,
        "label_name": LABEL_NAMES[lang][label],
        "actions": _GUIDANCE[lang][label],
        "advisory": ADVISORY[lang],
        "language": lang,
    }


def label_options(language: str = "en") -> list[dict]:
    lang = language if language in LABEL_NAMES else "en"
    return [{"label": label, "name": LABEL_NAMES[lang][label]} for label in LABELS]


# A diagnosis candidate type suggests a label, which the scout confirms or overrides.
CANDIDATE_TO_LABEL = {
    "pest": LABEL_PEST,
    "disease": LABEL_DISEASE,
    "nutrient": LABEL_NUTRIENT,
    "water": LABEL_WATER,
    "weeds_other": LABEL_WEEDS,
    "healthy": LABEL_FALSE_ALARM,
}
