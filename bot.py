import os
from fastapi import FastAPI, Request
import httpx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Serverless-safe backend
import matplotlib.pyplot as plt
from io import BytesIO
import tempfile

# Use /tmp for matplotlib cache (Vercel serverless)
tmpdir = tempfile.mkdtemp()
matplotlib.rcParams['cache.directory'] = tmpdir

app = FastAPI()

# Telegram bot
TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Google Sheets
SHEET_ID = os.getenv("SHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_CRED_JSON")

scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(SERVICE_ACCOUNT_JSON), scope)
client = gspread.authorize(creds)

# Worksheets
telegram_sheet = client.open_by_key(SHEET_ID).worksheet("Telegram")
site_down_sheet = client.open_by_key(SHEET_ID).worksheet("Site Down Hourly")

@app.post("/api/bot")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        if "message" not in data:
            return {"ok": True}

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # --- 1️⃣ Update Telegram sheet ---
        try:
            telegram_sheet.clear()
            for line in text.split("\n"):
                row = [part.strip() for part in line.split("│")] if "│" in line else [line]
                telegram_sheet.append_row(row)
        except Exception as e:
            print("Error updating Telegram sheet:", e)

        # --- 2️⃣ Generate PNG safely ---
        buf = None
        try:
            records = site_down_sheet.get_all_records()
            df = pd.DataFrame(records)
            if df.empty:
                df = pd.DataFrame([["No data"]], columns=["Site Down Hourly"])

            df = df.head(30)  # limit rows

            fig, ax = plt.subplots(figsize=(8, max(len(df)*0.4, 2)))
            ax.axis('off')
            ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')

            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            plt.close(fig)
        except Exception as e:
            print("PNG generation error:", e)

        # --- 3️⃣ Send PNG and confirmation text ---
        async with httpx.AsyncClient(timeout=15) as client_req:
            # Send PNG if available
            if buf:
                try:
                    await client_req.post(
                        f"{BASE_URL}/sendPhoto",
                        files={"photo": ("site_down.png", buf, "image/png")},
                        data={"chat_id": chat_id, "caption": "📊 Updated Site Down Hourly"}
                    )
                except Exception as e:
                    print("Error sending PNG:", e)

            # Always send text confirmation
            try:
                await client_req.post(
                    f"{BASE_URL}/sendMessage",
                    json={"chat_id": chat_id, "text": "✅ Your message has been logged in Telegram sheet!"}
                )
            except Exception as e:
                print("Error sending confirmation:", e)

    except Exception as e:
        print("Webhook error:", e)

    # Always return 200 OK
    return {"ok": True}
