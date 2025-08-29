import os
from fastapi import FastAPI, Request
import httpx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

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

        # Reply to user
        reply = "✅ Message logged in Google Sheet."
        async with httpx.AsyncClient() as client_req:
            await client_req.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )

        # Clear the sheet
        sheet.clear()

        # Paste user message line by line
        for line in text.split("\n"):
            sheet.append_row([line])

    return {"ok": True}
