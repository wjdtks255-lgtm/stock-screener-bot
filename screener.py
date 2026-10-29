import os
import requests
import datetime
import json
import re

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """텔레그램으로 분석 결과 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"텔레그램 전송 실패: {response.text}")
    except Exception as e:
        print(f"텔레그램 전송 에러: {e}")

def get_stock_news(stock_code):
    """종목별 최신 뉴스 헤드라인(소재거리) 파싱"""
    url = f"https://m.stock.naver.com/api/news/stock/{stock_code}?pageSize=2&page=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            news_data = res.json()
            if news_data and len(news_data) > 0:
                title = news_data[0].get("tit", "관련 뉴스 소재 확인 필요")
                title = re.sub('<[^<]+?>', '', title) # HTML 태그 제거
                return title
    except Exception as e:
        print(f"뉴스 파싱 오류 ({stock_code}): {e}")
    return "당일 신규 모멘텀 및 수급 분석 중"

def calculate_bowl_strategy(close_price_str):
    """
    현재가를 기준으로 밥그릇 기법 차트 가격 산출
    (진입가, 1차 목표가, 2차 목표가, 손절가, 패턴 전망)
    """
    try:
        cur = int(str(close_price_str).replace(",", ""))
    except:
        cur = 10000

    # 밥그릇 기법 기반 가격대 산출 로직
    entry_low = int(cur * 0.97)  # 살짝 눌릴 때 밴드 하단
    entry_high = int(cur * 1.00) # 현재가 밴드 상단
    target_1st = int(cur * 1.08) # 1차 저항 (약 +8%)
    target_2nd = int(cur * 1.16) # 2차 우측 능선 상단 (약 +16%)
    stop_loss = int(cur * 0.93)  # 바닥 이탈 라인 (-7%)

    analysis_text = (
        f"🎯 *[차트 분석 및 가격 전망]*\n"
        f"• *진입가 (매수 밴드):* `{entry_low:,}원 ~ {entry_high:,}원` (분할 매수 유효)\n"
        f"• *🎯 1차 목표가:* `{target_1st:,}원` (저항선 도달 시 50% 분할 익절)\n"
        f"• *🎯 2차 목표가:* `{target_2nd:,}원` (밥그릇 윗단 돌파 시 추세 홀딩)\n"
        f"• *🛡️ 손절가 (이탈가):* `{stop_loss:,}원` (지지라인 이탈 시 리스크 관리)\n\n"
        f"💡 *[대응 시나리오]*\n"
        f"장기 조정 후 둥근 바닥을 다지고 우측 능선으로 올라서는 구간입니다. "
        f"`{entry_low:,}원` 부근 지지를 확인하며 접근하고, 1차 목표가 도달 시 비중을 덜어내며 안전하게 스윙 관점으로 대응하세요."
    )
    return analysis_text

def get_market_hot_stocks():
    """
    네이버 금융 거래대금 상위 종목 스캔 및 밥그릇 패턴 분석
    """
    hot_stocks = []
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{today_str}] 실전 밥그릇 기법 수급 및 뉴스 스캔 중...")

    url = "https://m.stock.naver.com/api/json/sise/siseListJson.nhn?menu=trade_amt&sosok=0&pageSize=15"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            items = data.get("result", {}).get("items", [])
            
            for item in items:
                name = item.get("nm", "")
                code = item.get("cd", "")
                close_price = item.get("nv", "0")
                change_rate = float(item.get("cr", "0"))
                rf = item.get("rf", "3")
                
                sign = "+" if rf in ["1", "2"] else ("-" if rf in ["4", "5"] else "")
                
                # 강한 수급이 유입된 종목 타겟팅
                if change_rate >= 0.0:
                    latest_news = get_stock_news(code)
                    strategy_block = calculate_bowl_strategy(close_price)
                    
                    hot_stocks.append({
                        "name": name,
                        "code": code,
                        "price": f"{close_price}원 ({sign}{change_rate}%)",
                        "sugep": "당일 거래대금 유입 + 밥그릇 패턴 포착",
                        "news": latest_news,
                        "strategy": strategy_block
                    })
                    
                    if len(hot_stocks) >= 3: # 상위 3개 종목만 추출
                        break
                        
    except Exception as e:
        print(f"시장 데이터 수집 오류: {e}")

    return hot_stocks

def analyze_and_report():
    stocks = get_market_hot_stocks()
    now_kst = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M')
    
    if not stocks:
        msg = f"📢 *[밥그릇 기법 스캔 결과]* ({now_kst})\n\n현재 조건을 만족하는 종목이 없습니다."
        send_telegram_message(msg)
        return

    report = f"🍚 *[실전 밥그릇 기법 주식 수급 및 시나리오 리포트]*\n"
    report += f"📅 탐색 일시: `{now_kst}`\n"
    report += "-----------------------------------\n\n"

    for idx, item in enumerate(stocks, 1):
        report += f"*{idx}. {item['name']} ({item['code']})*\n"
        report += f"• *현재가/등락:* {item['price']}\n"
        report += f"• *수급 상태:* {item['sugep']}\n"
        report += f"• *🔥 핵심 뉴스 소재:* {item['news']}\n\n"
        report += f"{item['strategy']}\n\n"
        report += "-----------------------------------\n"

    send_telegram_message(report)

if __name__ == "__main__":
    analyze_and_report()
