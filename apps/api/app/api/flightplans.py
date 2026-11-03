"""Flight-plan generator (F26)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.db import get_session
from app.errors import not_found
from app.models import FlightPlan, new_id
from app.schemas import FlightPlanCreate, FlightPlanOut
from app.services.flightplan import plan_flight, to_kml, to_qgc_waypoints

router = APIRouter(tags=["flight plans"])


def _payload(plan: FlightPlan) -> dict:
    return {
        "id": plan.id,
        "altitude_m": plan.altitude_m,
        "front_overlap": plan.front_overlap,
        "side_overlap": plan.side_overlap,
        "waypoints": plan.waypoints,
        "summary": plan.summary,
        "kml": plan.kml,
        "waypoint_file": plan.waypoint_file,
        "kml_url": f"/api/flightplans/{plan.id}/plan.kml",
        "waypoint_file_url": f"/api/flightplans/{plan.id}/plan.waypoints",
    }


@router.post(
    "/flightplans",
    response_model=FlightPlanOut,
    status_code=201,
    summary="Generate waypoints from a polygon",
)
def create_plan(body: FlightPlanCreate, session: Session = Depends(get_session)) -> dict:
    points = [(p.lat, p.lon) for p in body.polygon]
    plan = plan_flight(
        points, body.altitude_m, body.front_overlap, body.side_overlap, body.camera
    )
    row = FlightPlan(
        id=new_id("p"),
        polygon={"type": "Polygon", "coordinates": [[[lon, lat] for lat, lon in points]]},
        altitude_m=body.altitude_m,
        front_overlap=body.front_overlap,
        side_overlap=body.side_overlap,
        waypoints=plan["waypoints"],
        summary=plan["summary"],
        kml=to_kml(body.name, plan["waypoints"]),
        waypoint_file=to_qgc_waypoints(plan["waypoints"], plan["photo_spacing_m"]),
    )
    session.add(row)
    session.commit()
    return _payload(row)


def _download(session: Session, plan_id: str, attribute: str, media: str, name: str) -> Response:
    plan = session.get(FlightPlan, plan_id)
    if plan is None:
        raise not_found("Flight plan", plan_id)
    return Response(
        content=getattr(plan, attribute),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/flightplans/{plan_id}/plan.kml", summary="Download the KML", response_class=Response)
def get_kml(plan_id: str, session: Session = Depends(get_session)) -> Response:
    return _download(
        session, plan_id, "kml", "application/vnd.google-earth.kml+xml", f"{plan_id}.kml"
    )


@router.get(
    "/flightplans/{plan_id}/plan.waypoints",
    summary="Download the QGC waypoint file",
    response_class=Response,
)
def get_waypoints(plan_id: str, session: Session = Depends(get_session)) -> Response:
    return _download(session, plan_id, "waypoint_file", "text/plain", f"{plan_id}.waypoints")
