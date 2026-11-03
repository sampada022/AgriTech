"""Model versions, label handling, re-scoring and re-ranking (TRD 6.7, F16)."""

from __future__ import annotations

import threading

import numpy as np
from sqlmodel import Session, select

from app.diagnosis.guidance import (
    ABIOTIC_LABELS,
    BIOTIC_LABELS,
    LABEL_FALSE_ALARM,
    guidance_for,
)
from app.engine.scoring import (
    CUE_NAMES,
    PRIOR_BIAS,
    PRIOR_WEIGHTS,
    TIER_GREY,
    TIER_ORDER,
    TIER_RED,
    ScoringModel,
    agreement,
    normalise,
    refit,
    score_hotspot,
)
from app.models import (
    RESOLVED_STATUSES,
    SCAN_DONE,
    STATUS_CLEARED,
    STATUS_CONFIRMED,
    FieldRecord,
    Hotspot,
    ModelVersion,
    Observation,
    Scan,
    utcnow,
)
from app.services.routes import refresh_kpis, replan_from_previous, route_payload, scan_hotspots

# Serialises label, threshold and reset operations, which read and then rewrite many rows.
MUTATION_LOCK = threading.RLock()

FALSE_POSITIVE_HINT_AT = 3
RECALIBRATION_NOTE = (
    "A prior-regularised nudge to seven weights from a few confirmed labels, not trained learning. "
    "Show the weight changes so people can see exactly what moved."
)


def _weights_dict(weights: np.ndarray) -> dict[str, float]:
    return {name: float(value) for name, value in zip(CUE_NAMES, weights)}


def _weights_array(weights: dict[str, float]) -> np.ndarray:
    return np.array([weights[name] for name in CUE_NAMES], dtype=np.float64)


def ensure_prior(session: Session) -> ModelVersion:
    """v1 is always the priors. It exists before any label does."""
    row = session.exec(select(ModelVersion).where(ModelVersion.version == 1)).first()
    if row is None:
        row = ModelVersion(version=1, weights=_weights_dict(PRIOR_WEIGHTS), bias=PRIOR_BIAS)
        session.add(row)
        session.commit()
    return row


def active_version(session: Session) -> ModelVersion:
    rows = session.exec(select(ModelVersion)).all()
    if not rows:
        return ensure_prior(session)
    return max(rows, key=lambda r: r.version)


def to_scoring_model(row: ModelVersion) -> ScoringModel:
    return ScoringModel(_weights_array(row.weights), row.bias, row.version)


def active_model(session: Session) -> ScoringModel:
    return to_scoring_model(active_version(session))


def training_set(session: Session) -> tuple[np.ndarray, np.ndarray]:
    """One row per hotspot whose current label trains the score. False alarms do not."""
    observations = session.exec(
        select(Observation).where(Observation.in_training == True)  # noqa: E712
    ).all()
    hotspot_ids = {o.hotspot_id for o in observations if o.label is not None}
    rows, labels = [], []
    for hotspot_id in sorted(hotspot_ids):
        hotspot = session.get(Hotspot, hotspot_id)
        if hotspot is None or not hotspot.cues:
            continue
        if hotspot.label in BIOTIC_LABELS:
            labels.append(1.0)
        elif hotspot.label in ABIOTIC_LABELS:
            labels.append(0.0)
        else:
            continue
        rows.append(normalise(hotspot.cues))
    if not rows:
        return np.empty((0, len(CUE_NAMES))), np.empty(0)
    return np.stack(rows), np.array(labels)


def false_positive_summary(session: Session) -> dict:
    count = len(
        session.exec(
            select(Observation).where(
                Observation.label == LABEL_FALSE_ALARM,
                Observation.in_training == True,  # noqa: E712
            )
        ).all()
    )
    suggest = count >= FALSE_POSITIVE_HINT_AT
    return {
        "count": count,
        "suggest_raise_threshold": suggest,
        "hint": (
            "Several hotspots were false alarms. Consider raising the sensitivity threshold."
            if suggest
            else None
        ),
    }


def rerank_scan(session: Session, scan_id: str) -> None:
    """Open hotspots first, by tier, evidence and size. Resolved hotspots sink to the bottom."""
    hotspots = session.exec(select(Hotspot).where(Hotspot.scan_id == scan_id)).all()

    def key(h: Hotspot) -> tuple:
        return (
            h.status in RESOLVED_STATUSES,
            TIER_ORDER.get(h.tier, 99),
            -round(h.biotic_score, 6),
            -h.area_m2,
            h.id,
        )

    for rank, hotspot in enumerate(sorted(hotspots, key=key), start=1):
        if hotspot.rank != rank:
            hotspot.previous_rank = hotspot.rank
            hotspot.rank = rank
        session.add(hotspot)


def apply_score(hotspot: Hotspot, model: ScoringModel, quality: float) -> None:
    score = score_hotspot(
        model, hotspot.cues, hotspot.mean_anomaly, hotspot.tile_count, quality
    )
    if score.tier != hotspot.tier:
        hotspot.previous_tier = hotspot.tier
    hotspot.biotic_score = score.biotic_score
    hotspot.hotspot_class = score.hotspot_class
    hotspot.tier = score.tier
    hotspot.confidence_score = score.confidence_score
    hotspot.confidence = score.confidence
    hotspot.contributions = score.contributions
    hotspot.abiotic_hint = score.abiotic_hint


