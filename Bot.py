import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import requests
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

# === CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ASSETS = {
    "GC=F": {"name": "Or (Futures)", "cat": "Matières premières"},
    "GLD":  {"name": "Or ETF", "cat": "Matières premières"},
    "CL=F": {"name": "Pétrole WTI", "cat": "Matières premières"},
    "USO":  {"name": "Pétrole ETF", "cat": "Matières premières"},
    "SI=F": {"name": "Argent", "cat": "Matières premières"},
    "EURUSD=X": {"name": "EUR/USD", "cat": "Forex"},
    "GBPUSD=X": {"name": "GBP/USD", "cat": "Forex"},
    "USDJPY=X": {"name": "USD/JPY", "cat": "Forex"},
    "USDCHF=X": {"name": "USD/CHF", "cat": "Forex"},
    "USDCAD=X": {"name": "USD/CAD", "cat": "Forex"},
    "BTC-USD": {"name": "Bitcoin", "cat": "Crypto"},
    "ETH-USD": {"name": "Ethereum", "cat": "Crypto"},
}

def get_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="6mo")
        if df.empty or len(df) < 50:
            return None
        return df
    except:
        return None

def analyse(ticker, meta):
    df = get_data(ticker)
    if df is None:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    ema9 = EMAIndicator(close, 9).ema_indicator()
    ema21 = EMAIndicator(close, 21).ema_indicator()
    ema50 = EMAIndicator(close, 50).ema_indicator()
    rsi = RSIIndicator(close, 14).rsi()
    macd = MACD(close)
    adx = ADXIndicator(high, low, close, 14).adx()
    atr = AverageTrueRange(high, low, close, 14).average_true_range()

    last = df.iloc[-1]
    score = 50

    # Tendance
    if ema9.iloc[-1] > ema21.iloc[-1] > ema50.iloc[-1]:
        score += 18
    elif ema9.iloc[-1] < ema21.iloc[-1] < ema50.iloc[-1]:
        score -= 15

    if last["Close"] > ema50.iloc[-1]:
        score += 8
    else:
        score -= 6

    # RSI
    r = rsi.iloc[-1]
    if r < 30:
        score += 12
    elif r < 40:
        score += 7
    elif r > 70:
        score -= 10
    elif r > 60:
        score -= 4

    # MACD
    if macd.macd().iloc[-1] > macd.macd_signal().iloc[-1]:
        score += 6
    else:
        score -= 5

    # ADX
    if adx.iloc[-1] > 25:
        score += 5

    score = max(0, min(100, score))

    if score >= 72:
        signal = "FORT ACHAT"
    elif score >= 58:
        signal = "ACHAT"
    elif score >= 45:
        signal = "NEUTRE"
    else:
        signal = "ÉVITER"

    return {
        "name": meta["name"],
        "cat": meta["cat"],
        "price": round(last["Close"], 2 if last["Close"] > 10 else 4),
        "score": round(score),
        "signal": signal,
        "rsi": round(r, 1),
        "change": round((last["Close"] / df["Close"].iloc[-21] - 1) * 100, 1)
    }

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload, timeout=30)
    print("Status code:", response.status_code)
    print("Réponse Telegram:", response.text)

def main():
    results = []
    for ticker, meta in ASSETS.items():
        res = analyse(ticker, meta)
        if res:
            results.append(res)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    msg = f"<b>📊 ANALYSE DU {now}</b>\n\n"
    msg += "<b>Classement technique :</b>\n\n"

    for i, r in enumerate(results, 1):
        emoji = "🟢" if r["score"] >= 65 else "🟡" if r["score"] >= 50 else "🔴"
        msg += f"{emoji} <b>{i}. {r['name']}</b>\n"
        msg += f"   Score: {r['score']}/100 | {r['signal']}\n"
        msg += f"   Prix: {r['price']} | 20j: {r['change']}% | RSI: {r['rsi']}\n\n"

    # Top suggestions
    top = [r for r in results if r["score"] >= 60][:4]
    msg += "<b>💡 Meilleures opportunités :</b>\n"
    if top:
        for t in top:
            msg += f"• {t['name']} ({t['score']}/100)\n"
    else:
        msg += "Aucune opportunité claire pour le moment.\n"

    msg += "\n<i>Analyse purement technique – Pas un conseil financier</i>"

    send_telegram(msg)
    print("Analyse envoyée avec succès")

if __name__ == "__main__":
    main()
