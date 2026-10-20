#!/usr/bin/env python3
"""Agent 07 data connector — pulls YouTube Analytics for the channel.

Usage:
  .venv/bin/python yt_analytics.py auth                 # one-time browser login
  .venv/bin/python yt_analytics.py videos               # list uploads with video IDs
  .venv/bin/python yt_analytics.py report <VIDEO_ID>    # full 07 report (markdown to stdout)

Needs tools/client_secret.json (OAuth desktop client from Google Cloud Console).
Token is cached in tools/token.json after the first auth.

NOT available via API (paste manually from YouTube Studio): impressions, impressions CTR.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

HERE = Path(__file__).parent
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_creds():
    token_path = HERE / "token.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    if not creds or not creds.valid:
        secret = HERE / "client_secret.json"
        if not secret.exists():
            sys.exit("Missing tools/client_secret.json — download it from Google Cloud Console (OAuth desktop client).")
        flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    return creds


def cmd_auth():
    get_creds()
    print("Authenticated. Token saved to tools/token.json.")


def cmd_videos():
    creds = get_creds()
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="contentDetails,snippet", mine=True).execute()
    if not ch.get("items"):
        sys.exit("No channel found for this Google account.")
    channel = ch["items"][0]
    uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Channel: {channel['snippet']['title']}\n")
    page = None
    while True:
        res = yt.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads, maxResults=50, pageToken=page
        ).execute()
        for item in res.get("items", []):
            vid = item["contentDetails"]["videoId"]
            published = item["contentDetails"].get("videoPublishedAt", "unpublished")[:10]
            print(f"{vid}  {published}  {item['snippet']['title']}")
        page = res.get("nextPageToken")
        if not page:
            break


def query(analytics, video_id, start, metrics, dimensions=None, sort=None, max_results=None):
    kwargs = dict(
        ids="channel==MINE",
        startDate=start,
        endDate=date.today().isoformat(),
        metrics=metrics,
        filters=f"video=={video_id}",
    )
    if dimensions:
        kwargs["dimensions"] = dimensions
    if sort:
        kwargs["sort"] = sort
    if max_results:
        kwargs["maxResults"] = max_results
    return analytics.reports().query(**kwargs).execute()


def cmd_report(video_id):
    creds = get_creds()
    yt = build("youtube", "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)

    meta = yt.videos().list(part="snippet,statistics,contentDetails", id=video_id).execute()
    if not meta.get("items"):
        sys.exit(f"Video {video_id} not found.")
    v = meta["items"][0]
    published = v["snippet"]["publishedAt"][:10]
    start = published

    print(f"# Analytics — {v['snippet']['title']}")
    print(f"- Video ID: {video_id}")
    print(f"- Published: {published} (report generated {date.today().isoformat()})")
    print(f"- Duration: {v['contentDetails']['duration']}")
    stats = v.get("statistics", {})
    print(f"- Public counts: {stats.get('viewCount', '?')} views · {stats.get('likeCount', '?')} likes · {stats.get('commentCount', '?')} comments\n")

    core = query(
        analytics, video_id, start,
        "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares",
    )
    if core.get("rows"):
        row = dict(zip([c["name"] for c in core["columnHeaders"]], core["rows"][0]))
        avd = int(row["averageViewDuration"])
        print("## Core metrics (lifetime)")
        print(f"- Views: {row['views']}")
        print(f"- Watch time: {row['estimatedMinutesWatched']} min")
        print(f"- **AVD: {avd // 60}:{avd % 60:02d}** ({row['averageViewPercentage']:.1f}% of video)")
        print(f"- Subs: +{row['subscribersGained']} / -{row['subscribersLost']}")
        print(f"- Likes {row['likes']} · Comments {row['comments']} · Shares {row['shares']}\n")
    else:
        print("## Core metrics\n- No analytics rows yet (data lags ~48h after publish).\n")

    print("## CTR / impressions\n- ⚠️ Not exposed by the API — paste from YouTube Studio → Content → this video → Reach.\n")

    traffic = query(
        analytics, video_id, start,
        "views,estimatedMinutesWatched",
        dimensions="insightTrafficSourceType",
        sort="-views",
    )
    print("## Traffic sources")
    for r in traffic.get("rows", []):
        print(f"- {r[0]}: {r[1]} views ({r[2]} min watched)")
    if not traffic.get("rows"):
        print("- No data yet.")
    print()

    retention = query(
        analytics, video_id, start,
        "audienceWatchRatio,relativeRetentionPerformance",
        dimensions="elapsedVideoTimeRatio",
    )
    rows = retention.get("rows", [])
    print("## Retention curve (elapsed % → audience still watching)")
    if rows:
        for r in rows:
            pct = float(r[0]) * 100
            watching = float(r[1]) * 100
            bar = "█" * int(watching / 2.5)
            print(f"{pct:5.1f}%  {watching:5.1f}%  {bar}")
        first30 = [r for r in rows if float(r[0]) <= 0.07]
        if first30:
            drop = 100 - float(first30[-1][1]) * 100
            print(f"\n- Hook check: {drop:.1f}% lost in the first ~30s window.")
    else:
        print("- No retention data yet (needs enough views, lags ~48h).")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "auth":
        cmd_auth()
    elif args[0] == "videos":
        cmd_videos()
    elif args[0] == "report" and len(args) > 1:
        cmd_report(args[1])
    else:
        sys.exit(__doc__)
