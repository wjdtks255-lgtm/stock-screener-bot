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
    # yfinance 최신 버전의 MultiIndex 열 구조 단일화 처리
    df = yf.download(ticker_symbol, period="1y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if len(df) < 224:
        return
    
    df['SMA112'] = df['Close'].rolling(window=112).mean()
    df['SMA224'] = df['Close'].rolling(window=224).mean()
    
    recent = df.iloc[-1]
    prev_6m = df.iloc[-120]
    
    current_price = float(recent['Close'].item() if hasattr(recent['Close'], 'item') else recent['Close'])
    sma112 = float(recent['SMA112'].item() if hasattr(recent['SMA112'], 'item') else recent['SMA112'])
    sma224 = float(recent['SMA224'].item() if hasattr(recent['SMA224'], 'item') else recent['SMA224'])
    
    # 밥그릇 3번 자리 추세 전환/224일선 상향 조건
    max_high = float(df['High'].iloc[-250:-60].max())
    prev_close = float(prev_6m['Close'])
    
    is_dropped = (max_high - prev_close) / max_high >= 0.35
    is_above_224 = (current_price >= sma224) and (current_price >= sma112)
    
    if is_dropped and is_above_224:
        msg = f"🥣 *[밥그릇 패턴 3번 자리 포착]*\n- 종목: `{ticker_symbol}`\n- 현재가: {current_price:,.0f}원\n- 224일선: {sma224:,.0f}원\n- 112일선: {sma112:,.0f}원"
        send_telegram_msg(msg)
    else:
        print(f"{ticker_symbol}: 조건 미충족 (정상 스캔 완료)")

# 스캔할 종목 리스트
tickers = ["005930.KS", "000660.KS", "035420.KS", "035720.KS"]
for t in tickers:
    check_ricebowl_stock(t)
