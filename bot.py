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

# Initialize FastAPI
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

        # --- 1️⃣ Clear Telegram sheet and log user message ---
        try:
            telegram_sheet.clear()
            for line in text.split("\n"):
                # Split by "│" to separate columns, or use the whole line if not found
                row = [part.strip() for part in line.split("│")] if "│" in line else [line]
                telegram_sheet.append_row(row)
        except Exception as e:
            print("Error updating Telegram sheet:", e)

        # --- 2️⃣ Generate Site Down Hourly PNG ---
        buf = None
        try:
            records = site_down_sheet.get_all_records()
            df = pd.DataFrame(records)
            if df.empty:
                df = pd.DataFrame([["No data"]], columns=["Site Down Hourly"])

            # Limit to 30 rows to avoid timeout/memory issues
            df = df.head(30)

            fig, ax = plt.subplots(figsize=(8, max(len(df)*0.4, 2)))
            ax.axis('off')
            ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')

            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            plt.close(fig)
        except Exception as e:
            print("PNG generation error:", e)

        # --- 3️⃣ Send PNG and confirmation message ---
        async with httpx.AsyncClient(timeout=15) as client_req:
            if buf:
                try:
                    resp = await client_req.post(
                        f"{BASE_URL}/sendPhoto",
                        files={"photo": ("site_down.png", buf, "image/png")},
                        data={"chat_id": chat_id, "caption": "📊 Updated Site Down Hourly"}
                    )
                    print("sendPhoto response:", resp.status_code, resp.text)
                except Exception as e:
                    print("Error sending PNG:", e)

            # Always send text confirmation
            try:
                resp = await client_req.post(
                    f"{BASE_URL}/sendMessage",
                    json={"chat_id": chat_id, "text": "✅ Your message has been logged in Telegram sheet!"}
                )
                print("sendMessage response:", resp.status_code, resp.text)
            except Exception as e:
                print("Error sending confirmation:", e)

    except Exception as e:
        print("Webhook error:", e)

    # Always return 200 OK to Telegram
    return {"ok": True}
