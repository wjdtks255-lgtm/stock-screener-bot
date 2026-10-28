import os
import requests
import yfinance as yf
import pandas as pd

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            print("텔레그램 메시지 전송 성공")
        else:
            print(f"전송 실패: {res.text}")
    except Exception as e:
        print(f"에러: {e}")

def check_ricebowl_stock(ticker_symbol):
    df = yf.download(ticker_symbol, period="1y", interval="1d")
    if len(df) < 224:
        return
    
    df['SMA112'] = df['Close'].rolling(window=112).mean()
    df['SMA224'] = df['Close'].rolling(window=224).mean()
    
    recent = df.iloc[-1]
    prev_6m = df.iloc[-120]
    
    current_price = float(recent['Close'])
    sma112 = float(recent['SMA112'])
    sma224 = float(recent['SMA224'])
    
    # 밥그릇 3번 자리 추세 전환/224일선 상향 조건
    max_high = df['High'].iloc[-250:-60].max()
    is_dropped = (max_high - prev_6m['Close']) / max_high >= 0.35
    is_above_224 = current_price >= sma224 and current_price >= sma112
    
    if is_dropped and is_above_224:
        msg = f"🥣 *[밥그릇 패턴 3번 자리 포착]*\n- 종목: `{ticker_symbol}`\n- 현재가: {current_price:,.0f}원\n- 224일선: {sma224:,.0f}원\n- 112일선: {sma112:,.0f}원"
        send_telegram_msg(msg)

# 관심 종목 리스트 (필요한 종목 추가 가능)
tickers = ["005930.KS", "000660.KS", "035420.KS", "035720.KS"]
for t in tickers:
    check_ricebowl_stock(t)
