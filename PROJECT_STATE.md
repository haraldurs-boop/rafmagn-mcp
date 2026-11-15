# Project State: Icelandic Electricity Usage MCP Server & Dashboard (RARIK & Orkusalan)

## 1. Objective & Definition of "Done"
- **Objective:** Create a local Python MCP server and a Scandinavian light-mode Web Dashboard interfacing with:
  1. RARIK (`minarsidur.rarik.is`) for electricity consumption data and distribution invoices.
  2. Orkusalan (`minarsidur.orkusalan.is`) for billing, invoices, and granular AMR/MMR consumption data.
- **Definition of "Done":**
  - Fully verified reverse-engineered REST/GraphQL endpoints documented with sample schemas: **DONE**
  - Headed Playwright and CLI authentication helper (`auth_helper.py`) facilitating manual Icelandic Electronic ID (Rafræn skilríki) login, extracting session tokens/cookies, and storing them in `.auth_session.json`: **DONE**
  - FastMCP server (`server.py`) exposing tools (`get_electricity_usage`, `get_meters`, `get_invoices`, `check_auth_status`): **DONE**
  - Web Dashboard UI (Phase 5) comparing Heimilið and Sumarbústaðurinn: **DONE**
  - Deployed to home server `r8q` with systemd persistent services: **DONE**

## 2. Verified API Endpoints & Auth Mechanics

### RARIK (`minarsidur.rarik.is`)
- **Base URL:** `https://minarsidur.rarik.is`
- **Auth Scheme:** Cookie-based forms authentication via Signet (`.ASPXAUTH`, `ASP.NET_SessionId`, `.LRoles`).
- **Key Endpoints:**
  - Meter Overview: `GET /yfirlit/notkun/`
  - Reading History: `GET /yfirlit/notkun/nanar/notkunarsaga/`
  - Consumption Export: `POST /yfirlit/notkun/nanar/notkunarsaga/$MeterReading/ExportToExcel/`
  - Invoices List: `GET /yfirlit/reikningar/?nationalId={nationalId}`
  - Invoice PDF: `GET /yfirlit/$Invoice/GetInvoicePDF/?invoiceNr={invoiceNr}&nationalId={nationalId}`

### Orkusalan (`minarsidur.orkusalan.is`)
- **Base URL:** `https://minarsidur.orkusalan.is`
- **Auth Scheme:** Native REST flow (`POST /auth/start` + `GET /auth/poll`), session stored in `connect.sid` cookie.
- **Key Endpoints:**
  - Auth Start: `POST /auth/start` (`{"identifier": "<phone>", "method": "Sim"}`)
  - Auth Poll: `GET /auth/poll?authRequestId={<id>}`
  - User & Connections: `GET /_next/data/{buildId}/minar-sidur.json`
  - Consumption: `GET /api/user/consumption?configurationName={config}&timePeriod={Hourly|Daily|Monthly}&unitOfMesure=kWh&startDate={start}&endDate={end}`
  - Invoices: `GET /api/user/invoices?from={from}&to={to}&page=1&pageSize=100`

## 3. Server Deployment on `r8q`
- **Server Path:** `/opt/rafmagn-mcp`
- **Dashboard Service:** `rafmagn-dashboard.service`
  - URL: `http://192.168.68.87:8050` (or `http://r8q.local:8050`)
- **MCP Service:** `rafmagn-mcp.service`
  - SSE Endpoint: `http://192.168.68.87:8051/sse`
  - SSH Stdio Command: `ssh r8q /opt/rafmagn-mcp/.venv/bin/python3 /opt/rafmagn-mcp/server.py`

## 4. Current File Structure
```
rafmagn-mcp/
├── dashboard/
│   ├── app.py                  (Web server listening on 0.0.0.0:8050)
│   ├── data_service.py         (Metrics & YoY aggregation)
│   └── index.html              (Scandinavian minimalist UI)
├── docs/
│   ├── rarik_api_spec.md
│   └── orkusalan_api_spec.md
├── .env.example
├── auth_helper.py
├── server.py                   (FastMCP supporting stdio and SSE on port 8051)
├── test_server.py
├── README.md
└── PROJECT_STATE.md
```
