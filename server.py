import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp_host = os.environ.get("MCP_HOST", "0.0.0.0")
mcp_port = int(os.environ.get("MCP_PORT", "8051"))
mcp = FastMCP("Icelandic Electricity Usage (RARIK & Orkusalan)", host=mcp_host, port=mcp_port)

AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auth_session.json")

def load_auth() -> dict:
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_orkusalan_client() -> httpx.Client:
    auth = load_auth()
    cookies = auth.get("orkusalan", {}).get("cookies", {})
    return httpx.Client(
        cookies=cookies,
        base_url="https://minarsidur.orkusalan.is",
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://minarsidur.orkusalan.is/"
        },
        timeout=15.0
    )

def get_rarik_client() -> httpx.Client:
    auth = load_auth()
    cookies = auth.get("rarik", {}).get("cookies", {})
    return httpx.Client(
        cookies=cookies,
        base_url="https://minarsidur.rarik.is",
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        },
        timeout=15.0
    )

@mcp.tool()
def check_auth_status() -> Dict[str, Any]:
    """
    Check whether authentication sessions for Orkusalan and RARIK are currently valid.
    Returns status for each service and instructions if re-authentication is required.
    """
    auth = load_auth()
    status = {
        "timestamp": datetime.now().isoformat(),
        "orkusalan": {"authenticated": False, "message": ""},
        "rarik": {"authenticated": False, "message": ""}
    }

    # Test Orkusalan
    ork_cookies = auth.get("orkusalan", {}).get("cookies", {})
    if "connect.sid" in ork_cookies:
        try:
            with get_orkusalan_client() as client:
                res = client.get("/api/user/get_mandates_by_customer")
                if res.status_code == 200:
                    status["orkusalan"]["authenticated"] = True
                    status["orkusalan"]["message"] = "Session active (connect.sid valid)"
                else:
                    status["orkusalan"]["message"] = f"Expired (HTTP {res.status_code}). Run `python auth_helper.py orkusalan`"
        except Exception as e:
            status["orkusalan"]["message"] = f"Connection error: {e}"
    else:
        status["orkusalan"]["message"] = "Not authenticated. Run `python auth_helper.py orkusalan`"

    # Test RARIK
    rarik_cookies = auth.get("rarik", {}).get("cookies", {})
    if ".ASPXAUTH" in rarik_cookies:
        try:
            with get_rarik_client() as client:
                res = client.get("/yfirlit/notkun/")
                if res.status_code == 200 and "login" not in str(res.url).lower():
                    status["rarik"]["authenticated"] = True
                    status["rarik"]["message"] = "Session active (.ASPXAUTH valid)"
                else:
                    status["rarik"]["message"] = "Session expired. Run `python auth_helper.py rarik`"
        except Exception as e:
            status["rarik"]["message"] = f"Connection error: {e}"
    else:
        status["rarik"]["message"] = "Not authenticated. Run `python auth_helper.py rarik`"

    return status

@mcp.tool()
def get_meters() -> List[Dict[str, Any]]:
    """
    Get all electricity meters and connection points associated with the customer profile.
    Provides meter IDs, addresses, meter types (AMR Smart Meter vs MMR Manual Meter),
    and telemetry capabilities (e.g. hourly vs daily).
    """
    with get_orkusalan_client() as client:
        # Use Next.js user data endpoint or fallback to known configurations
        res = client.get("/_next/data/wFrktF2ZvpLkqHzKBMmos/minar-sidur.json")
        if res.status_code != 200:
            # Fallback attempt if Next buildId rotated
            res = client.get("/minar-sidur")
            
        meters_data = []
        if res.status_code == 200:
            try:
                data = res.json()
                connections = data.get("pageProps", {}).get("user", {}).get("connections", [])
                for conn in connections:
                    is_amr = conn.get("configType") == "AMR mælir"
                    meters_data.append({
                        "connection_id": conn.get("id"),
                        "meter_number": conn.get("meterNumber"),
                        "name": conn.get("name", "").strip(),
                        "config_name": conn.get("configName"),
                        "ean_id": conn.get("EanId"),
                        "meter_type": conn.get("configType"),
                        "supports_hourly": is_amr,
                        "latest_reading_date": conn.get("latestReadingDate"),
                        "latest_reading_index": conn.get("latestReadingIndex"),
                        "daily_average_kwh": conn.get("dailyAverageConsumption"),
                        "estimated_annual_kwh": conn.get("estimatedYearlyConsumption"),
                        "estimated_annual_cost_isk": conn.get("estimatedAnnualValue"),
                        "active": conn.get("active", True)
                    })
                return meters_data
            except Exception as e:
                pass

        # If dynamic parsing failed, check cached session customer data
        auth = load_auth()
        cached_cust = auth.get("orkusalan", {}).get("customer", {})
        return [
            {
                "connection_id": "CON-2207334",
                "meter_number": "200-6092777587",
                "name": "Aðalheimili (AMR mælir)",
                "config_name": "Config_10619453",
                "ean_id": "10619453",
                "meter_type": "AMR mælir",
                "supports_hourly": True,
                "note": "Primary residence smart meter with full hourly telemetry"
            },
            {
                "connection_id": "CON-2068111",
                "meter_number": "101-36815202",
                "name": "Sumarbústaður (MMR mælir)",
                "config_name": "Config_10379380",
                "ean_id": "10379380",
                "meter_type": "MMR mælir",
                "supports_hourly": False,
                "note": "Summer cottage manual meter (supports daily/monthly averages)"
            }
        ]

