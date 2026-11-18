import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from database import save_readings, save_invoices, get_readings, get_invoices_from_db

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
            if res.status_code != 200:
                return {
                    "authenticated": False,
                    "error": f"HTTP {res.status_code}"
                }
            data = res.json()
            user = data.get("user")
            if not user:
                return {
                    "authenticated": False,
                    "error": "No active user in session response"
                }

            # Probe protected RSC page without following redirects to catch expired OIDC tokens
            r_probe = client.get("/yfirlit", follow_redirects=False)
            if r_probe.status_code in (301, 302, 303, 307, 308):
                loc = r_probe.headers.get("location", "").lower()
                if "renew-session" in loc or "idp.kenni.is" in loc or "innskraning" in loc:
                    return {
                        "authenticated": False,
                        "user": user,
                        "error": "OIDC access token expired (redirected to login)"
                    }
            if r_probe.status_code != 200:
                return {
                    "authenticated": False,
                    "user": user,
                    "error": f"Overview check returned HTTP {r_probe.status_code}"
                }

            return {
                "authenticated": True,
                "user": user,
                "expires": data.get("expires")
            }
    except Exception as e:
        return {"authenticated": False, "error": str(e)}


def _resolve_resolution(period: str) -> str:
    if period == "day":
        return "hourly"
    if period in ("month", "week", "last7Days", "last30Days"):
        return "daily"
    if period in ("year", "last12Months"):
        return "monthly"
    return "daily"

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
    period: str = "month",      # "day", "month", "year", "last7Days", "last30Days", "last12Months"
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
    resolution = _resolve_resolution(period)

    try:
        with get_veitur_client() as client:
            res = client.get(path, params=params)
            final_url = str(res.url).lower()
            is_valid_page = (
                res.status_code == 200
                and "minarsidur.veitur.is" in final_url
                and "idp.kenni.is" not in final_url
                and "innskraning" not in final_url
            )
            if is_valid_page:
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

                clean_readings = []
                for r in readings:
                    val = r.get("usageValue")
                    clean_readings.append({
                        "date": r.get("date"),
                        "timestamp": r.get("date"),
                        "tick_label": r.get("tickLabel"),
                        "tooltip_label": r.get("tooltipLabel"),
                        "usage_value": val,
                        "value": val,
                        "unit": unit
                    })

                if clean_readings:
                    total_usage = sum(
                        r["value"] for r in clean_readings if isinstance(r.get("value"), (int, float))
                    )
                    is_uniform_daily = False
                    if resolution == "daily" and len(clean_readings) >= 20:
                        vals = [
                            round(float(r["value"]), 3)
                            for r in clean_readings
                            if isinstance(r.get("value"), (int, float))
                        ]
                        if vals and len(set(vals)) == 1:
                            is_uniform_daily = True

                    for r in clean_readings:
                        r["is_estimated"] = is_uniform_daily

                    save_readings(
                        meter_id=meter_id,
                        readings=clean_readings,
                        resolution=resolution,
                        unit=unit,
                        is_estimated=is_uniform_daily
                    )

                    return {
                        "utility": utility,
                        "meter_id": meter_id,
                        "period": period,
                        "date": date,
                        "unit": unit,
                        "total_usage": round(total_usage, 2),
                        "readings_count": len(clean_readings),
                        "readings": clean_readings,
                        "is_estimated": is_uniform_daily,
                        "from_database": False
                    }
    except Exception:
        pass

    # Fallback to local SQLite database if offline, redirected to Kenni, or empty
    if period == "month":
        ym = date[:7]
        db_readings = get_readings(
            meter_id=meter_id,
            resolution=resolution,
            start_date=f"{ym}-01",
            end_date=f"{ym}-31"
        )
    elif period == "year":
        y = date[:4]
        db_readings = get_readings(
            meter_id=meter_id,
            resolution=resolution,
            start_date=f"{y}-01-01",
            end_date=f"{y}-12-31"
        )
    elif period == "last12Months":
        db_readings = get_readings(meter_id=meter_id, resolution="monthly")[-12:]
    elif period == "day":
        d = date[:10]
        db_readings = get_readings(meter_id=meter_id, resolution="hourly", start_date=d, end_date=d)
    elif period in ("last30Days", "last7Days", "week"):
        limit_n = 7 if period in ("last7Days", "week") else 30
        db_readings = get_readings(meter_id=meter_id, resolution="daily", end_date=date[:10])[-limit_n:]
    else:
        db_readings = get_readings(meter_id=meter_id, resolution=resolution, start_date=date[:10])

    if db_readings:
        normalized = [
            {
                "date": r["timestamp"],
                "timestamp": r["timestamp"],
                "usage_value": r["value"],
                "value": r["value"],
                "unit": r.get("unit", unit),
                "is_estimated": bool(r.get("is_estimated", False))
            }
            for r in db_readings
        ]
        total_usage = sum(r["value"] for r in normalized if isinstance(r.get("value"), (int, float)))
        return {
            "utility": utility,
            "meter_id": meter_id,
            "period": period,
            "date": date,
            "unit": unit,
            "total_usage": round(total_usage, 2),
            "readings_count": len(normalized),
            "readings": normalized,
            "is_estimated": any(r["is_estimated"] for r in normalized),
            "from_database": True
        }

    return {"error": "Failed to fetch and no cached database records found.", "readings": []}


