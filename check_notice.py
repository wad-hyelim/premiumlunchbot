import json
import os
import hashlib
import asyncio
import requests
from playwright.async_api import async_playwright

PLACE_ID = "2015500490"
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
LAST_NOTICE_FILE = "last_notice.json"
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
            "text": {"type": "mrkdwn", "text": f"*🍱 프리미엄회사식당 새 소식*\n{text}"}
        }
    ]
    if image_url:
        blocks.append({
            "type": "image",
            "image_url": image_url,
            "alt_text": "소식 이미지"
        })
    requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks})

def clean_text(raw):
    # "프리미엄회사식당\n알림" 또는 "프리미엄회사식당\nNEW" 이후 본문 추출
    lines = raw.split("\n")
    result = []
    skip_prefixes = {"프리미엄회사식당", "알림", "NEW", "공지", "좋아요", "좋아요1", "좋아요2", "좋아요3"}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 날짜 패턴이면 중단
        if line.startswith("20") or "시간 전" in line or "일 전" in line:
            break
        # 중복/불필요 줄 스킵
        if line in skip_prefixes or line.startswith("좋아요"):
            continue
        result.append(line)
    return "\n".join(result)

async def get_latest_notice():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(FEED_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

        result = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('li.place_apply_pui.sjRRS');
                if (items.length === 0) return { error: 'no feed items' };
                const first = items[0];
                const text = (first.innerText || '').trim();
                const img = first.querySelector('img');
                return {
                    text: text,
                    image: img ? img.src : null,
                    count: items.length
                };
            }
        """)

        await browser.close()
        return result

def main():
    result = asyncio.run(get_latest_notice())

    if not result or "error" in result:
        print(f"소식 없음: {result}")
        return

    raw_text = result.get("text", "")
    image_url = result.get("image")
    text = clean_text(raw_text)

    notice_id = hashlib.md5(raw_text.encode()).hexdigest()
    last_id = load_last_notice()

    print(f"[최신 소식] {text[:80]}")

    if notice_id == last_id:
        print("새 소식 없음")
        return

    print("새 소식 감지! Slack 전송 중...")
    send_slack(text, image_url)
    save_last_notice(notice_id)
    print("완료")

if __name__ == "__main__":
    main()
