import os
from fastapi import FastAPI, Request
import httpx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

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

# Sheets
telegram_sheet = client.open_by_key(SHEET_ID).worksheet("Telegram")
site_down_sheet = client.open_by_key(SHEET_ID).worksheet("Site Down Hourly")

@app.post("/api/bot")
async def telegram_webhook(req: Request):
    data = await req.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # 1️⃣ Clear Telegram sheet & paste user message line by line
        telegram_sheet.clear()
        for line in text.split("\n"):
            telegram_sheet.append_row([line])

        # 2️⃣ Read Site Down Hourly sheet
        records = site_down_sheet.get_all_records()
        df = pd.DataFrame(records)

        # If sheet is empty, create placeholder
        if df.empty:
            df = pd.DataFrame([["No data"]], columns=["Site Down Hourly"])

        # 3️⃣ Generate PNG table
        fig, ax = plt.subplots(figsize=(8, len(df)*0.5+1))
        ax.axis('off')
        ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)

        # 4️⃣ Send PNG to Telegram
        async with httpx.AsyncClient() as client_req:
            await client_req.post(
                f"{BASE_URL}/sendPhoto",
                files={"photo": ("site_down.png", buf, "image/png")},
                data={"chat_id": chat_id, "caption": "Updated Site Down Hourly"}
            )

        # 5️⃣ Reply confirmation
        async with httpx.AsyncClient() as client_req:
            await client_req.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": chat_id, "text": "✅ Your message has been logged!"}
            )

    return {"ok": True}