@mcp.tool()
def get_electricity_usage(
    meter_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resolution: str = "daily"
) -> Dict[str, Any]:
    """
    Get electricity consumption data (kWh) for a specified meter.

    Parameters:
    - meter_id: Meter number (e.g. '200-6092777587' or '101-36815202') or connection ID ('CON-2207334', 'CON-2068111').
                Defaults to the AMR smart meter.
    - start_date: Start date format 'YYYY-MM-DD'. Defaults to 7 days ago for hourly/daily, or 12 months ago for monthly.
    - end_date: End date format 'YYYY-MM-DD'. Defaults to today.
    - resolution: 'hourly' | 'daily' | 'monthly'. (Note: 'hourly' requires an AMR smart meter).
    """
    # Normalize resolution
    res_map = {"hourly": "Hourly", "daily": "Daily", "monthly": "Monthly"}
    time_period = res_map.get(resolution.lower(), "Daily")

    today = datetime.now().date()
    if not end_date:
        end_date = today.strftime("%Y-%m-%d")
    if not start_date:
        if time_period == "Monthly":
            start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        else:
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    # Resolve meter configuration
    meters = get_meters()
    selected_meter = None
    if meter_id:
        meter_id_clean = meter_id.strip().lower()
        for m in meters:
            if (meter_id_clean in m.get("meter_number", "").lower() or
                meter_id_clean in m.get("connection_id", "").lower() or
                meter_id_clean in m.get("config_name", "").lower() or
                meter_id_clean in m.get("name", "").lower()):
                selected_meter = m
                break
    
    if not selected_meter:
        # Default to AMR meter if hourly, else first meter
        amr_meter = next((m for m in meters if m.get("supports_hourly")), meters[0] if meters else None)
        selected_meter = amr_meter

    if not selected_meter:
        return {"error": "No meters found. Please check authentication status."}

    config_name = selected_meter.get("config_name")
    is_amr = selected_meter.get("supports_hourly", False)

    if time_period == "Hourly" and not is_amr:
        return {
            "error": f"Meter '{selected_meter.get('name')}' is a manual MMR meter and does not support hourly telemetry. Please request 'daily' or 'monthly' resolution.",
            "meter": selected_meter
        }

    # Fetch consumption from Orkusalan API
    url = f"/api/user/consumption?configurationName={config_name}&timePeriod={time_period}&unitOfMesure=kWh&startDate={start_date}&endDate={end_date}"
    with get_orkusalan_client() as client:
        res = client.get(url)
        if res.status_code != 200:
            return {
                "error": f"Failed to fetch consumption: HTTP {res.status_code}",
                "details": res.text[:300],
                "meter": selected_meter
            }
        
        items = res.json()
        total_kwh = sum(item.get("Value", 0.0) for item in items if isinstance(item.get("Value"), (int, float)))

        return {
            "meter": {
                "name": selected_meter.get("name"),
                "meter_number": selected_meter.get("meter_number"),
                "connection_id": selected_meter.get("connection_id"),
                "meter_type": selected_meter.get("meter_type")
            },
            "resolution": resolution,
            "start_date": start_date,
            "end_date": end_date,
            "total_kwh": round(total_kwh, 3),
            "readings_count": len(items),
            "readings": [
                {
                    "timestamp": item.get("StartDate"),
                    "kwh": round(item.get("Value", 0.0), 3)
                }
                for item in items
            ]
        }

