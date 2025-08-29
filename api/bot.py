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
    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    # Clear Telegram sheet & paste user message line by line
    telegram_sheet.clear()
    for line in text.split("\n"):
        telegram_sheet.append_row([line])

    # Read Site Down Hourly sheet
    records = site_down_sheet.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        df = pd.DataFrame([["No data"]], columns=["Site Down Hourly"])

    # Generate PNG table (optimized size)
    fig, ax = plt.subplots(figsize=(8, max(len(df)*0.3, 2)))
    ax.axis('off')
    ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    plt.close(fig)  # free memory

    # Use a single async client for both requests
    async with httpx.AsyncClient(timeout=15) as client_req:
        # Send PNG to user
        await client_req.post(
            f"{BASE_URL}/sendPhoto",
            files={"photo": ("site_down.png", buf, "image/png")},
            data={"chat_id": chat_id, "caption": "📊 Updated Site Down Hourly"}
        )

        # Send confirmation message
        await client_req.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": "✅ Your message has been logged!"}
        )

    return {"ok": True}
