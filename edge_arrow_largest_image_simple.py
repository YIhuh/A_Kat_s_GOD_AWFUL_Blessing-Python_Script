import os
import time
import requests
from io import BytesIO
from urllib.parse import urlparse, urljoin

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options

# ================= 配置 =================
START_URL = "https://a-kats-god-awful-blessing.mehgazone.com/2024/11/08/a-kats-god-awful-blessing-prologue/"
OUT_DIR = "out"
DELAY = 2.5
SUPPORTED_EXT = (".png", ".jpg", ".jpeg", ".webp")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
# =======================================


def ensure_out():
    os.makedirs(OUT_DIR, exist_ok=True)


def filename_from_url(url):
    return os.path.basename(urlparse(url).path.split("?")[0])


def download(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def is_excluded(filename):
    fname = filename.lower()

    # 1️⃣ Patreon 赞助图（仅这一张）
    if fname == "patreon-names-v2-18.png":
        return True

    # 2️⃣ 评论头像
    if "-150x150" in fname:
        return True

    # 3️⃣ 网站 banner（仅这一张）
    if fname == "mehgazone-website-banner.png":
        return True

    return False


def main():
    ensure_out()
    downloaded = set(os.listdir(OUT_DIR))

    downloaded_count = 0
    excluded_count = 0

    options = Options()
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--disable-gpu")

    driver = webdriver.Edge(options=options)
    driver.get(START_URL)
    time.sleep(3)

    print("▶ 开始抓取（仅排除明确指定图片）\n")

    try:
        while True:
            imgs = driver.find_elements(By.TAG_NAME, "img")
            new_found = False

            for img in imgs:
                src = img.get_attribute("src")
                if not src:
                    continue

                src = urljoin(driver.current_url, src)
                if not src.lower().endswith(SUPPORTED_EXT):
                    continue

                name = filename_from_url(src)
                if not name or name in downloaded:
                    continue

                if is_excluded(name):
                    excluded_count += 1
                    continue

                data = download(src)
                if not data:
                    continue

                with open(os.path.join(OUT_DIR, name), "wb") as f:
                    f.write(data)

                downloaded.add(name)
                downloaded_count += 1
                new_found = True

                print(f"✔ 下载：{name}")

            print(f"📊 已下载：{downloaded_count} | 已排除：{excluded_count}")

            if not new_found:
                print("\n⚠ 本页未发现新图片")
                print("⏸ 已停止翻页，浏览器保持打开，Ctrl+C 结束脚本\n")
                while True:
                    time.sleep(1)

            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
            time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n⛔ 用户手动终止")

    finally:
        print("✔ 脚本结束（浏览器未自动关闭）")


if __name__ == "__main__":
    main()
