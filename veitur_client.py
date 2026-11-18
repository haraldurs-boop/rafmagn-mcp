import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
from database import save_readings, save_invoices

AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auth_session.json")

def load_auth() -> dict:
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_veitur_client() -> httpx.Client:
    auth = load_auth()
    cookies = auth.get("veitur", {}).get("cookies", {})
    return httpx.Client(
        cookies=cookies,
        base_url="https://minarsidur.veitur.is",
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        },
        timeout=15.0
    )

def check_veitur_auth() -> Dict[str, Any]:
    try:
        with get_veitur_client() as client:
            res = client.get("/api/auth/session")
            if res.status_code == 200:
                data = res.json()
                return {
                    "authenticated": True,
                    "user": data.get("user"),
                    "expires": data.get("expires")
                }
            return {
                "authenticated": False,
                "error": f"HTTP {res.status_code}"
            }
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

def _extract_rsc_text(html: str) -> str:
    matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:\\.|[^"\\])*)"\]\)', html)
    full_str = ""
    for m in matches:
        try:
            # Use json.loads to unescape without corrupting multi-byte UTF-8
            chunk = json.loads(f'"{m}"')
            full_str += chunk
        except Exception:
            try:
                full_str += m.encode("utf-8").decode("unicode_escape")
            except Exception:
                full_str += m
    return full_str

def get_veitur_consumption(
    utility: str = "rafmagn",  # "rafmagn" or "heitt-vatn"
    meter_id: str = "62858",
    period: str = "month",      # "day", "month", "last30Days", "last12Months"
    date: Optional[str] = None
) -> Dict[str, Any]:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    path = f"/notkun/{utility}"
    params = {
        "meter": meter_id,
        "period": period,
        "date": date
    }

    unit = "kWh" if utility == "rafmagn" else "m³"

    try:
        with get_veitur_client() as client:
            res = client.get(path, params=params)
            if res.status_code == 200:
                rsc_text = _extract_rsc_text(res.text)
                
                # Robust extraction of readings data array
                data_matches = re.findall(r'"data":\s*(\[[^\]]+\])', rsc_text)
                readings = []
                for dm in data_matches:
                    try:
                        parsed = json.loads(dm)
                        if parsed and isinstance(parsed, list) and "usageValue" in parsed[0]:
                            readings = parsed
                            break
                    except Exception:
                        continue

                total_usage = sum(r.get("usageValue", 0) for r in readings if isinstance(r.get("usageValue"), (int, float)))

                clean_readings = []
                for r in readings:
                    clean_readings.append({
                        "date": r.get("date"),
                        "timestamp": r.get("date"),
                        "tick_label": r.get("tickLabel"),
                        "tooltip_label": r.get("tooltipLabel"),
                        "usage_value": r.get("usageValue"),
                        "value": r.get("usageValue"),
                        "unit": unit
                    })

                # Save to local SQLite database
                resolution = "hourly" if period == "day" else "daily" if period == "month" else "monthly"
                if clean_readings:
                    save_readings(meter_id=meter_id, readings=clean_readings, resolution=resolution, unit=unit)

                return {
                    "utility": utility,
                    "meter_id": meter_id,
                    "period": period,
                    "date": date,
                    "unit": unit,
                    "total_usage": round(total_usage, 2),
                    "readings_count": len(clean_readings),
                    "readings": clean_readings
                }
    except Exception as e:
        pass

    # Fallback to local SQLite database if offline or session expired
    from database import get_readings
    resolution = "hourly" if period == "day" else "daily" if period == "month" else "monthly"
    db_readings = get_readings(meter_id=meter_id, resolution=resolution, start_date=date[:7] if period == "month" else date)
    if db_readings:
        total_usage = sum(r["value"] for r in db_readings)
        return {
            "utility": utility,
            "meter_id": meter_id,
            "period": period,
            "date": date,
            "unit": unit,
            "total_usage": round(total_usage, 2),
            "readings_count": len(db_readings),
            "readings": db_readings,
            "from_database": True
        }

    return {"error": "Failed to fetch and no cached database records found.", "readings": []}

def get_veitur_invoices(limit: int = 10) -> List[Dict[str, Any]]:
    claims = []
    try:
        with get_veitur_client() as client:
            res = client.get("/reikningar")
            if res.status_code == 200:
                rsc_text = _extract_rsc_text(res.text)
                
                # Find all claim blocks
                for m in re.finditer(r'\{"claimNumber":"[^"]+"[^{}]*\}', rsc_text):
                    try:
                        raw = m.group(0).replace('"$D', '"')
                        claim = json.loads(raw)
                        token = claim.get("documentReferenceToken", "")
                        pdf_url = f"https://minarsidur.veitur.is/reikningar/krofur/download?token={token}" if token else ""
                        due_d = claim.get("dueDate", "")[:10]
                        claims.append({
                            "provider": "Veitur",
                            "invoice_id": f"Veitur-{claim.get('claimNumber')}",
                            "claim_number": claim.get("claimNumber"),
                            "location": "Heimili (Veitur flutningur/vatn)",
                            "period": due_d[:7] if due_d else "2026-10",
                            "referral_claim": claim.get("referralClaim"),
                            "company_id": claim.get("companyId", "Veitur"),
                            "issued_date": due_d,
                            "due_date": due_d,
                            "final_due_date": claim.get("finalDueDate", "")[:10],
                            "amount_isk": claim.get("originalAmount"),
                            "amount_incl_vat_isk": claim.get("originalAmount"),
                            "is_paid": claim.get("isPaid", True),
                            "payment_method": claim.get("paymentMethodDescription"),
                            "pdf_url": pdf_url
                        })
                    except Exception:
                        continue

                # Save to database
                if claims:
                    save_invoices(claims)
    except Exception:
        pass

    if not claims:
        from database import get_invoices_from_db
        db_invs = get_invoices_from_db(limit=limit, provider="Veitur")
        if db_invs:
            return db_invs

    # Sort descending by due_date
    claims.sort(key=lambda x: str(x.get("due_date", "")), reverse=True)
    return claims[:limit]
