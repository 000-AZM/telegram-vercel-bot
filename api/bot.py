import os
from fastapi import FastAPI, Request
import httpx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

app = FastAPI()

# Telegram bot
TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Google Sheets setup
SHEET_ID = os.getenv("SHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_CRED_JSON")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(SERVICE_ACCOUNT_JSON), scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet("Telegram")  # Your sheet name

@app.post("/api/bot")
async def telegram_webhook(req: Request):
    data = await req.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        user = data["message"]["from"].get("username") or data["message"]["from"].get("first_name")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Reply to user
        reply = f"Hello 👋, you said: {text}"
        async with httpx.AsyncClient() as client_req:
            await client_req.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )

        # Save to Google Sheet
        sheet.append_row([user, text, timestamp])

    return {"ok": True}
