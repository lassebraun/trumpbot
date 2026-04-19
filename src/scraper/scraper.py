import html

from curl_cffi import requests
from bs4 import BeautifulSoup
import json
from config import Config

session = requests.Session(impersonate="chrome116")
session.get(Config.TRUMP_ACCOUNT_PAGE) # establish session

def get_latest_posts(since_id: str | None = None, limit: int = 5) -> list[dict]:
    params = {"limit": limit}
    if since_id:
        params["since_id"] = since_id

    response = session.get(
        f"{Config.TRUTH_SOCIAL_BASE_URL}/accounts/{Config.TRUMP_ACCOUNT_ID}/statuses",
        params=params,
    )
    response.raise_for_status()

    posts = response.json()

    return [
        {
            "id": p["id"],
            "text": BeautifulSoup(p["content"], "html.parser").get_text(),
            "created_at": p["created_at"],
            "reblogs": p["reblogs_count"],
            "favourites": p["favourites_count"],
        }
        for p in posts
    ]

if __name__ == "__main__":
    posts = get_latest_posts()
    for p in posts:
        print(p["created_at"], p["text"][:100])