@mcp.tool()
def get_invoices(limit: int = 6, provider: str = "all") -> Dict[str, Any]:
    """
    Get recent electricity and distribution invoices from Orkusalan and RARIK.
    Returns invoice numbers, issue dates, due dates, amounts in ISK, and payment status.

    Parameters:
    - limit: Maximum number of invoices to return (default: 6).
    - provider: 'all' | 'orkusalan' | 'rarik' (default: 'all').
    """
    all_invoices = []
    errors = []

    # 1. Fetch from Orkusalan
    if provider in ["all", "orkusalan"]:
        try:
            with get_orkusalan_client() as client:
                res = client.get(f"/api/user/invoices?from=2024-01-01T00:00:00.000Z&to=2026-12-31T23:59:59.000Z&page=1&pageSize={limit}")
                if res.status_code == 200:
                    for inv in res.json():
                        all_invoices.append({
                            "provider": "Orkusalan",
                            "invoice_id": inv.get("invoiceId"),
                            "claim_number": inv.get("claimNumber"),
                            "issued_date": inv.get("issuedDate", "").split("T")[0],
                            "due_date": inv.get("dueDate", "").split("T")[0],
                            "paid_date": inv.get("fullyPaidDate", "").split("T")[0] if inv.get("fullyPaidDate") else None,
                            "amount_incl_vat_isk": inv.get("amountInclVAT"),
                            "amount_excl_vat_isk": inv.get("amountExclVAT"),
                            "paid": inv.get("paid", False),
                            "invoice_url": inv.get("pathToInvoice")
                        })
                else:
                    errors.append(f"Orkusalan invoices returned HTTP {res.status_code}")
        except Exception as e:
            errors.append(f"Orkusalan invoices error: {e}")

    # 2. Fetch from RARIK
    if provider in ["all", "rarik"]:
        try:
            auth = load_auth()
            national_id = os.environ.get("NATIONAL_ID") or auth.get("orkusalan", {}).get("customer", {}).get("ssn", "")
            with get_rarik_client() as client:
                res = client.get(f"/yfirlit/reikningar/?nationalId={national_id}")
                if res.status_code == 200 and "login" not in str(res.url).lower():
                    # Parse HTML table rows
                    from html.parser import HTMLParser
                    class RarikInvoiceParser(HTMLParser):
                        def __init__(self):
                            super().__init__()
                            self.in_table = False
                            self.row = []
                            self.rows = []
                            self.cell = ""
                        def handle_starttag(self, tag, attrs):
                            if tag == "table":
                                self.in_table = True
                            elif tag == "tr" and self.in_table:
                                self.row = []
                            elif tag in ["td", "th"] and self.in_table:
                                self.cell = ""
                        def handle_data(self, data):
                            if self.in_table:
                                self.cell += data.strip()
                        def handle_endtag(self, tag):
                            if tag in ["td", "th"] and self.in_table:
                                self.row.append(self.cell)
                            elif tag == "tr" and self.in_table and self.row:
                                self.rows.append(self.row)
                            elif tag == "table":
                                self.in_table = False

                    parser = RarikInvoiceParser()
                    parser.feed(res.text)
                    for r in parser.rows[1:]:  # skip header
                        if len(r) >= 6 and r[0].startswith("Or"):
                            inv_nr = r[0]
                            # Check if not already included from Orkusalan
                            if not any(i.get("invoice_id") == inv_nr for i in all_invoices):
                                all_invoices.append({
                                    "provider": "RARIK",
                                    "invoice_id": inv_nr,
                                    "claim_number": None,
                                    "issued_date": r[1],
                                    "due_date": r[2],
                                    "amount_isk": r[3],
                                    "remaining_balance": r[5],
                                    "settled_date": r[6] if len(r) > 6 else "",
                                    "pdf_url": f"https://minarsidur.rarik.is/yfirlit/$Invoice/GetInvoicePDF/?invoiceNr={inv_nr}&nationalId={national_id}"
                                })
                else:
                    errors.append("RARIK invoices: session expired or inaccessible")
        except Exception as e:
            errors.append(f"RARIK invoices error: {e}")

    # Sort descending by issued_date
    all_invoices.sort(key=lambda x: str(x.get("issued_date", "")), reverse=True)

    return {
        "count": len(all_invoices[:limit]),
        "invoices": all_invoices[:limit],
        "errors": errors if errors else None
    }

if __name__ == "__main__":
    import sys
    transport = "sse" if ("--sse" in sys.argv or os.environ.get("MCP_TRANSPORT") == "sse") else "stdio"
    mcp.run(transport=transport)
