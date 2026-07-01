import asyncio
import os
import requests
from playwright.async_api import async_playwright

PLACE_ID = "2015500490"
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
FEED_URL = f"https://pcmap.place.naver.com/restaurant/{PLACE_ID}/feed?from=map&fromPanelNum=1&additionalHeight=76&locale=ko&svcName=map_pcv5"

def clean_text(raw):
    lines = raw.split("\n")
    result = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("20") or "시간 전" in line or "일 전" in line:
            break
        if line in {"프리미엄회사식당", "알림", "NEW", "공지"} or line.startswith("좋아요"):
            continue
        for prefix in ["알림", "NEW", "공지"]:
            if line.startswith(prefix):
                line = line[len(prefix):]
                break
        if line and line not in seen:
            seen.add(line)
            result.append(line)
    return "\n".join(result)

def send_slack(text, image_url=None):
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🍱 오늘의 프리미엄회사식당 소식*\n{text}"}
        }
    ]
    if image_url:
        blocks.append({
            "type": "image",
            "image_url": image_url,
            "alt_text": "소식 이미지"
        })
    requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks})

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
                // 모든 이미지 URL 출력 (디버그)
                const imgs = first.querySelectorAll('img');
                const allImgs = Array.from(imgs).map(img => img.src);
                // 프로필 이미지(ldb-phinf) 제외하고 첫 번째 이미지 추출
                let image = null;
                for (const img of imgs) {
                    const src = img.src || '';
                    if (!src.includes('ldb-phinf')) {
                        image = src;
                        break;
                    }
                }
                return { text, image, allImgs };
            }
        """)

        await browser.close()
        return result

def main():
    result = asyncio.run(get_latest_notice())

    if not result or "error" in result:
        print(f"소식 없음: {result}")
        return

    text = clean_text(result.get("text", ""))
    image_url = result.get("image")

    print(f"[소식] {text[:80]}")
    print(f"[이미지] {image_url}")
    print(f"[전체 이미지] {result.get('allImgs', [])}")

    send_slack(text, image_url)
    print("Slack 전송 완료")

if __name__ == "__main__":
    main()
