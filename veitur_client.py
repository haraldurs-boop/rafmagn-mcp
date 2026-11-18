import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx

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
            full_str += bytes(m, "utf-8").decode("unicode_escape")
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

    with get_veitur_client() as client:
        res = client.get(path, params=params)
        if res.status_code != 200:
            return {"error": f"HTTP {res.status_code}", "readings": []}

        rsc_text = _extract_rsc_text(res.text)
        
        # Look for the second data array which contains the actual readings
        data_matches = re.findall(r'"data":\s*(\[[^\]]+\])', rsc_text)
        readings = []
        for dm in data_matches:
            try:
                parsed = json.loads(dm)
                # Check if it has 'date' and 'usageValue'
                if parsed and isinstance(parsed, list) and "usageValue" in parsed[0]:
                    readings = parsed
                    break
            except Exception:
                continue

        unit = "kWh" if utility == "rafmagn" else "m³"
        total_usage = sum(r.get("usageValue", 0) for r in readings if isinstance(r.get("usageValue"), (int, float)))

        clean_readings = []
        for r in readings:
            clean_readings.append({
                "date": r.get("date"),
                "tick_label": r.get("tickLabel"),
                "tooltip_label": r.get("tooltipLabel"),
                "usage_value": r.get("usageValue"),
                "unit": unit
            })

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

def get_veitur_invoices(limit: int = 10) -> List[Dict[str, Any]]:
    with get_veitur_client() as client:
        res = client.get("/reikningar")
        if res.status_code != 200:
            return []

        rsc_text = _extract_rsc_text(res.text)
        
        # Find all claim blocks
        claims = []
        for m in re.finditer(r'\{"claimNumber":"[^"]+"[^{}]*\}', rsc_text):
            try:
                # clean up Next.js date prefixes like "$D"
                raw = m.group(0).replace('"$D', '"')
                claim = json.loads(raw)
                token = claim.get("documentReferenceToken", "")
                pdf_url = f"https://minarsidur.veitur.is/reikningar/krofur/download?token={token}" if token else ""
                claims.append({
                    "provider": "Veitur",
                    "invoice_id": claim.get("claimNumber"),
                    "claim_number": claim.get("claimNumber"),
                    "referral_claim": claim.get("referralClaim"),
                    "company_id": claim.get("companyId", "Veitur"),
                    "due_date": claim.get("dueDate", "")[:10],
                    "final_due_date": claim.get("finalDueDate", "")[:10],
                    "amount_isk": claim.get("originalAmount"),
                    "amount_incl_vat_isk": claim.get("originalAmount"),
                    "is_paid": claim.get("isPaid", True),
                    "payment_method": claim.get("paymentMethodDescription"),
                    "pdf_url": pdf_url
                })
            except Exception:
                continue

        # Sort descending by due_date
        claims.sort(key=lambda x: str(x.get("due_date", "")), reverse=True)
        return claims[:limit]

if __name__ == "__main__":
    print("Checking auth...")
    print(check_veitur_auth())

    print("\nFetching hot water consumption (month)...")
    hw = get_veitur_consumption("heitt-vatn", "30968", "month", "2026-10-01")
    print(f"Total hot water: {hw['total_usage']} {hw['unit']} across {hw['readings_count']} days")
    if hw['readings']:
        print("Sample:", hw['readings'][0])

    print("\nFetching electricity consumption (day)...")
    el = get_veitur_consumption("rafmagn", "62858", "day", "2026-11-15")
    print(f"Total electricity: {el['total_usage']} {el['unit']} across {el['readings_count']} hours")
    if el['readings']:
        print("Sample:", el['readings'][0])

    print("\nFetching invoices...")
    invs = get_veitur_invoices(5)
    print(f"Retrieved {len(invs)} invoices:")
    for inv in invs:
        print(f"  - Claim {inv['claim_number']} | Due: {inv['due_date']} | ISK {inv['amount_isk']} | Paid: {inv['is_paid']}")
