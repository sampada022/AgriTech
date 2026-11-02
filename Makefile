PYTHON = C:\tools\python311\python.exe
UVICORN = C:\tools\python311\Scripts\uvicorn.exe
PYTEST = C:\tools\python311\Scripts\pytest.exe
NODE = C:\tools\node_full\node-v20.15.0-win-x64\node.exe
NPM = C:\tools\node_full\node-v20.15.0-win-x64\npm.cmd

.PHONY: dev dev-api dev-web demo test seed reset health

dev-api:
	cd apps/api && $(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

dev-web:
	cd apps/web && $(NPM) run dev

dev:
	powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd apps/api; $(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload'; Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd apps/web; $(NPM) run dev'"

demo:
	powershell -Command "$$env:DEMO_MODE='1'; $$env:DEMO_FORCE_CACHED_AI='1'; Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd apps/api; $(UVICORN) app.main:app --host 0.0.0.0 --port 8000'; Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd apps/web; $(NPM) run dev'"

test:
	cd apps/api && $(PYTEST) tests/ -v

seed:
	$(PYTHON) -m app.sim.generate --scenario mixed --seed 42 --difficulty medium

reset:
	powershell -Command "Remove-Item -Recurse -Force data/* -ErrorAction SilentlyContinue; Write-Output 'Database and cache reset complete.'"

health:
	$(PYTHON) -c "import urllib.request, json; res = urllib.request.urlopen('http://localhost:8000/api/health'); print(json.dumps(json.loads(res.read()), indent=2))"

