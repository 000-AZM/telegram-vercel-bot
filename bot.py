import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# Telegram token from Vercel environment
TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

@app.post("/api/bot")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        if "message" not in data:
            return {"ok": True}

        chat_id = data["message"]["chat"]["id"]

        # Send a simple text reply
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": chat_id, "text": "✅ Test reply received!"}
            )

    except Exception as e:
        print("Webhook error:", e)

    # Always return 200 OK to Telegram
    return {"ok": True}
