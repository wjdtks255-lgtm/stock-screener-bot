import os
import io
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

def get_krx_tickers():
    tickers = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        for sosok, suffix in [(0, ".KS"), (1, ".KQ")]:
            for page in range(1, 40):
                url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
                res = requests.get(url, headers=headers)
                res.encoding = 'cp949'
                dfs = pd.read_html(io.StringIO(res.text))
                df = dfs[1]
                df = df.dropna(subset=['종목명'])
                if len(df) == 0:
                    break
                for _, row in df.iterrows():
                    code = str(row['종목코드']).zfill(6)
                    tickers.append(code + suffix)
        unique_tickers = list(set(tickers))
        print(f"총 {len(unique_tickers)}개의 국내 전체 종목 코드를 성공적으로 불러왔습니다.")
        return unique_tickers
    except Exception as e:
        print(f"종목 리스트 수집 실패: {e}")
        return ["005930.KS", "000660.KS", "373220.KS", "207940.KS", "005380.KS", "035420.KS", "035720.KS"]

def check_ricebowl_stock(ticker_symbol):
    try:
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
        
        max_high = float(df['High'].iloc[-250:-60].max())
        prev_close = float(prev_6m['Close'])
        
        is_dropped = (max_high - prev_close) / max_high >= 0.35
        is_above_224 = (current_price >= sma224) and (current_price >= sma112)
        
        if is_dropped and is_above_224:
            msg = f"🥣 *[밥그릇 패턴 3번 자리 포착]*\n- 종목코드: `{ticker_symbol}`\n- 현재가: {current_price:,.0f}원\n- 224일선: {sma224:,.0f}원\n- 112일선: {sma112:,.0f}원"
            send_telegram_msg(msg)
            print(f"★ 포착 완료 및 전송: {ticker_symbol}")
    except Exception as e:
        pass

tickers = get_krx_tickers()
if tickers:
    print(f"전체 종목 대상 밥그릇 패턴 분석을 시작합니다...")
    for t in tickers:
        check_ricebowl_stock(t)
    print("전체 종목 스캔 및 분석 완료!")
else:
    print("스캔할 종목 리스트가 비어 있습니다.")
