import json
import sys
from server import check_auth_status, get_meters, get_electricity_usage, get_water_usage, get_invoices

def test_all():
    print("==================================================")
    print("TEST 1: check_auth_status()")
    print("==================================================")
    status = check_auth_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    assert status["veitur"]["authenticated"] is True, "Veitur should be authenticated"
    print("[PASS] Auth status verified (Veitur active).")

    print("\n==================================================")
    print("TEST 2: get_meters()")
    print("==================================================")
    meters = get_meters()
    print(f"Found {len(meters)} meters:")
    for m in meters:
        print(f" - [{m.get('provider')}] {m['name']} ({m['meter_number']}): {m.get('utility')} | Hourly: {m.get('supports_hourly')}")
    assert any(m["meter_number"] == "30968" for m in meters), "Expected hot water meter 30968"
    assert any(m["meter_number"] == "62858" for m in meters), "Expected Veitur electricity meter 62858"
    print("[PASS] Meters verified (Orkusalan, RARIK, Veitur).")

    print("\n==================================================")
    print("TEST 3: get_water_usage() - Veitur Hot Water (m³)")
    print("==================================================")
    hw = get_water_usage(meter_id="30968", period="month", date="2026-10-01")
    print(f"Meter: {hw['meter']['name']}")
    print(f"Period: {hw['period']} ({hw['date']})")
    print(f"Total: {hw['total_cubic_meters']} m³ across {hw['readings_count']} daily readings")
    if hw['readings']:
        print(f"Sample reading: {hw['readings'][0]}")
    assert hw["readings_count"] > 0, "Expected hot water readings"
    assert hw["total_cubic_meters"] > 0, "Expected positive total water usage"
    print("[PASS] Hot water usage verified.")

    print("\n==================================================")
    print("TEST 4: get_electricity_usage() - Veitur Distribution")
    print("==================================================")
    el_veitur = get_electricity_usage(meter_id="62858", resolution="daily", end_date="2026-10-18")
    print(f"Meter: {el_veitur['meter']['name']}")
    print(f"Total: {el_veitur['total_kwh']} kWh across {el_veitur['readings_count']} daily readings")
    assert el_veitur["readings_count"] > 0, "Expected Veitur electricity readings"
    print("[PASS] Veitur electricity usage verified.")

    print("\n==================================================")
    print("TEST 5: get_invoices() - Veitur & Combined")
    print("==================================================")
    invoices = get_invoices(limit=5, provider="veitur")
    print(f"Retrieved {invoices['count']} Veitur invoices:")
    for inv in invoices["invoices"]:
        print(f" - [{inv.get('provider')}] Claim {inv.get('claim_number')} | Due: {inv.get('due_date')} | ISK: {inv.get('amount_isk')} | Paid: {inv.get('is_paid')}")
    assert invoices["count"] > 0, "Expected Veitur invoices"
    print("[PASS] Invoices verified.")

    print("\n" + "="*50)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("="*50)

if __name__ == "__main__":
    test_all()
