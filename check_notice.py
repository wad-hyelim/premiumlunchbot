import json
import os
import hashlib
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

async def get_latest_notice():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(FEED_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

        # 렌더링된 DOM에서 피드 첫 번째 항목 추출
        result = await page.evaluate("""
            () => {
                // iframe 안에 렌더링되는 경우 확인
                const iframe = document.querySelector('iframe#entryIframe');
                const doc = iframe ? iframe.contentDocument : document;

                // 피드/소식 관련 컨테이너 탐색
                const selectors = [
                    '[class*="feed_"] li',
                    '[class*="post_"] li',
                    '[class*="Feed"] li',
                    '[class*="Post"] li',
                    'li[class*="item"]',
                ];

                for (const sel of selectors) {
                    const items = doc.querySelectorAll(sel);
                    if (items.length > 0) {
                        const first = items[0];
                        const text = first.innerText || first.textContent || '';
                        const img = first.querySelector('img');
                        return {
                            selector: sel,
                            text: text.trim().slice(0, 500),
                            image: img ? img.src : null,
                            count: items.length
                        };
                    }
                }
                return { error: 'no feed elements found', bodyPreview: doc.body.innerHTML.slice(0, 300) };
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

    # 텍스트 해시를 ID로 사용
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
