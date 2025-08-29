import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

@app.get("/")
async def home():
    return {"ok": True, "message": "Bot is running"}

@app.post("/api/bot")
async def telegram_webhook(req: Request):
    data = await req.json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        reply = f"Hello 👋, you said: {text}"

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )
    return {"ok": True}
