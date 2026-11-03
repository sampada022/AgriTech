def test_backend_sanity():
    import app.main
    assert app.main.app.title == "AeroScout API"

def test_config_defaults():
    from app.config import settings
    assert settings.PORT == 8000
    assert settings.demo_mode is True
