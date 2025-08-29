import os
from fastapi import FastAPI, Request
import httpx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

SHEET_ID = os.getenv("SHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_CRED_JSON")

scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(SERVICE_ACCOUNT_JSON), scope)
client = gspread.authorize(creds)

telegram_sheet = client.open_by_key(SHEET_ID).worksheet("Telegram")

@app.post("/api/bot")
async def webhook(req: Request):
    data = await req.json()
    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    # Clear sheet
    telegram_sheet.clear()

    # Append user message line by line
    for line in text.split("\n"):
        telegram_sheet.append_row([line])

    # Send confirmation to Telegram
    async with httpx.AsyncClient(timeout=15) as client_req:
        resp = await client_req.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": "✅ Message logged successfully!"}
        )
        # Log Telegram response for debugging
        print("Telegram sendMessage response:", resp.status_code, resp.text)

    return {"ok": True}
