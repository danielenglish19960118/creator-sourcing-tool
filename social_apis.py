"""
Social platform API clients.

- YouTubeClient: uses a simple API key, safe to deploy on Streamlit Cloud.
- InstagramClient: requires a valid Graph API access token for an authorized business/creator account.
- TikTokClient: requires a valid Display API access token for the currently authorized user.

Note: Instagram and TikTok clients do NOT use instagrapi or tiktokapi.
They only use `requests`, so they will not break deployment.
"""

import requests
from googleapiclient.discovery import build


class YouTubeClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("YouTube API key is required.")
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def get_channel_by_handle(self, handle: str):
        """Look up a channel by @handle or channel ID."""
        if not handle:
            return None

        resp = self.youtube.search().list(
            part="snippet",
            q=handle.strip(),
            type="channel",
            maxResults=1,
        ).execute()

        items = resp.get("items", [])
        if not items:
            return None

        channel_id = items[0]["snippet"]["channelId"]

        stats = self.youtube.channels().list(
            part="statistics,snippet",
            id=channel_id,
        ).execute()

        stats_items = stats.get("items", [])
        if not stats_items:
            return None

        item = stats_items[0]
        sn = item.get("snippet", {})
        st = item.get("statistics", {})

        subs = int(st.get("subscriberCount", 0))
        views = int(st.get("viewCount", 0))
        videos = int(st.get("videoCount", 0))

        # Approximate engagement: total views / (subscribers * videos)
        engagement = (views / (subs * videos)) if subs and videos else 0.0

        return {
            "platform": "youtube",
            "channel_id": channel_id,
            "title": sn.get("title", ""),
            "description": sn.get("description", "")[:300],
            "subscribers": subs,
            "total_views": views,
            "video_count": videos,
            "engagement_rate": round(engagement, 4),
            "country": sn.get("country", ""),
        }


class InstagramClient:
    def __init__(self, access_token: str):
        self.token = access_token
        self.base = "https://graph.facebook.com/v18.0"

    def get_profile(self, ig_user_id: str):
        """
        Only works for authorized business/creator accounts.
        ig_user_id comes from the Instagram Business Account ID.
        """
        url = f"{self.base}/{ig_user_id}"
        params = {
            "fields": "username,followers_count,biography,media_count",
            "access_token": self.token,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if "error" in data:
            return {"platform": "instagram", "error": data["error"].get("message", "Unknown error")}

        return {
            "platform": "instagram",
            "username": data.get("username", ""),
            "followers": data.get("followers_count", 0),
            "media_count": data.get("media_count", 0),
            "biography": data.get("biography", ""),
        }


class TikTokClient:
    def __init__(self, access_token: str):
        self.token = access_token
        self.base = "https://open.tiktokapis.com/v2"

    def get_user_info(self):
        """
        Only works for the currently authorized user.
        Display API cannot search arbitrary users.
        """
        url = f"{self.base}/user/info/"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {
            "fields": "open_id,display_name,follower_count,video_count,likes_count",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()

        error = data.get("error", {})
        if error and error.get("code") not in (None, "", "ok"):
            return {"platform": "tiktok", "error": error}

        user = data.get("data", {}).get("user", {})
        return {
            "platform": "tiktok",
            "display_name": user.get("display_name", ""),
            "follower_count": user.get("follower_count", 0),
            "video_count": user.get("video_count", 0),
            "likes_count": user.get("likes_count", 0),
        }
      
