from fastapi.staticfiles import StaticFiles

# Add demo static file serving for maps and imagery
import os
os.makedirs("demo", exist_ok=True)
app.mount("/demo", StaticFiles(directory="demo"), name="demo")

