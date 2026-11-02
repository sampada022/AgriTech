import math
from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel, Field
from typing import List

router = APIRouter(prefix="/flightplans", tags=["Flight Plan (P1)"])

class FlightPlanRequest(BaseModel):
    field_id: str = "f_01"
    altitude_m: float = Field(default=35.0, description="Flight altitude in meters AGL")
    overlap_front_pct: float = Field(default=75.0, description="Forward overlap percentage")
    overlap_side_pct: float = Field(default=70.0, description="Side overlap percentage")
    speed_ms: float = Field(default=5.0, description="Drone cruise speed in m/s")
    # Coordinates of bounding box: min_lon, min_lat, max_lon, max_lat
    bounds: List[float] = Field(
        default=[76.8198, 11.0165, 76.8228, 11.0189],
        description="[min_lon, min_lat, max_lon, max_lat]"
    )

def generate_lawnmower_grid(min_lon: float, min_lat: float, max_lon: float, max_lat: float, altitude_m: float, side_overlap_pct: float):
    """
    Computes a simple lawnmower (boustrophedon) path given sensor FOV assumptions:
    Sensor FOV ~ 60 degrees -> Ground footprint width ~ 1.15 * altitude
    Spacing between flight lines = Footprint * (1 - side_overlap)
    """
    footprint_width = 1.1547 * altitude_m
    line_spacing_m = max(5.0, footprint_width * (1.0 - side_overlap_pct / 100.0))

    # Approx meters per degree lat/lon at ~11 deg N
    lat_m_per_deg = 110600.0
    lon_m_per_deg = 111320.0 * math.cos(math.radians((min_lat + max_lat) / 2.0))

    line_spacing_lat = line_spacing_m / lat_m_per_deg
    
    waypoints = []
    curr_lat = min_lat
    direction = 1 # 1: west->east, -1: east->west

    seq = 1
    while curr_lat <= max_lat + (line_spacing_lat * 0.1):
        if direction == 1:
            waypoints.append((seq, min_lon, curr_lat, altitude_m))
            seq += 1
            waypoints.append((seq, max_lon, curr_lat, altitude_m))
            seq += 1
        else:
            waypoints.append((seq, max_lon, curr_lat, altitude_m))
            seq += 1
            waypoints.append((seq, min_lon, curr_lat, altitude_m))
            seq += 1
        direction *= -1
        curr_lat += line_spacing_lat

    return waypoints

@router.post("/kml")
def get_flightplan_kml(req: FlightPlanRequest = FlightPlanRequest()):
    """
    Outputs standard Google Earth / DJI Pilot compatible KML with 3D flight lines.
    """
    min_lon, min_lat, max_lon, max_lat = req.bounds
    wps = generate_lawnmower_grid(min_lon, min_lat, max_lon, max_lat, req.altitude_m, req.overlap_side_pct)

    coord_str = "\n".join([f"            {lon},{lat},{alt}" for _, lon, lat, alt in wps])

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>AeroScout Autonomous Flight Plan - {req.field_id}</name>
    <description>Lawnmower survey at {req.altitude_m}m AGL with {req.overlap_front_pct}% front / {req.overlap_side_pct}% side overlap</description>
    <Style id="dronePath">
      <LineStyle>
        <color>ff00ffff</color>
        <width>3</width>
      </LineStyle>
    </Style>
    <Placemark>
      <name>Survey Track</name>
      <styleUrl>#dronePath</styleUrl>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>
{coord_str}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

    return Response(
        content=kml,
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f"attachment; filename=aeroscout_flight_{req.field_id}.kml"}
    )

@router.post("/qgc")
def get_flightplan_qgroundcontrol(req: FlightPlanRequest = FlightPlanRequest()):
    """
    Outputs standard QGroundControl Waypoint (.wpl) / MAVLink mission format.
    Format:
    QGC WPL <VERSION>
    <INDEX> <CURRENT_WP> <COORD_FRAME> <COMMAND> <PARAM1> <PARAM2> <PARAM3> <PARAM4> <PARAM5/LAT> <PARAM6/LON> <PARAM7/ALT> <AUTOCONTINUE>
    """
    min_lon, min_lat, max_lon, max_lat = req.bounds
    wps = generate_lawnmower_grid(min_lon, min_lat, max_lon, max_lat, req.altitude_m, req.overlap_side_pct)

    lines = ["QGC WPL 110"]
    # 0 = Home waypoint
    lines.append(f"0\t1\t0\t16\t0\t0\t0\t0\t{min_lat:.8f}\t{min_lon:.8f}\t{req.altitude_m:.2f}\t1")
    
    # 16 = MAV_CMD_NAV_WAYPOINT
    for seq, lon, lat, alt in wps:
        lines.append(f"{seq}\t0\t3\t16\t0.000000\t0.000000\t0.000000\t0.000000\t{lat:.8f}\t{lon:.8f}\t{alt:.2f}\t1")

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=aeroscout_{req.field_id}.waypoints"}
    )

