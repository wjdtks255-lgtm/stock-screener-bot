import os
import requests
import datetime
# import FinanceDataReader as fdr  # 주가 및 거래대금 데이터 수집용 (필요시 설치)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """텔레그램으로 분석 결과 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"텔레그램 전송 실패: {response.text}")

def fetch_market_data_and_news():
    """
    1. 오늘 나온 뉴스 키워드 매칭 및 수급(거래대금 터진 종목) 필터링 로직 구현부
    2. 여기서는 예시 구조를 제공합니다. 실제 연동 시 PyKrx, FinanceDataReader 또는 증권사 API 활용
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] 시장 수급 및 뉴스 스캔 시작...")
    
    # [예시 데이터] 실제로 돈이 붙었다고 가정되는 종목 리스트
    # 실전에서는 거래대금 상위 종목 중 외인/기관 순매수 동반 및 당일 뉴스 키워드가 매칭되는 종목을 필터링
    hot_stocks = [
        {
            "name": "예시종목A",
            "code": "000000",
            "turnover": "1,500억",
            "sugep": "외인+기관 양매수",
            "news": "정부 신사업 육성 정책 발표 및 대규모 수주 기대감",
            "support": "12,000원",
            "resistance": "15,000원",
            "scenario": "단기 박스권 상단 돌파 시 17,000원까지 룸 열림. 단, 11,500원 이탈 시 관망."
        }
    ]
    return hot_stocks

def analyze_and_report():
    stocks = fetch_market_data_and_news()
    
    if not stocks:
        msg = "📢 *[시장 스캔 결과]*\n\n오늘 장에서 기준(거래대금·수급)을 만족한 종목이 없습니다."
        send_telegram_message(msg)
        return

    report = f"🚨 *[AI 주식 수급 및 시나리오 리포트]*\n"
    report += f"📅 일시: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}`\n"
    report += "-----------------------------------\n\n"

    for idx, item in enumerate(stocks, 1):
        report += f"*{idx}. {item['name']} ({item['code'])*`\n"
        report += f"• *거래대금/수급:* {item['turnover']} / {item['sugep']}\n"
        report += f"• *관련 뉴스:* {item['news']}\n"
        report += f"• *핵심 가격:* 지지 `{item['support']}` | 저항 `{item['resistance']}`\n"
        report += f"• *💡 대응 시나리오:* \n  {item['scenario']}\n\n"
        report += "-----------------------------------\n"

    send_telegram_message(report)

if __name__ == "__main__":
    analyze_and_report()
