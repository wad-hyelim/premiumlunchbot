import json
import os
import re
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

        await page.goto(FEED_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)

        # 방법 1: window.__INITIAL_STATE__ 또는 유사한 전역 변수 탐색
        for var in ["__INITIAL_STATE__", "__PRELOADED_STATE__", "__STATE__", "naver"]:
            try:
                data = await page.evaluate(f"JSON.stringify(window['{var}'])")
                if data and data != "undefined" and data != "null":
                    print(f"[전역변수 발견] window.{var} (길이: {len(data)})")
                    parsed = json.loads(data)
                    # feed/items 키 탐색
                    text_preview = json.dumps(parsed, ensure_ascii=False)[:300]
                    print(f"  → 미리보기: {text_preview}")
            except Exception as e:
                print(f"[{var}] 없음")

        # 방법 2: HTML 내 JSON 데이터 블록 탐색
        html = await page.content()
        patterns = [
            r'"items"\s*:\s*\[.*?\]',
            r'"feedList"\s*:\s*\[.*?\]',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                print(f"[HTML 패턴 발견] {match.group(0)[:200]}")

        # 방법 3: 피드 관련 DOM 요소 텍스트 추출
        feed_texts = await page.evaluate("""
            () => {
                const els = document.querySelectorAll('[class*="feed"], [class*="Feed"], [class*="post"], [class*="Post"]');
                return Array.from(els).slice(0, 5).map(el => el.innerText.slice(0, 100));
            }
        """)
        if feed_texts:
            print(f"[DOM 피드 요소] {feed_texts}")

        await browser.close()
    return []

def main():
    asyncio.run(get_notices())

if __name__ == "__main__":
    main()
