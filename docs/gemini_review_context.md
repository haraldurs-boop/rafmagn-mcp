# Icelandic Electricity & Utility MCP Project Review

## Context & Architecture
We have built a unified local Python FastMCP server and Web Dashboard interfacing with three Icelandic energy utilities:
1. **RARIK (`minarsidur.rarik.is`)**:
   - Manages the distribution grid and manual meter reading for the summer cottage (**Sumarbústaðurinn**, Meter `101-36815202`).
   - Authentication: ASP.NET Forms authentication cookies (`.ASPXAUTH`, `ASP.NET_SessionId`, `.LRoles`). Session lasts ~2-3 days.
   - Data mechanics: `/yfirlit/notkun/nanar/notkunarsaga/`, HTML table scraping, and XLSX export via `ExportToExcel`.
   - Characteristics: Cottage meter is MMR (Handvirkur mælir / áætluð og raunnotkun). Data arrives in monthly reading chunks or periodic settlement invoices.
2. **Orkusalan (`minarsidur.orkusalan.is`)**:
   - Retail electricity supplier for both the primary residence (**Heimilið**, Meter `200-6092777587`, AMR smart meter) and the cottage.
   - Authentication: Native REST flow (`/auth/start` + `/auth/poll`), session cookie `connect.sid`. Session lasts ~2-4 days.
   - Data mechanics: `GET /api/user/consumption?configurationName={config}&timePeriod={Hourly|Daily|Monthly}&unitOfMesure=kWh&startDate=...&endDate=...`
   - Characteristics: AMR meter (`Config_10619453`) provides full hourly resolution. MMR meter (`Config_10379380`) times out if `Hourly` is requested; only Daily/Monthly aggregations succeed.
3. **Veitur (`minarsidur.veitur.is`)**:
   - Distribution system operator for Heimilið (Electricity meter `62858`) and geothermal hot water provider (Meter `30968`).
   - Authentication: Next.js App Router session via Ísland.is / Auðkenni (`veitur-service.session-token`). Session TTL is 30 days.
   - Data mechanics: Next.js Server Components (RSC) serialized into `self.__next_f.push`. Both hourly and daily telemetry available.
4. **Services & Infrastructure**:
   - Running locally and deployed to home server `r8q` (`192.168.68.87`) via systemd (`rafmagn-mcp.service` on 8051, `rafmagn-dashboard.service` on 8050).
   - FastMCP server (`server.py`) exposing `get_electricity_usage`, `get_water_usage`, `get_meters`, `get_invoices`, `check_auth_status`.
   - `auth_helper.py` supporting CLI polling and headed Playwright login.

## Questions for Review:
1. **Setup & Code Architecture**:
   - Is our FastMCP + client module architecture clean, robust, and idiomatic for production/home automation?
   - How can we best handle session token expiration and renewal gracefully across all three providers?
2. **Data Pipeline & Reliability (Orkusalan & RARIK)**:
   - Are the data streams from Orkusalan and RARIK coming through well enough?
   - Given the inherent limitation of MMR (manual/settlement) meters vs AMR (telemetric smart meters), what are the best statistical practices for normalizing historical baseload, seasonal differences, and cost calculations?
   - How can we avoid timeouts and improve data resilience when external portals are slow or rotating build IDs?
