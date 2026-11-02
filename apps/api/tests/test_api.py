from app.main import read_root
from app.routers.health import get_health

def test_health_endpoint():
    data = get_health()
    assert data["status"] == "ok"
    assert data["service"] == "AeroScout Core API"
    assert "llm" in data
    assert "basemap" in data

def test_root_endpoint():
    data = read_root()
    assert "AeroScout" in data["message"]
