import json
import os
import hashlib
import asyncio
import requests
from playwright.async_api import async_playwright

PLACE_ID = "2015500490"
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
LAST_NOTICE_FILE = "last_notice.json"
# iframe URL에 직접 접근
FEED_URL = f"https://pcmap.place.naver.com/restaurant/{PLACE_ID}/feed?from=map&fromPanelNum=1&additionalHeight=76&locale=ko&svcName=map_pcv5"

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

async def get_latest_notice():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(FEED_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

        # 페이지 HTML 일부 출력 (디버그)
        html = await page.content()
        print(f"[HTML 앞 500자]\n{html[:500]}")

        # DOM에서 피드 항목 추출 시도
        result = await page.evaluate("""
            () => {
                // 모든 li의 class와 텍스트 출력 (디버그)
                const allLi = document.querySelectorAll('li');
                const liInfo = Array.from(allLi).slice(0, 30).map(el => ({
                    cls: el.className.slice(0, 80),
                    text: (el.innerText || '').trim().slice(0, 80),
                    hasImg: !!el.querySelector('img')
                }));
                return { liInfo };
            }
        """)

        print(f"[DOM 결과] {json.dumps(result, ensure_ascii=False, indent=2)}")
        await browser.close()
        return result

def main():
    result = asyncio.run(get_latest_notice())

    if not result or "error" in result:
        print("소식 없음")
        return

    text = result.get("text", "")
    image_url = result.get("image")

    notice_id = hashlib.md5(text.encode()).hexdigest()
    last_id = load_last_notice()

    if notice_id == last_id:
        print("새 소식 없음")
        return

    print(f"새 소식 감지!")
    send_slack(text, image_url)
    save_last_notice(notice_id)

if __name__ == "__main__":
    main()
