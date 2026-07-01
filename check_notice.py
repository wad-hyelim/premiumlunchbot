import requests
import json
import os
import sys

PLACE_ID = "2015500490"
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
LAST_NOTICE_FILE = "last_notice.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://map.naver.com/",
    "Accept": "application/json",
}

def get_notices():
    url = f"https://api.place.naver.com/place/v1/feed/{PLACE_ID}?lang=ko&offset=0&limit=5"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    return data.get("items", [])

def load_last_notice():
    if not os.path.exists(LAST_NOTICE_FILE):
        return None
    with open(LAST_NOTICE_FILE, "r") as f:
        return json.load(f).get("last_id")

def save_last_notice(notice_id):
    with open(LAST_NOTICE_FILE, "w") as f:
        json.dump({"last_id": notice_id}, f)

def send_slack(notice):
    text = notice.get("body", "")
    images = notice.get("images", [])
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*네이버 지도 새 소식*\n{text}"}
        }
    ]
    for img in images[:1]:  # 첫 번째 이미지만
        blocks.append({
            "type": "image",
            "image_url": img.get("url", ""),
            "alt_text": "공지 이미지"
        })
    payload = {"blocks": blocks}
    requests.post(SLACK_WEBHOOK_URL, json=payload)

def main():
    notices = get_notices()
    if not notices:
        print("소식 없음")
        return

    latest = notices[0]
    latest_id = latest.get("id")
    last_id = load_last_notice()

    if str(latest_id) == str(last_id):
        print("새 소식 없음")
        return

    print(f"새 소식 감지: {latest_id}")
    send_slack(latest)
    save_last_notice(latest_id)

if __name__ == "__main__":
    main()
