import json
import sys
from server import check_auth_status, get_meters, get_electricity_usage, get_invoices

def test_all():
    print("==================================================")
    print("TEST 1: check_auth_status()")
    print("==================================================")
    status = check_auth_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    assert status["orkusalan"]["authenticated"] is True, "Orkusalan should be authenticated"
    assert status["rarik"]["authenticated"] is True, "RARIK should be authenticated"
    print("[PASS] Auth status verified.")

    print("\n==================================================")
    print("TEST 2: get_meters()")
    print("==================================================")
    meters = get_meters()
    print(f"Found {len(meters)} meters:")
    for m in meters:
        print(f" - {m['name']} ({m['meter_number']}): {m['meter_type']} | Hourly: {m.get('supports_hourly')}")
    assert len(meters) >= 2, "Expected at least 2 meters"
    print("[PASS] Meters verified.")

    print("\n==================================================")
    print("TEST 3: get_electricity_usage() - Hourly AMR")
    print("==================================================")
    amr_meter = next((m for m in meters if m.get("supports_hourly")), meters[0])
    amr_usage = get_electricity_usage(
        meter_id=amr_meter.get("meter_number"),
        start_date="2026-11-10",
        end_date="2026-11-12",
        resolution="hourly"
    )
    print(f"Meter: {amr_usage['meter']['name']}")
    print(f"Resolution: {amr_usage['resolution']}")
    print(f"Total kWh: {amr_usage['total_kwh']} kWh across {amr_usage['readings_count']} hourly readings")
    if amr_usage['readings']:
        print(f"Sample reading: {amr_usage['readings'][0]}")
    assert amr_usage["readings_count"] > 0, "Expected hourly readings"
    print("[PASS] Hourly usage verified.")

    print("\n==================================================")
    print("TEST 4: get_electricity_usage() - Daily MMR")
    print("==================================================")
    mmr_meter = next((m for m in meters if not m.get("supports_hourly")), meters[-1])
    mmr_usage = get_electricity_usage(
        meter_id=mmr_meter.get("meter_number"),
        start_date="2026-11-01",
        end_date="2026-11-10",
        resolution="daily"
    )
    print(f"Meter: {mmr_usage['meter']['name']}")
    print(f"Resolution: {mmr_usage['resolution']}")
    print(f"Total kWh: {mmr_usage['total_kwh']} kWh across {mmr_usage['readings_count']} daily readings")
    assert mmr_usage["readings_count"] > 0, "Expected daily readings"
    print("[PASS] Daily MMR usage verified.")

    print("\n==================================================")
    print("TEST 5: get_invoices()")
    print("==================================================")
    invoices = get_invoices(limit=4)
    print(f"Retrieved {invoices['count']} invoices:")
    for inv in invoices["invoices"]:
        print(f" - [{inv.get('provider')}] Invoice {inv.get('invoice_id')} | Issued: {inv.get('issued_date')} | Due: {inv.get('due_date')} | ISK: {inv.get('amount_incl_vat_isk') or inv.get('amount_isk')}")
    assert invoices["count"] > 0, "Expected invoices"
    print("[PASS] Invoices verified.")

    print("\n" + "="*50)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("="*50)

if __name__ == "__main__":
    test_all()