def rescore_all(session: Session, model: ScoringModel) -> None:
    """Re-score every unlabelled hotspot on every finished scan, then re-rank."""
    scans = session.exec(select(Scan).where(Scan.status == SCAN_DONE)).all()
    for scan in scans:
        quality = scan.quality_score if scan.quality_score is not None else 1.0
        for hotspot in session.exec(select(Hotspot).where(Hotspot.scan_id == scan.id)).all():
            if hotspot.label is None and hotspot.cues:
                apply_score(hotspot, model, quality)
                session.add(hotspot)
        rerank_scan(session, scan.id)
        scan.version_used = model.version
        session.add(scan)
    session.flush()


def _snapshot(session: Session, scan_id: str) -> dict[str, dict]:
    return {
        h.id: {"tier": h.tier, "rank": h.rank, "biotic_score": round(h.biotic_score, 3)}
        for h in scan_hotspots(session, scan_id)
    }


def _diff(before: dict[str, dict], after: dict[str, dict]) -> list[dict]:
    """What changed on screen. Tiny score drift is left out so the UI animates real changes."""
    changes = []
    for hotspot_id, now in after.items():
        was = before.get(hotspot_id)
        if was is None:
            continue
        if (
            was["tier"] != now["tier"]
            or was["rank"] != now["rank"]
            or abs(was["biotic_score"] - now["biotic_score"]) >= 0.01
        ):
            changes.append({"hotspot_id": hotspot_id, "before": was, "after": now})
    return sorted(changes, key=lambda c: c["after"]["rank"])


def _new_version(session: Session, parent: ModelVersion) -> ModelVersion:
    features, labels = training_set(session)
    weights, bias = refit(features, labels)
    candidate = ScoringModel(weights, bias, parent.version + 1)
    row = ModelVersion(
        version=candidate.version,
        weights=_weights_dict(weights),
        bias=float(bias),
        label_count=int(len(labels)),
        agreement=agreement(candidate, features, labels),
        parent_version=parent.version,
    )
    session.add(row)
    session.flush()
    return row


def confirm_observation(
    session: Session, observation: Observation, label: str, note: str | None
) -> dict:
    """The closed loop: save the label, refit, re-score the rest, re-plan the walk."""
    with MUTATION_LOCK:
        hotspot = session.get(Hotspot, observation.hotspot_id)
        scan = session.get(Scan, hotspot.scan_id)
        field = session.get(FieldRecord, scan.field_id)
        before = _snapshot(session, scan.id)
        parent = active_version(session)

        previous_label = hotspot.label
        trainable = BIOTIC_LABELS | ABIOTIC_LABELS
        needs_refit = previous_label != label and (
            label in trainable or previous_label in trainable
        )

        observation.label = label
        observation.confirmed_at = utcnow()
        observation.in_training = True
        if note is not None:
            observation.note = note
        hotspot.label = label
        hotspot.previous_tier = hotspot.tier
        if label == LABEL_FALSE_ALARM:
            hotspot.status = STATUS_CLEARED
        else:
            hotspot.status = STATUS_CONFIRMED
            # The tier now states what the ground check found. Score and class stay as predicted,
            # which is what agreement is measured against.
            hotspot.tier = TIER_RED if label in BIOTIC_LABELS else TIER_GREY
        session.add(observation)
        session.add(hotspot)
        session.flush()

        current = parent
        if needs_refit:
            current = _new_version(session, parent)
        rescore_all(session, to_scoring_model(current))

        # The scout is standing at this hotspot, so the rest of the walk starts here. Using the
        # hotspot rather than GPS keeps the re-route sensible indoors or with a poor fix.
        route = replan_from_previous(
            session, scan, field, start=(hotspot.centroid_lat, hotspot.centroid_lon)
        )
        kpis = refresh_kpis(session, scan, field)
        session.commit()

        payload = {
            "observation_id": observation.id,
            "hotspot_id": hotspot.id,
            "label": label,
            "model": {
                "version": current.version,
                "previous_version": parent.version,
                "changed": current.version != parent.version,
                "label_count": current.label_count,
                "agreement": current.agreement,
                "note": RECALIBRATION_NOTE,
                "weight_changes": {
                    name: {
                        "before": round(parent.weights[name], 3),
                        "after": round(current.weights[name], 3),
                    }
                    for name in CUE_NAMES
                },
            },
            "changes": _diff(before, _snapshot(session, scan.id)),
            "route": route_payload(session, route),
            "kpis": kpis,
            "false_positive": false_positive_summary(session),
            "guidance": guidance_for(label, observation.language),
        }
        return payload


def reset_model(session: Session) -> ModelVersion:
    """Back to priors for rehearsal. Labels stay on record but stop training."""
    with MUTATION_LOCK:
        prior = ensure_prior(session)
        for row in session.exec(select(ModelVersion).where(ModelVersion.version != 1)).all():
            session.delete(row)
        for observation in session.exec(select(Observation)).all():
            observation.in_training = False
            session.add(observation)
        session.flush()
        rescore_all(session, to_scoring_model(prior))
        for scan in session.exec(select(Scan).where(Scan.status == SCAN_DONE)).all():
            field = session.get(FieldRecord, scan.field_id)
            if field is not None:
                replan_from_previous(session, scan, field)
                refresh_kpis(session, scan, field)
        session.commit()
        return prior


def model_payload(session: Session) -> dict:
    row = active_version(session)
    return {
        "version": row.version,
        "weights": row.weights,
        "bias": row.bias,
        "prior_weights": _weights_dict(PRIOR_WEIGHTS),
        "prior_bias": PRIOR_BIAS,
        "is_prior": row.version == 1,
        "label_count": row.label_count,
        "agreement": row.agreement,
        "agreement_note": "Training-set agreement on labelled hotspots, not accuracy.",
        "recalibration_note": RECALIBRATION_NOTE,
        "false_positive": false_positive_summary(session),
    }
