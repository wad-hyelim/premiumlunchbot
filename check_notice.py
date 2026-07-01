import json
import os
import asyncio
import requests
from playwright.async_api import async_playwright

PLACE_ID = "2015500490"
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
LAST_NOTICE_FILE = "last_notice.json"
FEED_URL = f"https://map.naver.com/p/entry/place/{PLACE_ID}?placePath=%2Ffeed"

def load_last_notice():
    if not os.path.exists(LAST_NOTICE_FILE):
        return None
    with open(LAST_NOTICE_FILE, "r") as f:
        return json.load(f).get("last_id")

def save_last_notice(notice_id):
    with open(LAST_NOTICE_FILE, "w") as f:
        json.dump({"last_id": notice_id}, f)

def send_slack(text, image_url=None):
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*네이버 지도 새 소식*\n{text}"}
        }
    ]
    if image_url:
        blocks.append({
            "type": "image",
            "image_url": image_url,
            "alt_text": "공지 이미지"
        })
    requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks})

async def get_notices():
    notices = []
    all_urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        async def handle_response(response):
            url = response.url
            all_urls.append(url)
            if "place.naver.com" in url:
                print(f"[API] {url}")
                try:
                    data = await response.json()
                    items = data.get("items", [])
                    if items:
                        print(f"  → items 발견: {len(items)}개")
                        notices.extend(items)
                except Exception as e:
                    print(f"  → JSON 파싱 실패: {e}")

        page.on("response", handle_response)
        await page.goto(FEED_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)
        await browser.close()

    if not notices:
        print(f"[디버그] 총 {len(all_urls)}개 요청 중 place.naver.com 없음")

    return notices

def main():
    notices = asyncio.run(get_notices())

    if not notices:
        print("소식 없음")
        return

    latest = notices[0]
    latest_id = str(latest.get("id", ""))
    last_id = str(load_last_notice() or "")

    if latest_id == last_id:
        print("새 소식 없음")
        return

    print(f"새 소식 감지: {latest_id}")
    text = latest.get("body", "")
    images = latest.get("images", [])
    image_url = images[0].get("url") if images else None
    send_slack(text, image_url)
    save_last_notice(latest_id)

if __name__ == "__main__":
    main()
