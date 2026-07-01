import json
import os
import requests
from datetime import datetime, timezone, timedelta

PLACE_ID = "2015500490"
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
LAST_NOTICE_FILE = "last_notice.json"

def get_timestamp():
    kst = datetime.now(timezone(timedelta(hours=9)))
    return kst.strftime("%Y%m%d%H%M")

def get_notices():
    url = (
        f"https://pcmap.place.naver.com/place/{PLACE_ID}/feed"
        f"?from=map&fromPanelNum=1&additionalHeight=76"
        f"&timestamp={get_timestamp()}&locale=ko&svcName=map_pcv5"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Referer": f"https://map.naver.com/p/entry/place/{PLACE_ID}?placePath=%2Ffeed",
        "Accept": "application/json, text/plain, */*",
    }
    res = requests.get(url, headers=headers, allow_redirects=True)
    print(f"[상태코드] {res.status_code}")
    res.raise_for_status()
    data = res.json()
    print(f"[응답 키] {list(data.keys())}")
    return data.get("items", [])

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

def main():
    notices = get_notices()

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
