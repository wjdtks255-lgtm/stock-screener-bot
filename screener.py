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
    """종목별 최신 뉴스 헤드라인 파싱"""
    url = f"https://m.stock.naver.com/api/news/stock/{stock_code}?pageSize=2&page=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            news_data = res.json()
            if news_data and len(news_data) > 0:
                title = news_data[0].get("tit", "관련 뉴스 제목 없음")
                title = re.sub('<[^<]+?>', '', title) # HTML 태그 제거
                return title
    except Exception as e:
        print(f"뉴스 파싱 오류 ({stock_code}): {e}")
    return "당일 신규 뉴스 스캔 중"

def get_market_hot_stocks():
    """
    네이버 금융 실시간 '거래대금 상위' 종목 및 실시간 뉴스 파싱
    """
    hot_stocks = []
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{today_str}] 시장 거래대금 및 수급 종목 스캔 중...")

    # [핵심 수정] 시가총액 순서(market_sum)가 아닌 진짜 '거래대금 상위(trade_amt)' API로 변경
    url = "https://m.stock.naver.com/api/json/sise/siseListJson.nhn?menu=trade_amt&sosok=0&pageSize=10"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            items = data.get("result", {}).get("items", [])
            
            # 상위 3개 핵심 종목 추출
            for item in items[:3]:
                name = item.get("nm", "")
                code = item.get("cd", "")
                close_price = item.get("nv", "0")
                change_rate = item.get("cr", "0")
                rf = item.get("rf", "3") # 등락구분
                
                # 등락 기호
                sign = "+" if rf in ["1", "2"] else ("-" if rf in ["4", "5"] else "")
                
                # 종목 관련 뉴스 수집
                latest_news = get_stock_news(code)
                
                hot_stocks.append({
                    "name": name,
                    "code": code,
                    "price": f"{close_price}원 ({sign}{change_rate}%)",
                    "sugep": "당일 거래대금 상위 / 강한 수급 유입",
                    "news": latest_news,
                    "scenario": f"실시간 거래대금 동반 구간. 분봉상 주요 마디가 및 당일 고점 돌파 여부 지속 관찰 필요."
                })
    except Exception as e:
        print(f"시장 데이터 수집 오류: {e}")

    return hot_stocks

def analyze_and_report():
    stocks = get_market_hot_stocks()
    now_kst = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M')
    
    if not stocks:
        msg = f"📢 *[시장 스캔 결과]* ({now_kst})\n\n현재 포착된 실시간 수급 집중 종목이 없습니다."
        send_telegram_message(msg)
        return

    report = f"🚨 *[실시간 주식 수급 및 뉴스 리포트]*\n"
    report += f"📅 탐색 일시: `{now_kst}`\n"
    report += "-----------------------------------\n\n"

    for idx, item in enumerate(stocks, 1):
        report += f"*{idx}. {item['name']} ({item['code']})*\n"
        report += f"• *현재가/등락:* {item['price']}\n"
        report += f"• *수급 상태:* {item['sugep']}\n"
        report += f"• *실시간 뉴스:* {item['news']}\n"
        report += f"• *💡 대응 시나리오:* \n  {item['scenario']}\n\n"
        report += "-----------------------------------\n"

    send_telegram_message(report)

if __name__ == "__main__":
    analyze_and_report()
