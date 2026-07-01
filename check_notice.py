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
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        def is_feed_response(response):
            return (
                "place.naver.com" in response.url
                and "feed" in response.url
                and response.status == 200
            )

        async with page.expect_response(is_feed_response, timeout=30000) as response_info:
            await page.goto(FEED_URL, wait_until="domcontentloaded", timeout=30000)

        response = await response_info.value
        print(f"[API URL] {response.url}")
        data = await response.json()
        print(f"[응답 키] {list(data.keys())}")
        items = data.get("items", [])
        print(f"[items 수] {len(items)}")

        await browser.close()
        return items

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
