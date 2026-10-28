from googleapiclient.discovery import build


class YouTubeClient:
    def __init__(self, api_key: str):
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def get_channel_by_handle(self, handle: str):
        """handle: @username 或 channel ID"""
        resp = self.youtube.search().list(
            part="snippet",
            q=handle,
            type="channel",
            maxResults=1,
        ).execute()

        if not resp.get("items"):
            return None

        channel_id = resp["items"][0]["snippet"]["channelId"]

        stats = self.youtube.channels().list(
            part="statistics,snippet",
            id=channel_id,
        ).execute()

        if not stats.get("items"):
            return None

        item = stats["items"][0]
        sn = item["snippet"]
        st = item["statistics"]

        subs = int(st.get("subscriberCount", 0))
        views = int(st.get("viewCount", 0))
        videos = int(st.get("videoCount", 0))

        # 近似互动率：总观看 / (订阅 × 视频数) —— 仅作参考
        engagement = (views / (subs * videos)) if subs and videos else 0

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
      import requests


class InstagramClient:
    def __init__(self, access_token: str):
        self.token = access_token
        self.base = "https://graph.facebook.com/v18.0"

    def get_profile(self, ig_user_id: str):
        """
        仅能获取已授权商业/创作者账号的公开信息。
        ig_user_id 来自 Instagram 商业账号 ID。
        """
        url = f"{self.base}/{ig_user_id}"
        params = {
            "fields": "username,followers_count,biography,media_count",
            "access_token": self.token,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "error" in data:
            return {"platform": "instagram", "error": data["error"]["message"]}

        followers = data.get("followers_count", 0)
        media = data.get("media_count", 1)

        return {
            "platform": "instagram",
            "username": data.get("username", ""),
            "followers": followers,
            "media_count": media,
            "biography": data.get("biography", ""),
        }
import requests


class TikTokClient:
    def __init__(self, access_token: str):
        self.token = access_token
        self.base = "https://open.tiktokapis.com/v2"

    def get_user_info(self):
        """
        仅能获取当前授权用户的公开信息（Display API 限制）。
        无法用它搜索任意用户。
        """
        url = f"{self.base}/user/info/"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {
            "fields": "open_id,display_name,follower_count,video_count,likes_count",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        if "error" in data and data["error"].get("code") != "ok":
            return {"platform": "tiktok", "error": data["error"]}

        user = data.get("data", {}).get("user", {})
        return {
            "platform": "tiktok",
            "display_name": user.get("display_name", ""),
            "follower_count": user.get("follower_count", 0),
            "video_count": user.get("video_count", 0),
            "likes_count": user.get("likes_count", 0),
        }
      