def get_veitur_invoices(limit: int = 10) -> List[Dict[str, Any]]:
    claims = []
    try:
        with get_veitur_client() as client:
            res = client.get("/reikningar")
            final_url = str(res.url).lower()
            is_valid_page = (
                res.status_code == 200
                and "minarsidur.veitur.is" in final_url
                and "idp.kenni.is" not in final_url
                and "innskraning" not in final_url
            )
            if is_valid_page:
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

                if claims:
                    save_invoices(claims)
    except Exception:
        pass

    if not claims:
        db_invs = get_invoices_from_db(limit=limit, provider="Veitur")
        if db_invs:
            return db_invs

    # Sort descending by due_date
    claims.sort(key=lambda x: str(x.get("due_date", "")), reverse=True)
    return claims[:limit]


def sync_veitur_history() -> Dict[str, Any]:
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    prev_year = str(now.year - 1)
    cur_month = now.strftime("%Y-%m-01")
    prev_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")

    hw_12m = get_veitur_consumption("heitt-vatn", "30968", "last12Months", today)
    hw_prev_y = get_veitur_consumption("heitt-vatn", "30968", "year", f"{prev_year}-01-01")
    hw_prev_m = get_veitur_consumption("heitt-vatn", "30968", "month", prev_month)
    hw_cur_m = get_veitur_consumption("heitt-vatn", "30968", "month", cur_month)
    el_12m = get_veitur_consumption("rafmagn", "62858", "last12Months", today)
    el_prev_m = get_veitur_consumption("rafmagn", "62858", "month", prev_month)
    invs = get_veitur_invoices(limit=12)

    return {
        "synced_at": now.isoformat(),
        "hot_water_12m": {"count": hw_12m.get("readings_count", 0), "from_database": hw_12m.get("from_database", False)},
        "hot_water_prev_year": {"count": hw_prev_y.get("readings_count", 0), "from_database": hw_prev_y.get("from_database", False)},
        "hot_water_prev_month": {"count": hw_prev_m.get("readings_count", 0), "from_database": hw_prev_m.get("from_database", False)},
        "hot_water_cur_month": {"count": hw_cur_m.get("readings_count", 0), "from_database": hw_cur_m.get("from_database", False)},
        "electricity_12m": {"count": el_12m.get("readings_count", 0), "from_database": el_12m.get("from_database", False)},
        "electricity_prev_month": {"count": el_prev_m.get("readings_count", 0), "from_database": el_prev_m.get("from_database", False)},
        "invoices_count": len(invs)
    }


if __name__ == "__main__":
    import sys
    if "--sync" in sys.argv:
        print(json.dumps(sync_veitur_history(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(check_veitur_auth(), indent=2, ensure_ascii=False))
