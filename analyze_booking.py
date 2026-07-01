import asyncio
import json
from playwright.async_api import async_playwright

PLACE_ID = "38522494"
BOOKING_URL = f"https://pcmap.place.naver.com/restaurant/{PLACE_ID}/booking?from=map&fromPanelNum=2&locale=ko&svcName=map_pcv5"

async def analyze():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # JSON API 응답 캡처
        json_responses = []

        async def handle_response(response):
            if response.status != 200:
                return
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                return
            if "naver.com" not in response.url:
                return
            try:
                raw = await response.text()
                data = json.loads(raw)
                json_responses.append({"url": response.url, "keys": list(data.keys())})
            except:
                pass

        page.on("response", handle_response)
        await page.goto(BOOKING_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

        print(f"[JSON API 목록]")
        for r in json_responses:
            print(f"  {r['url'][:100]}")
            print(f"  키: {r['keys']}")

        # DOM에서 예약 상품 목록 추출 시도
        result = await page.evaluate("""
            () => {
                const allLi = document.querySelectorAll('li');
                const liInfo = Array.from(allLi).slice(0, 20).map(el => ({
                    cls: el.className.slice(0, 80),
                    text: (el.innerText || '').trim().slice(0, 100),
                }));
                return {
                    liInfo,
                    bodyText: document.body.innerText.slice(0, 500)
                };
            }
        """)

        print(f"\n[페이지 텍스트 앞 500자]\n{result.get('bodyText', '')}")
        print(f"\n[li 목록]")
        for li in result.get("liInfo", []):
            if li["text"]:
                print(f"  cls={li['cls']} | {li['text']}")

        await browser.close()

asyncio.run(analyze())
