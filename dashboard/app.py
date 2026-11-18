import os
import json
import time
import asyncio
from contextlib import asynccontextmanager
import uvicorn
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from data_service import get_dashboard_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")
CACHE_FILE = "/var/cache/rafmagn_dashboard.json"

_CACHE_DATA = None
_CACHE_TIME = 0

def load_disk_cache():
    global _CACHE_DATA, _CACHE_TIME
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _CACHE_DATA = json.load(f)
                _CACHE_TIME = os.path.getmtime(CACHE_FILE)
                print(f"Loaded disk cache from {CACHE_FILE} (timestamp {_CACHE_TIME})", flush=True)
        except Exception as e:
            print(f"Error loading disk cache: {e}", flush=True)

def save_disk_cache(data):
    try:
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, CACHE_FILE)
    except Exception as e:
        print(f"Error saving disk cache: {e}", flush=True)

async def background_worker():
    global _CACHE_DATA, _CACHE_TIME
    while True:
        try:
            print("Background worker starting fetch from Orkusalan and RARIK...", flush=True)
            data = await asyncio.to_thread(get_dashboard_data)
            if data and "home" in data:
                _CACHE_DATA = data
                _CACHE_TIME = time.time()
                save_disk_cache(data)
                print("Background worker successfully refreshed dashboard cache.", flush=True)
        except Exception as e:
            print(f"Background worker error: {e}", flush=True)
        await asyncio.sleep(900)  # Refresh every 15 minutes

async def homepage(request):
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)

async def api_dashboard_data(request):
    global _CACHE_DATA, _CACHE_TIME
    force = request.query_params.get("force") == "1"
    if not force:
        if _CACHE_DATA is not None:
            return JSONResponse(_CACHE_DATA)
        load_disk_cache()
        if _CACHE_DATA is not None:
            return JSONResponse(_CACHE_DATA)

    try:
        data = await asyncio.to_thread(get_dashboard_data)
        _CACHE_DATA = data
        _CACHE_TIME = time.time()
        save_disk_cache(data)
        return JSONResponse(_CACHE_DATA)
    except Exception as e:
        if _CACHE_DATA is not None:
            return JSONResponse(_CACHE_DATA)
        return JSONResponse({"error": str(e)}, status_code=500)

@asynccontextmanager
async def lifespan(app):
    load_disk_cache()
    task = asyncio.create_task(background_worker())
    try:
        yield
    finally:
        task.cancel()

routes = [
    Route("/", homepage),
    Route("/api/dashboard-data", api_dashboard_data),
]

app = Starlette(debug=False, routes=routes, lifespan=lifespan)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    print(f"Starting Scandinavian Electricity Dashboard at http://localhost:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False, app_dir=BASE_DIR)
