import os
import json
import uvicorn
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from data_service import get_dashboard_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

async def homepage(request):
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)

async def api_dashboard_data(request):
    data = get_dashboard_data()
    return JSONResponse(data)

routes = [
    Route("/", homepage),
    Route("/api/dashboard-data", api_dashboard_data),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    print(f"Starting Scandinavian Electricity Dashboard at http://localhost:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False, app_dir=BASE_DIR)
