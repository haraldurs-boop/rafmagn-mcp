# Icelandic Electricity Usage MCP Server (RARIK & Orkusalan)

A Model Context Protocol (MCP) server providing real-time electricity consumption telemetry, meter configuration, and billing data from **RARIK** (`minarsidur.rarik.is`) and **Orkusalan** (`minarsidur.orkusalan.is`).

## Features
- **Hourly Telemetry:** Granular hourly electricity consumption (kWh) for AMR smart meters.
- **Daily / Monthly Summaries:** Daily and monthly aggregates for both AMR and MMR meters.
- **Meter Inventory:** Multi-property overview (primary residence, summer cottage) with meter IDs and capabilities.
- **Billing & Invoices:** Real-time retrieval of invoices, due dates, settlement status, and PDF links.
- **Auth Helper:** Automated CLI and Playwright authentication helper for Icelandic Electronic ID (Rafræn skilríki).

## Setup & Installation

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install "mcp<2" httpx playwright
   playwright install chromium
   ```

2. Authentication:
   Run the auth helper to log in via Rafræn skilríki:
   ```bash
   # Check session status
   python auth_helper.py status

   # Authenticate Orkusalan (direct phone prompt)
   python auth_helper.py orkusalan

   # Authenticate RARIK (opens headed browser for Signet login)
   python auth_helper.py rarik
   ```

3. Run the MCP Server:
   ```bash
   python server.py
   ```

## MCP Tools Exposed

### `get_meters`
Returns all registered meters and connection points:
```json
[
  {
    "connection_id": "CON-2207334",
    "meter_number": "200-6092777587",
    "name": "Dæmigata 1, 200 Kópavogi",
    "meter_type": "AMR mælir",
    "supports_hourly": true,
    "daily_average_kwh": 14.48,
    "estimated_annual_kwh": 5285
  },
  {
    "connection_id": "CON-2068111",
    "meter_number": "101-36815202",
    "name": "Dæmivegur 10 sumarhús, 805 Selfossi",
    "meter_type": "MMR mælir",
    "supports_hourly": false,
    "daily_average_kwh": 17.33,
    "estimated_annual_kwh": 6324
  }
]
```

### `get_electricity_usage`
Retrieves kWh consumption for a given time window and resolution:
- `meter_id`: Meter number or connection ID (defaults to AMR smart meter).
- `start_date`: 'YYYY-MM-DD'
- `end_date`: 'YYYY-MM-DD'
- `resolution`: `'hourly'` | `'daily'` | `'monthly'`

### `get_invoices`
Fetches recent invoices from Orkusalan and RARIK:
- `limit`: Maximum number of invoices (default: 6).
- `provider`: `'all'` | `'orkusalan'` | `'rarik'`.

### `check_auth_status`
Reports validity of stored session cookies and notifies if renewal is needed.
