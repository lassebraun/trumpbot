from bs4 import BeautifulSoup
from curl_cffi import requests

from src.database.models import Posts
from src.config import Config

session = requests.Session(impersonate="chrome116")
session.get(Config.trump_account_page) # establish session

def get_latest_posts(since_id: str | None = None, limit: int = 5) -> list[Posts]:
    params = {"limit": limit}
    if since_id:
        params["since_id"] = since_id

    response = session.get(
        f"{Config.truth_social_base_url}/accounts/{Config.trump_account_id}/statuses",
        params=params,
    )
    response.raise_for_status()

    posts = response.json()

    return [
        Posts(
            id= p["id"],
            text= BeautifulSoup(p["content"], "html.parser").get_text(),
            created_at= p["created_at"],
            reblogs= p["reblogs_count"],
            favourites= p["favourites_count"],
    )
        for p in posts
    ]

if __name__ == "__main__":
    posts = get_latest_posts()
    for p in posts:
        print(p["created_at"], p["text"][:100])
