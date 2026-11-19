import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
from mcp.server.fastmcp import FastMCP
from veitur_client import (
    get_veitur_client,
    check_veitur_auth,
    get_veitur_consumption,
    get_veitur_invoices
)
from database import (
    save_meter,
    save_readings,
    get_readings,
    save_invoices,
    get_invoices_from_db
)

# Initialize FastMCP Server
mcp_host = os.environ.get("MCP_HOST", "0.0.0.0")
mcp_port = int(os.environ.get("MCP_PORT", "8051"))
mcp = FastMCP("Icelandic Utility Usage (RARIK, Orkusalan & Veitur)", host=mcp_host, port=mcp_port)

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

def _normalize_date(d_str: str) -> str:
    """Normalize date strings (e.g. '02.11.2026' or '2026-11-02T00:00:00') to 'YYYY-MM-DD'."""
    if not d_str:
        return ""
    d_clean = d_str.strip()
    if "." in d_clean:
        parts = d_clean.split(".")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return d_clean[:10]

@mcp.tool()
def check_auth_status() -> Dict[str, Any]:
    """
    Check whether authentication sessions for Orkusalan, RARIK, and Veitur are currently valid.
    Returns status for each service and instructions if re-authentication is required.
    """
    auth = load_auth()
    status = {
        "timestamp": datetime.now().isoformat(),
        "orkusalan": {"authenticated": False, "message": ""},
        "rarik": {"authenticated": False, "message": ""},
        "veitur": {"authenticated": False, "message": ""}
    }

    # 1. Test Orkusalan
    ork_cookies = auth.get("orkusalan", {}).get("cookies", {})
    if "connect.sid" in ork_cookies:
        try:
            with httpx.Client(
                cookies=ork_cookies,
                base_url="https://minarsidur.orkusalan.is",
                follow_redirects=False,
                timeout=5.0,
                headers={"User-Agent": "Mozilla/5.0"}
            ) as client:
                res = client.get("/minar-sidur")
                if res.status_code == 200:
                    status["orkusalan"]["authenticated"] = True
                    status["orkusalan"]["message"] = "Session active (connect.sid valid)"
                else:
                    status["orkusalan"]["message"] = f"Session expired (HTTP {res.status_code}). Run `python auth_helper.py orkusalan`"
        except Exception as e:
            status["orkusalan"]["message"] = f"Connection error: {e}"
    else:
        status["orkusalan"]["message"] = "Not authenticated. Run `python auth_helper.py orkusalan`"

    # 2. Test RARIK
    rarik_cookies = auth.get("rarik", {}).get("cookies", {})
    if ".ASPXAUTH" in rarik_cookies:
        try:
            with get_rarik_client() as client:
                res = client.get("/yfirlit/notkun/")
                url_lower = str(res.url).lower()
                if res.status_code == 200 and "login" not in url_lower and "innskraning" not in url_lower:
                    status["rarik"]["authenticated"] = True
                    status["rarik"]["message"] = "Session active (.ASPXAUTH valid)"
                else:
                    status["rarik"]["message"] = "Session expired. Run `python auth_helper.py rarik`"
        except Exception as e:
            status["rarik"]["message"] = f"Connection error: {e}"
    else:
        status["rarik"]["message"] = "Not authenticated. Run `python auth_helper.py rarik`"

    # 3. Test Veitur
    v_status = check_veitur_auth()
    if v_status.get("authenticated"):
        user_name = v_status.get("user", {}).get("name", "Active")
        status["veitur"]["authenticated"] = True
        status["veitur"]["message"] = f"Session active ({user_name})"
    else:
        status["veitur"]["message"] = f"Not authenticated ({v_status.get('error', 'expired')}). Run `python auth_helper.py veitur`"

    return status

