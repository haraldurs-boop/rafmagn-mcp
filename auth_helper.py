import asyncio
import json
import os
import sys
import time
from datetime import datetime
import httpx
from playwright.async_api import async_playwright

AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auth_session.json")

def load_session() -> dict:
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "updated_at": None,
        "rarik": {"cookies": {}},
        "orkusalan": {"cookies": {}},
        "veitur": {"cookies": {}}
    }

def save_session(session: dict):
    session["updated_at"] = datetime.now().isoformat()
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)
    print(f"[AuthHelper] Saved session to {AUTH_FILE}")

def check_status() -> dict:
    session = load_session()
    results = {
        "timestamp": datetime.now().isoformat(),
        "rarik": {"valid": False, "details": ""},
        "orkusalan": {"valid": False, "details": ""},
        "veitur": {"valid": False, "details": ""}
    }

    # 1. Check Orkusalan
    ork_cookies = session.get("orkusalan", {}).get("cookies", {})
    if "connect.sid" in ork_cookies:
        try:
            with httpx.Client(cookies=ork_cookies, timeout=10.0) as client:
                resp = client.get("https://minarsidur.orkusalan.is/api/user/get_mandates_by_customer")
                if resp.status_code == 200:
                    results["orkusalan"]["valid"] = True
                    results["orkusalan"]["details"] = "Session active (connect.sid valid)"
                else:
                    results["orkusalan"]["details"] = f"HTTP {resp.status_code} - Session expired"
        except Exception as e:
            results["orkusalan"]["details"] = f"Network error: {e}"
    else:
        results["orkusalan"]["details"] = "No connect.sid cookie found"

    # 2. Check RARIK
    rarik_cookies = session.get("rarik", {}).get("cookies", {})
    if ".ASPXAUTH" in rarik_cookies:
        try:
            with httpx.Client(cookies=rarik_cookies, follow_redirects=False, timeout=10.0) as client:
                resp = client.get("https://minarsidur.rarik.is/yfirlit/notkun/")
                if resp.status_code == 200:
                    results["rarik"]["valid"] = True
                    results["rarik"]["details"] = "Session active (.ASPXAUTH valid)"
                elif resp.status_code in [301, 302] and "login" in resp.headers.get("location", "").lower():
                    results["rarik"]["details"] = "Redirected to login - Session expired"
                else:
                    results["rarik"]["details"] = f"HTTP {resp.status_code}"
        except Exception as e:
            results["rarik"]["details"] = f"Network error: {e}"
    else:
        results["rarik"]["details"] = "No .ASPXAUTH cookie found"

    # 3. Check Veitur
    veitur_cookies = session.get("veitur", {}).get("cookies", {})
    if "veitur-service.session-token" in veitur_cookies:
        try:
            with httpx.Client(cookies=veitur_cookies, timeout=10.0) as client:
                resp = client.get("https://minarsidur.veitur.is/api/auth/session")
                if resp.status_code == 200:
                    data = resp.json()
                    name = data.get("user", {}).get("name", "Active")
                    results["veitur"]["valid"] = True
                    results["veitur"]["details"] = f"Session active ({name})"
                else:
                    results["veitur"]["details"] = f"HTTP {resp.status_code} - Session expired"
        except Exception as e:
            results["veitur"]["details"] = f"Network error: {e}"
    else:
        results["veitur"]["details"] = "No veitur-service.session-token cookie found"

    return results

