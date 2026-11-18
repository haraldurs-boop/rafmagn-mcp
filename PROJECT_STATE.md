# Project State: Icelandic Electricity & Utility MCP Server & Dashboard (RARIK, Orkusalan & Veitur)

## 1. Objective & Definition of "Done"
- **Objective:** Create a unified local Python MCP server and a Scandinavian light-mode Web Dashboard interfacing with:
  1. **RARIK (`minarsidur.rarik.is`)** for cottage electricity consumption and distribution invoices.
  2. **Orkusalan (`minarsidur.orkusalan.is`)** for retail electricity billing, invoices, and granular AMR/MMR consumption.
  3. **Veitur (`minarsidur.veitur.is`)** for primary residence electricity distribution, geothermal hot water (`m³`), and utility claims.
- **Definition of "Done":**
  - Fully verified reverse-engineered REST/RSC endpoints documented with sample schemas: **DONE**
  - Headed Playwright and CLI authentication helper (`auth_helper.py`) facilitating manual Icelandic Electronic ID (Rafræn skilríki) login for RARIK, Orkusalan, and Veitur: **DONE**
  - FastMCP server (`server.py`) exposing tools (`get_electricity_usage`, `get_water_usage`, `get_meters`, `get_invoices`, `check_auth_status`): **DONE**
  - Local SQLite telemetry database (`database.py` / `telemetry.db`) in WAL mode persisting all meter metadata, historical consumption (hourly/daily/monthly), and claims independently of cookie timeouts: **DONE**
  - Data modeling accuracy fixes (removed fabricated cottage daily spikes; flagged MMR meters as monthly-averaged uniform distribution; strictly differentiated retail electricity [Orkusalan] vs distribution [Veitur / RARIK] vs geothermal hot water [Veitur]): **DONE**
  - Web Dashboard UI comparing Heimilið and Sumarbústaðurinn with hot water telemetry and invoices: **DONE**
  - Deployed to home server `r8q` (`192.168.68.87`) with systemd persistent services: **DONE**

---

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

### Veitur (`minarsidur.veitur.is`)
- **Base URL:** `https://minarsidur.veitur.is`
- **Auth Scheme:** Next.js App Router session via Ísland.is / Auðkenni (`veitur-service.session-token`).
- **Key Endpoints:**
  - Session Check: `GET /api/auth/session`
  - Overview & Meters: `GET /yfirlit`
  - Electricity Consumption: `GET /notkun/rafmagn?meter={meterId}&period={day|month|last12Months}&date={YYYY-MM-DD}`
  - Hot Water Consumption: `GET /notkun/heitt-vatn?meter={meterId}&period={day|month|last12Months}&date={YYYY-MM-DD}`
  - Claims & Invoices: `GET /reikningar`
  - Invoice PDF Download: `GET /reikningar/krofur/download?token={documentReferenceToken}`

---

## 3. Server Deployment on `r8q`
- **Server Path:** `/opt/rafmagn-mcp`
- **Dashboard Service:** `rafmagn-dashboard.service`
  - URL: `http://192.168.68.87:8050` (or `http://r8q.local:8050`)
- **MCP Service:** `rafmagn-mcp.service`
  - SSE Endpoint: `http://192.168.68.87:8051/sse`
  - SSH Stdio Command: `ssh r8q /opt/rafmagn-mcp/.venv/bin/python3 /opt/rafmagn-mcp/server.py`

---

## 4. Current File Structure
```
rafmagn-mcp/
├── dashboard/
│   ├── app.py                  (Web server listening on 0.0.0.0:8050)
│   ├── data_service.py         (Metrics & YoY aggregation with Veitur data & MMR indicators)
│   └── index.html              (Scandinavian minimalist UI with provider role badges)
├── docs/
│   ├── rarik_api_spec.md
│   ├── orkusalan_api_spec.md
│   ├── veitur_api_spec.md
│   └── sumarbus_notkunarsaga.md
├── .env.example
├── auth_helper.py              (Multi-provider auth CLI & headed Playwright)
├── database.py                 (SQLite telemetry & invoice persistence in WAL mode)
├── veitur_client.py            (Veitur RSC telemetry & claim parser with SQLite storage)
├── inspect_veitur.py           (Veitur discovery tool)
├── server.py                   (FastMCP supporting stdio and SSE on port 8051 with DB fallback)
├── test_server.py              (Integration test suite)
├── README.md
└── PROJECT_STATE.md
```

---

## 5. Next Steps
- When RARIK / Orkusalan sessions expire, renew with `python auth_helper.py all`.
- Optional: Add cold water (kaldavatn / fráveita) tariff metrics if metered.
