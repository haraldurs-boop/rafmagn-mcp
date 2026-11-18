import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
os.makedirs(DOCS_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DOCS_DIR, "captured_veitur_traffic.json")
STOP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".stop_inspect")

if os.path.exists(STOP_FILE):
    try:
        os.remove(STOP_FILE)
    except Exception:
        pass

IGNORE_EXTENSIONS = (
    ".woff", ".woff2", ".ttf", ".eot", ".png", ".jpg", ".jpeg", 
    ".gif", ".svg", ".ico", ".css"
)

IGNORE_DOMAINS = (
    "google-analytics.com", "googletagmanager.com", "cookiehub.net",
    "cookiehub.eu", "facebook.net", "plausible.io", "doubleclick.net"
)

async def main():
    print("=" * 60)
    print("VEITUR API DISCOVERY & INSPECTION TOOL")
    print("=" * 60)
    print("Launching Chromium in headed mode.")
    print("1. Log in using Rafræn skilríki on your phone.")
    print("2. Once logged in, browse through:")
    print("   - Yfirlit / Mælar (Heimilið: Rafmagn, Heitt vatn, Kalt vatn)")
    print("   - Notkun / Graf (Notkunarsaga, klukkustundar-/daga-/mánaðargögn)")
    print("   - Reikningar (Invoices)")
    print("3. When done, simply reply in chat (or press ENTER in terminal).\n")

    captured_entries = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        context = await browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        async def on_response(response):
            url = response.url
            if any(url.endswith(ext) or ext + "?" in url for ext in IGNORE_EXTENSIONS):
                return
            if any(dom in url for dom in IGNORE_DOMAINS):
                return

            req = response.request
            entry = {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "method": req.method,
                "status": response.status,
                "request_headers": req.headers,
                "response_headers": response.headers,
                "post_data": req.post_data
            }

            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct or "text/" in ct:
                    body = await response.text()
                    try:
                        entry["response_body"] = json.loads(body)
                    except Exception:
                        entry["response_body"] = body[:20000]
            except Exception as e:
                entry["response_body_error"] = str(e)

            captured_entries.append(entry)

            # Highlight interesting API or data endpoints
            if any(term in url.lower() for term in ["/api/", "graphql", "notkun", "reikning", "mael", "user", "overview", "yfirlit"]):
                print(f"[API HIT] {req.method} {response.status} -> {url}")
                if "application/json" in response.headers.get("content-type", ""):
                    print(f"         JSON Response captured ({len(str(entry.get('response_body', '')))} chars)")

        page.on("response", on_response)

        print("[*] Navigating to https://minarsidur.veitur.is ...")
        await page.goto("https://minarsidur.veitur.is")

        print("\n>>> Bíð eftir að þú klárir innskráningu og skoðir síðurnar... <<<")

        # Wait loop checking stdin or stop file or page close
        stop_requested = False
        while not stop_requested:
            await asyncio.sleep(1.0)
            if os.path.exists(STOP_FILE):
                stop_requested = True
                break
            if page.is_closed():
                stop_requested = True
                break

        print("\n[*] Safna kökum og local storage...")
        try:
            cookies = await context.cookies()
        except Exception:
            cookies = []
        
        try:
            if not page.is_closed():
                local_storage = await page.evaluate("() => Object.assign({}, window.localStorage)")
                session_storage = await page.evaluate("() => Object.assign({}, window.sessionStorage)")
            else:
                local_storage, session_storage = {}, {}
        except Exception:
            local_storage, session_storage = {}, {}

        dump_data = {
            "captured_at": datetime.now().isoformat(),
            "cookies": cookies,
            "local_storage": local_storage,
            "session_storage": session_storage,
            "requests": captured_entries
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2, ensure_ascii=False)

        print(f"[✓] Upptaka vistuð í {OUTPUT_FILE} ({len(captured_entries)} beiðnir teknar upp).")
        try:
            await browser.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