@mcp.tool()
def get_meters() -> List[Dict[str, Any]]:
    """
    Get all electricity and utility meters associated with the customer profile across
    Orkusalan, RARIK, and Veitur.
    Provides meter IDs, utility types (Electricity Retail vs Distribution vs Hot Water), addresses, and capabilities.
    """
    meters_data = []

    # 1. Fetch Orkusalan meters dynamically
    try:
        with get_orkusalan_client() as client:
            # Dynamically resolve buildId from HTML instead of hardcoded hash
            build_id = "wFrktF2ZvpLkqHzKBMmos"
            r_page = client.get("/minar-sidur")
            if r_page.status_code == 200:
                m_build = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r_page.text)
                if m_build:
                    try:
                        next_data = json.loads(m_build.group(1))
                        build_id = next_data.get("buildId", build_id)
                    except Exception:
                        pass

            res = client.get(f"/_next/data/{build_id}/minar-sidur.json")
            if res.status_code == 200:
                data = res.json()
                connections = data.get("pageProps", {}).get("user", {}).get("connections", [])
                for conn in connections:
                    is_amr = conn.get("configType") == "AMR mælir"
                    m_obj = {
                        "provider": "Orkusalan",
                        "utility": "electricity_retail",
                        "role": "Raforkusali (Orkusala)",
                        "connection_id": conn.get("id"),
                        "meter_number": conn.get("meterNumber"),
                        "name": conn.get("name", "").strip(),
                        "config_name": conn.get("configName"),
                        "ean_id": conn.get("EanId"),
                        "meter_type": conn.get("configType"),
                        "supports_hourly": is_amr,
                        "unit": "kWh",
                        "latest_reading_date": conn.get("latestReadingDate"),
                        "latest_reading_index": conn.get("latestReadingIndex"),
                        "daily_average_kwh": conn.get("dailyAverageConsumption"),
                        "estimated_annual_kwh": conn.get("estimatedYearlyConsumption"),
                        "estimated_annual_cost_isk": conn.get("estimatedAnnualValue"),
                        "active": conn.get("active", True)
                    }
                    meters_data.append(m_obj)
                    save_meter(m_obj)
    except Exception:
        pass

    if not meters_data:
        # Fallback to known Orkusalan meters
        fallback_ork = [
            {
                "provider": "Orkusalan",
                "utility": "electricity_retail",
                "role": "Raforkusali (Orkusala)",
                "connection_id": "CON-2207334",
                "meter_number": "200-6092777587",
                "name": "Heimilið - Raforkusala (Orkusalan)",
                "config_name": "Config_10619453",
                "ean_id": "10619453",
                "meter_type": "AMR mælir",
                "supports_hourly": True,
                "unit": "kWh",
                "note": "Primary residence smart meter retail electricity"
            },
            {
                "provider": "Orkusalan",
                "utility": "electricity_retail",
                "role": "Raforkusali (Orkusala)",
                "connection_id": "CON-2068111",
                "meter_number": "101-36815202",
                "name": "Sumarbústaður - Raforkusala (Orkusalan)",
                "config_name": "Config_10379380",
                "ean_id": "10379380",
                "meter_type": "MMR mælir",
                "supports_hourly": False,
                "unit": "kWh",
                "note": "Summer cottage manual meter retail electricity"
            }
        ]
        meters_data.extend(fallback_ork)
        for m in fallback_ork:
            save_meter(m)

    # 2. Add RARIK distribution meter for Summer cottage
    rarik_m = {
        "provider": "RARIK",
        "utility": "electricity_distribution",
        "role": "Dreifiveita (Flutningur raforku)",
        "connection_id": "RARIK-101-36815202",
        "meter_number": "101-36815202",
        "name": "Sumarbústaður - Rafmagnsdreifing (RARIK)",
        "config_name": "MMR mælir 101-36815202",
        "meter_type": "MMR Manual Meter (Álestrarmælir)",
        "supports_hourly": False,
        "unit": "kWh",
        "note": "Electricity grid distribution operator for Sumarbústaðurinn"
    }
    meters_data.append(rarik_m)
    save_meter(rarik_m)

    # 3. Add Veitur meters (Heimilið distribution & hot water)
    veitur_meters = [
        {
            "provider": "Veitur",
            "utility": "electricity_distribution",
            "role": "Dreifiveita (Flutningur raforku)",
            "connection_id": "Veitur-62858",
            "meter_number": "62858",
            "name": "Heimilið - Rafmagnsdreifing (Veitur)",
            "config_name": "Snjallmælir 6092777587",
            "meter_type": "Smart Meter (Snjallmælir)",
            "supports_hourly": True,
            "unit": "kWh",
            "note": "Electricity grid distribution operator for Heimilið"
        },
        {
            "provider": "Veitur",
            "utility": "hot_water",
            "role": "Hitaveita (Heitt vatn)",
            "connection_id": "Veitur-30968",
            "meter_number": "30968",
            "name": "Heimilið - Hitaveita (Veitur)",
            "config_name": "Snjallmælir 4081726607",
            "meter_type": "Smart Water Meter (Snjallmælir)",
            "supports_hourly": True,
            "unit": "m³",
            "note": "Geothermal hot water heating meter for Heimilið (Taxti H1A; monthly reading allocated evenly per day)"
        }
    ]
    meters_data.extend(veitur_meters)
    for m in veitur_meters:
        save_meter(m)

    return meters_data

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
    - meter_id: Meter number (e.g. '200-6092777587', '101-36815202', '62858') or connection ID.
                Defaults to the primary residence AMR smart meter.
    - start_date: Start date format 'YYYY-MM-DD'. Defaults to 7 days ago for hourly/daily, or 12 months ago for monthly.
    - end_date: End date format 'YYYY-MM-DD'. Defaults to today.
    - resolution: 'hourly' | 'daily' | 'monthly'. (Note: 'hourly' requires an AMR smart meter).
    """
    # Check if Veitur distribution meter requested
    if meter_id and ("62858" in meter_id or "veitur" in meter_id.lower()):
        period_map = {"hourly": "day", "daily": "month", "monthly": "last12Months"}
        period = period_map.get(resolution.lower(), "month")
        target_date = end_date or start_date or datetime.now().strftime("%Y-%m-%d")
        v_data = get_veitur_consumption(utility="rafmagn", meter_id="62858", period=period, date=target_date)
        return {
            "meter": {
                "name": "Heimilið - Rafmagnsdreifing (Veitur)",
                "meter_number": "62858",
                "provider": "Veitur",
                "utility": "electricity_distribution"
            },
            "resolution": resolution,
            "period": period,
            "date": target_date,
            "total_kwh": v_data.get("total_usage", 0.0),
            "readings_count": v_data.get("readings_count", 0),
            "readings": v_data.get("readings", [])
        }

    # Normalize resolution for Orkusalan
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
        amr_meter = next((m for m in meters if m.get("supports_hourly") and m.get("provider") == "Orkusalan"), meters[0] if meters else None)
        selected_meter = amr_meter

    if not selected_meter:
        return {"error": "No meters found. Please check authentication status."}

    config_name = selected_meter.get("config_name")
    is_amr = selected_meter.get("supports_hourly", False)
    m_number = selected_meter.get("meter_number")

    if time_period == "Hourly" and not is_amr:
        return {
            "error": f"Meter '{selected_meter.get('name')}' is a manual MMR meter and does not support hourly telemetry. Please request 'daily' or 'monthly' resolution.",
            "meter": selected_meter
        }

    # Attempt fetch from Orkusalan API
    url = f"/api/user/consumption?configurationName={config_name}&timePeriod={time_period}&unitOfMesure=kWh&startDate={start_date}&endDate={end_date}"
    try:
        with get_orkusalan_client() as client:
            res = client.get(url)
            if res.status_code == 200:
                items = res.json()
                readings = [
                    {
                        "timestamp": item.get("StartDate"),
                        "kwh": round(item.get("Value", 0.0), 3)
                    }
                    for item in items
                ]
                total_kwh = sum(r["kwh"] for r in readings)
                
                # Persist to local SQLite database
                save_readings(meter_id=m_number, readings=readings, resolution=resolution, unit="kWh")

                return {
                    "meter": {
                        "name": selected_meter.get("name"),
                        "meter_number": m_number,
                        "connection_id": selected_meter.get("connection_id"),
                        "meter_type": selected_meter.get("meter_type")
                    },
                    "resolution": resolution,
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_kwh": round(total_kwh, 3),
                    "readings_count": len(readings),
                    "readings": readings
                }
    except Exception:
        pass

    # Fallback to local SQLite database if offline or token expired
    db_readings = get_readings(meter_id=m_number, resolution=resolution, start_date=start_date, end_date=end_date)
    if db_readings:
        total_kwh = sum(r["value"] for r in db_readings)
        return {
            "meter": {
                "name": selected_meter.get("name"),
                "meter_number": m_number,
                "connection_id": selected_meter.get("connection_id"),
                "meter_type": selected_meter.get("meter_type")
            },
            "resolution": resolution,
            "start_date": start_date,
            "end_date": end_date,
            "total_kwh": round(total_kwh, 3),
            "readings_count": len(db_readings),
            "readings": db_readings,
            "from_database": True
        }

    return {
        "error": f"Failed to fetch consumption and no cached readings found in database for meter {m_number}.",
        "meter": selected_meter
    }

@mcp.tool()
def get_water_usage(
    meter_id: str = "30968",
    period: str = "month",
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get hot water consumption (hitaveita) from Veitur in cubic meters (m³).

    Parameters:
    - meter_id: Hot water meter number (default: '30968').
    - period: 'day' (hourly readings for that day) | 'month' (daily readings for that month) |
              'last30Days' (rolling 30 days) | 'last12Months' (monthly totals).
    - date: Target date in 'YYYY-MM-DD' format (e.g. '2026-10-01' or '2026-11-15'). Defaults to current date.
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    data = get_veitur_consumption(utility="heitt-vatn", meter_id=meter_id, period=period, date=date)
    return {
        "meter": {
            "name": "Heimilið - Hitaveita (Veitur)",
            "meter_number": meter_id,
            "provider": "Veitur",
            "utility": "hot_water",
            "unit": "m³"
        },
        "period": period,
        "date": date,
        "total_cubic_meters": data.get("total_usage", 0.0),
        "readings_count": data.get("readings_count", 0),
        "readings": data.get("readings", []),
        "from_database": data.get("from_database", False)
    }

@mcp.tool()
def get_invoices(limit: int = 10, provider: str = "all") -> Dict[str, Any]:
    """
    Get recent invoices and claims across Orkusalan, RARIK, and Veitur.
    Returns invoice numbers, issue dates, due dates, amounts in ISK, and payment status.

    Parameters:
    - limit: Maximum number of invoices to return (default: 10).
    - provider: 'all' | 'orkusalan' | 'rarik' | 'veitur' (default: 'all').
    """
    all_invoices = []
    errors = []
    future_to = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

    # 1. Fetch from Orkusalan
    if provider in ["all", "orkusalan"]:
        try:
            with get_orkusalan_client() as client:
                res = client.get(f"/api/user/invoices?from=2024-01-01T00:00:00.000Z&to={future_to}T23:59:59.000Z&page=1&pageSize={limit}")
                if res.status_code == 200:
                    for inv in res.json():
                        due_clean = _normalize_date(inv.get("dueDate"))
                        issued_clean = _normalize_date(inv.get("issuedDate"))
                        iid = str(inv.get("invoiceId"))
                        loc_name = (inv.get("locationName") or "").strip()
                        if "10379380" in iid or "sumar" in loc_name.lower() or "bústað" in loc_name.lower():
                            loc = "Bústaður (Orkusalan orka)"
                        elif "10619453" in iid or "blikahjall" in loc_name.lower():
                            loc = "Heimili (Orkusalan orka)"
                        elif loc_name:
                            loc = f"{loc_name} (Orkusalan orka)"
                        else:
                            loc = "Orkusalan (raforkusala)"
                        all_invoices.append({
                            "provider": "Orkusalan",
                            "invoice_id": f"Orkusalan-{iid}",
                            "claim_number": inv.get("claimNumber"),
                            "location": loc,
                            "period": due_clean[:7] if due_clean else "",
                            "issued_date": issued_clean,
                            "due_date": due_clean,
                            "paid_date": _normalize_date(inv.get("fullyPaidDate")) if inv.get("fullyPaidDate") else None,
                            "amount_isk": inv.get("amountInclVAT") or 0.0,
                            "amount_incl_vat_isk": inv.get("amountInclVAT"),
                            "amount_excl_vat_isk": inv.get("amountExclVAT"),
                            "paid": inv.get("paid", False),
                            "pdf_url": inv.get("pathToInvoice")
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
                    for r in parser.rows[1:]:
                        if len(r) >= 6 and r[0].startswith("Or"):
                            inv_nr = r[0]
                            if not any(i.get("invoice_id") == f"RARIK-{inv_nr}" for i in all_invoices):
                                issued_clean = _normalize_date(r[1])
                                due_clean = _normalize_date(r[2])
                                amt_str = re.sub(r"[^\d,]", "", str(r[3])).replace(",", ".")
                                amt_num = float(amt_str) if amt_str else 0.0
                                all_invoices.append({
                                    "provider": "RARIK",
                                    "invoice_id": f"RARIK-{inv_nr}",
                                    "claim_number": None,
                                    "location": "Bústaður (RARIK flutningur)",
                                    "period": due_clean[:7] if due_clean else "",
                                    "issued_date": issued_clean,
                                    "due_date": due_clean,
                                    "amount_isk": amt_num,
                                    "remaining_balance": r[5],
                                    "settled_date": _normalize_date(r[6]) if len(r) > 6 else "",
                                    "paid": True if (len(r) > 6 and r[6]) else False,
                                    "pdf_url": f"https://minarsidur.rarik.is/yfirlit/$Invoice/GetInvoicePDF/?invoiceNr={inv_nr}&nationalId={national_id}"
                                })
                else:
                    errors.append("RARIK invoices: session expired or inaccessible")
        except Exception as e:
            errors.append(f"RARIK invoices error: {e}")

    # 3. Fetch from Veitur
    if provider in ["all", "veitur"]:
        try:
            v_invoices = get_veitur_invoices(limit=limit)
            all_invoices.extend(v_invoices)
        except Exception as e:
            errors.append(f"Veitur invoices error: {e}")

    # Persist all live fetched invoices to local SQLite database
    if all_invoices:
        save_invoices(all_invoices)
    else:
        # Fallback to local SQLite database
        all_invoices = get_invoices_from_db(limit=limit, provider=provider)

    # Sort descending by normalized due_date (YYYY-MM-DD)
    all_invoices.sort(key=lambda x: str(x.get("due_date", "")), reverse=True)

    return {
        "count": len(all_invoices[:limit]),
        "invoices": all_invoices[:limit],
        "errors": errors if errors else None
    }

if __name__ == "__main__":
    import sys
    transport = "sse" if ("--sse" in sys.argv or os.environ.get("MCP_TRANSPORT") == "sse") else "stdio"
    mcp.run(transport=transport)
