from fastapi import APIRouter
from app.schemas import RouteRead, RouteRequest, RouteWaypoint
from app.mock_data import MOCK_HOTSPOTS
from app.route.planner import plan_field_route
from app.errors import AeroScoutError

router = APIRouter(tags=["Route"])

@router.post("/scans/{scan_id}/route", response_model=RouteRead)
def plan_route(scan_id: str, request: RouteRequest = RouteRequest()):
    hotspots = MOCK_HOTSPOTS.get(scan_id, [])
    if not hotspots:
        raise AeroScoutError(
            code="NO_HOTSPOTS_FOR_ROUTE",
            message=f"No hotspots found for scan '{scan_id}'.",
            hint="Run field scan analysis first.",
            status_code=400
        )

    # Simplified representation for planner
    formatted_hotspots = []
    for h in hotspots:
        formatted_hotspots.append({
            "id": h["id"],
            "rank": h["properties"]["rank"],
            "tier": h["properties"]["tier"],
            "area_m2": h["properties"]["area_m2"],
            "centroid": [h["geometry"]["coordinates"][0][0][0], h["geometry"]["coordinates"][0][0][1]]
        })

    start_lat = request.start[0] if request.start else 12.5205
    start_lon = request.start[1] if request.start else 76.8955

    route_res = plan_field_route(
        start_point={"lat": start_lat, "lon": start_lon, "label": "Start / Entry Point", "hotspot_id": None},
        hotspots=formatted_hotspots,
        mode=request.mode,
        include_abiotic=request.include_abiotic,
        field_area_m2=11000.0
    )

    waypoints = [
        RouteWaypoint(
            lat=w["lat"],
            lon=w["lon"],
            label=w["label"],
            hotspot_id=w.get("hotspot_id"),
            tier=w.get("tier"),
            rank=w.get("rank")
        )
        for w in route_res["waypoints"]
    ]

    return RouteRead(
        id=f"r_{scan_id}",
        scan_id=scan_id,
        mode=request.mode,
        ordered_hotspot_ids=route_res["ordered_hotspot_ids"],
        distance_m=route_res["distance_m"],
        eta_min=route_res["eta_min"],
        saved_pct=route_res["saved_pct"],
        baseline_m=route_res["baseline_m"],
        spray_area_pct=route_res["spray_area_pct"],
        waypoints=waypoints
    )
