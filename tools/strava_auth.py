"""
Strava OAuth Helper
===================

One-time script to obtain a refresh token with activity:read_all scope.

Usage:
    python3 tools/strava_auth.py

Then paste the redirect URL when prompted.
"""

import urllib.parse
import webbrowser

import dotenv
import requests

dotenv.load_dotenv()

import os

CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]

AUTH_URL = (
    "https://www.strava.com/oauth/authorize"
    f"?client_id={CLIENT_ID}"
    "&redirect_uri=http://localhost"
    "&response_type=code"
    "&approval_prompt=force"
    "&scope=activity:read_all"
)

print("\n1. Opening Strava authorization page in your browser...")
print(f"   If it doesn't open, visit:\n   {AUTH_URL}\n")
webbrowser.open(AUTH_URL)

print("2. Approve the app. Strava will redirect to http://localhost/?code=XXXX&...")
print("   (The page will fail to load — that's fine. Copy the full URL from the address bar.)\n")

redirect_url = input("Paste the full redirect URL here: ").strip()

parsed = urllib.parse.urlparse(redirect_url)
params = urllib.parse.parse_qs(parsed.query)

if "code" not in params:
    print("\nError: no 'code' found in URL. Make sure you copied the full redirect URL.")
    raise SystemExit(1)

code = params["code"][0]

print("\n3. Exchanging code for tokens...")
resp = requests.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    },
    timeout=15,
)
resp.raise_for_status()
data = resp.json()

refresh_token = data["refresh_token"]
scope = data.get("scope", "unknown")

print(f"\nSuccess! Scope: {scope}")
print(f"\nAdd this to your .env file:")
print(f"\nSTRAVA_REFRESH_TOKEN={refresh_token}\n")
