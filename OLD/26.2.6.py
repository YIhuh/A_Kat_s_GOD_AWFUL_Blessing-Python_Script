import os
import time
import json
import hashlib
import threading
import requests
from io import BytesIO
from urllib.parse import urlparse, urljoin
from datetime import datetime

import keyboard
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options

# ================= 配置 =================
START_URL = "https://a-kats-god-awful-blessing.mehgazone.com/2024/11/08/a-kats-god-awful-blessing-prologue/"
OUT_DIR = "out"
STATE_FILE = "state.json"
MANIFEST_FILE = "manifest.json"

DELAY = 2.5
MAX_EMPTY_PAGES = 5
MIN_VALID_AREA = 200_000
BLOCK_KEYWORDS = ("patreon", "support", "donate")
SUPPORTED_EXT = (".png", ".jpg", ".jpeg", ".webp")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
# =======================================


paused = False


def toggle_pause():
    global paused
    paused = not paused
    print("\n⏸ PAUSED" if paused else "\n▶ RESUMED")


def hotkey_listener():
    keyboard.add_hotkey("p", toggle_pause)
    keyboard.wait()


def ensure_dirs():
    os.makedirs(OUT_DIR, exist_ok=True)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def filename_from_url(url):
    return os.path.basename(urlparse(url).path)


def is_blocked(img):
    for attr in ("src", "alt", "class", "id"):
        v = img.get_attribute(attr)
        if v and any(k in v.lower() for k in BLOCK_KEYWORDS):
            return True
    return False


def wait_loaded(driver, img, timeout=6):
    start = time.time()
    while time.time() - start < timeout:
        w = driver.execute_script("return arguments[0].naturalWidth", img)
        h = driver.execute_script("return arguments[0].naturalHeight", img)
        if w and h:
            return w, h
        time.sleep(0.1)
    return None, None


def download(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def main():
    ensure_dirs()

    downloaded_files = set(os.listdir(OUT_DIR))
    manifest = load_json(MANIFEST_FILE, [])
    state = load_json(STATE_FILE, {})
    empty_pages = 0
    page_count = 0

    threading.Thread(target=hotkey_listener, daemon=True).start()

    options = Options()
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")

    driver = webdriver.Edge(options=options)

    start_url = state.get("last_page_url", START_URL)
    driver.get(start_url)
    time.sleep(3)

    print("▶ 运行中（按 P 暂停 / 继续）\n")

    try:
        while True:
            while paused:
                time.sleep(0.2)

            page_count += 1
            imgs = driver.find_elements(By.TAG_NAME, "img")

            best = None
            best_area = 0
            best_size = None

            for img in imgs:
                if is_blocked(img):
                    continue

                src = img.get_attribute("src")
                if not src:
                    continue

                src = urljoin(driver.current_url, src)
                if not src.lower().endswith(SUPPORTED_EXT):
                    continue

                w, h = wait_loaded(driver, img)
                if not w:
                    continue

                area = w * h
                if area < MIN_VALID_AREA:
                    continue

                name = filename_from_url(src)
                if not name or name in downloaded_files:
                    continue

                if area > best_area:
                    best = src
                    best_area = area
                    best_size = (w, h)

            if best:
                data = download(best)
                if data:
                    name = filename_from_url(best)
                    with open(os.path.join(OUT_DIR, name), "wb") as f:
                        f.write(data)

                    manifest.append({
                        "filename": name,
                        "url": best,
                        "width": best_size[0],
                        "height": best_size[1],
                        "sha256": sha256(data),
                        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                    save_json(MANIFEST_FILE, manifest)
                    save_json(STATE_FILE, {"last_page_url": driver.current_url})

                    downloaded_files.add(name)
                    empty_pages = 0
                else:
                    empty_pages += 1
            else:
                empty_pages += 1

            print(
                f"页数: {page_count} | "
                f"已下载: {len(downloaded_files)} | "
                f"连续空页: {empty_pages}/{MAX_EMPTY_PAGES} | "
                f"状态: {'PAUSED' if paused else 'RUNNING'}"
            )

            if empty_pages >= MAX_EMPTY_PAGES:
                print("\n✔ 已无新内容，自动停止")
                break

            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
            time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n⛔ 用户中断，进度已保存")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