def login_orkusalan_cli(phone_number: str = None) -> bool:
    if not phone_number:
        session = load_session()
        phone_number = os.environ.get("PHONE_NUMBER") or session.get("orkusalan", {}).get("customer", {}).get("phoneNumber")
        if not phone_number:
            phone_number = input("Sláðu inn símanúmer fyrir rafræn skilríki: ").strip()

    print(f"\n--- Initiating Orkusalan Rafræn Skilríki Auth for {phone_number} ---")
    start_url = "https://minarsidur.orkusalan.is/auth/start"
    payload = {"identifier": phone_number, "method": "Sim"}
    headers = {"Content-Type": "application/json", "Referer": "https://minarsidur.orkusalan.is/"}

    with httpx.Client(timeout=15.0) as client:
        res = client.post(start_url, json=payload, headers=headers)
        if res.status_code != 200:
            print(f"[!] Failed to initiate login: HTTP {res.status_code} - {res.text}")
            return False

        data = res.json()
        auth_request_id = data.get("authRequestId")
        verif_code = data.get("verificationCode")
        interval = data.get("pollingInterval", 2)

        print(f"\n>>> ÖRYGGISSTAFUR / VERIFICATION CODE: {verif_code} <<<")
        print("Vinsamlegast staðfestu á símanum þínum (Please approve on your phone)...")

        poll_url = f"https://minarsidur.orkusalan.is/auth/poll?authRequestId={auth_request_id}"
        max_attempts = 45
        for _ in range(max_attempts):
            time.sleep(interval)
            poll_res = client.get(poll_url, headers=headers)
            if poll_res.status_code == 200:
                poll_data = poll_res.json()
                if not poll_data.get("waitingForUserInput"):
                    if poll_data.get("statusMessage") == "Ok":
                        print("[+] Orkusalan authentication successful!")
                        cookies = dict(client.cookies)
                        session = load_session()
                        session.setdefault("orkusalan", {})["cookies"] = cookies
                        session["orkusalan"]["customer"] = poll_data.get("customer")
                        save_session(session)
                        return True
                    else:
                        print(f"[!] Authentication rejected: {poll_data.get('statusMessage')}")
                        return False
            else:
                print(f"[!] Polling HTTP {poll_res.status_code}")
                return False

        print("[!] Authentication timed out waiting for user approval.")
        return False

async def login_rarik_headed() -> bool:
    print("\n--- Launching Headed Browser for RARIK Login ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("Navigating to https://minarsidur.rarik.is...")
        await page.goto("https://minarsidur.rarik.is")
        print("Please complete Electronic ID (Rafræn skilríki) login in the opened browser window...")

        logged_in = False
        for _ in range(90):  # 3 minutes timeout
            await asyncio.sleep(2)
            cookies = await context.cookies()
            auth_cookie = next((c for c in cookies if c["name"] == ".ASPXAUTH" and "rarik.is" in c["domain"]), None)
            current_url = page.url
            if auth_cookie and "login" not in current_url:
                logged_in = True
                print("[+] RARIK authentication detected!")
                session = load_session()
                rarik_dict = {c["name"]: c["value"] for c in cookies if "rarik.is" in c["domain"]}
                session.setdefault("rarik", {})["cookies"] = rarik_dict
                save_session(session)
                os.system("scp .auth_session.json root@192.168.68.87:/opt/rafmagn-mcp/.auth_session.json")
                os.system("ssh root@192.168.68.87 'systemctl restart rafmagn-mcp.service rafmagn-dashboard.service'")
                print("[+] RARIK session synchronized with r8q and services restarted!")
                break

        await browser.close()
        return logged_in

async def login_veitur_headed() -> bool:
    print("\n--- Launching Headed Browser for Veitur Login ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("Navigating to https://minarsidur.veitur.is...")
        await page.goto("https://minarsidur.veitur.is")
        print("Please complete Electronic ID (Rafræn skilríki) login in the opened browser window...")

        logged_in = False
        for _ in range(90):  # 3 minutes timeout
            await asyncio.sleep(2)
            cookies = await context.cookies()
            auth_cookie = next((c for c in cookies if c["name"] == "veitur-service.session-token" and "veitur.is" in c["domain"]), None)
            current_url = page.url
            if auth_cookie and "yfirlit" in current_url:
                logged_in = True
                print("[+] Veitur authentication detected!")
                session = load_session()
                veitur_dict = {c["name"]: c["value"] for c in cookies if "veitur.is" in c["domain"]}
                session.setdefault("veitur", {})["cookies"] = veitur_dict
                save_session(session)
                break

        await browser.close()
        return logged_in

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "status":
        status = check_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    elif action == "orkusalan":
        phone = sys.argv[2] if len(sys.argv) > 2 else None
        success = login_orkusalan_cli(phone)
        sys.exit(0 if success else 1)
    elif action == "rarik":
        success = asyncio.run(login_rarik_headed())
        sys.exit(0 if success else 1)
    elif action == "veitur":
        success = asyncio.run(login_veitur_headed())
        sys.exit(0 if success else 1)
    elif action == "all":
        print("Checking current status...")
        st = check_status()
        if not st["orkusalan"]["valid"]:
            phone = input("Enter phone number for Orkusalan: ").strip()
            login_orkusalan_cli(phone)
        if not st["rarik"]["valid"]:
            asyncio.run(login_rarik_headed())
        if not st["veitur"]["valid"]:
            asyncio.run(login_veitur_headed())
        print("Final Status:")
        print(json.dumps(check_status(), indent=2, ensure_ascii=False))
    else:
        print("Usage: python auth_helper.py [status | orkusalan [phone] | rarik | veitur | all]")

if __name__ == "__main__":
    main()
