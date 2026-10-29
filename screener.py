import os
import requests
import datetime
import json
import re

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SLOTS_FILE = "slots.json"
MAX_SLOTS = 8

def send_telegram_message(message):
    """텔레그램으로 분석 결과 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("경고: TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"텔레그램 전송 결과: {response.status_code}")
    except Exception as e:
        print(f"텔레그램 전송 에러: {e}")

def load_slots():
    """저장된 슬롯 데이터 로드 (없으면 8개 빈 슬롯 생성)"""
    if os.path.exists(SLOTS_FILE):
        try:
            with open(SLOTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"슬롯 로드 예외 발생: {e}")
    
    slots = []
    for i in range(1, MAX_SLOTS + 1):
        slots.append({
            "slot_id": i,
            "code": None,
            "name": None,
            "status": "EMPTY",
            "entry_price": 0,
            "target_1": 0,
            "target_2": 0,
            "stop_loss": 0,
            "news": ""
        })
    return slots

def save_slots(slots):
    """슬롯 데이터 저장"""
    try:
        with open(SLOTS_FILE, "w", encoding="utf-8") as f:
            json.dump(slots, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"슬롯 저장 실패: {e}")

def get_stock_news(stock_code):
    """종목별 최신 뉴스 파싱"""
    url = f"https://m.stock.naver.com/api/news/stock/{stock_code}?pageSize=1&page=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            news_data = res.json()
            if isinstance(news_data, list) and len(news_data) > 0:
                title = news_data[0].get("tit", "관련 뉴스 확인 중")
                return re.sub('<[^<]+?>', '', title)
    except:
        pass
    return "신규 모멘텀 및 수급 분석 중"

def get_current_price(code):
    """네이버 금융 현재가 조회"""
    url_sise = f"https://m.stock.naver.com/api/json/sise/searchStockInfo.nhn?code={code}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url_sise, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            nv = data.get("nv")
            if nv:
                return int(str(nv).replace(",", ""))
    except:
        pass
    return None

def format_slots_status(slots):
    """슬롯 현황 리포트 텍스트"""
    status_text = "📊 *[현재 8개 관리 종목 현황]*\n"
    for s in slots:
        if s["status"] == "EMPTY":
            status_text += f"• `[Slot {s['slot_id']:02d}]` 공석 (예수금 대기)\n"
        else:
            status_text += f"• `[Slot {s['slot_id']:02d}]` {s['name']} ({s['status']})\n"
    return status_text

def run_slot_manager():
    slots = load_slots()
    now_kst = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M')
    slot_changed = False
    
    # 1. 기존 종목 모니터링
    for s in slots:
        if s["status"] == "EMPTY":
            continue
            
        cur_price = get_current_price(s["code"])
        if not cur_price:
            continue
            
        if cur_price <= s["stop_loss"]:
            msg = (
                f"🛡️ *[⚠️ 손절 기준 이탈 & 공석 전환]*\n"
                f"📅 일시: `{now_kst}`\n\n"
                f"**[Slot {s['slot_id']:02d}] {s['name']} ({s['code']})** 이 손절가를 이탈했습니다.\n"
                f"• *현재가:* `{cur_price:,}원` (손절 기준: `{s['stop_loss']:,}원`)\n"
                f"• *조치:* 원칙에 따른 손절 매도 및 공석 전환\n\n"
            ) + format_slots_status(slots)
            send_telegram_message(msg)
            s.update({"code": None, "name": None, "status": "EMPTY", "entry_price": 0, "target_1": 0, "target_2": 0, "stop_loss": 0, "news": ""})
            slot_changed = True
            
        elif cur_price >= s["target_2"]:
            msg = (
                f"🚀 *[최종 익절 달성 & 공석 전환]*\n"
                f"📅 일시: `{now_kst}`\n\n"
                f"**[Slot {s['slot_id']:02d}] {s['name']} ({s['code']})** 이 2차 목표가를 달성했습니다!\n"
                f"• *현재가:* `{cur_price:,}원` (2차 목표: `{s['target_2']:,}원`)\n"
                f"• *조치:* 전량 익절 완료 후 공석 전환\n\n"
            ) + format_slots_status(slots)
            send_telegram_message(msg)
            s.update({"code": None, "name": None, "status": "EMPTY", "entry_price": 0, "target_1": 0, "target_2": 0, "stop_loss": 0, "news": ""})
            slot_changed = True
            
        elif cur_price >= s["target_1"] and s["status"] != "TARGET_1_ACHIEVED":
            s["status"] = "TARGET_1_ACHIEVED"
            slot_changed = True
            msg = (
                f"🎯 *[1차 목표가 도달]*\n"
                f"📅 일시: `{now_kst}`\n\n"
                f"**[Slot {s['slot_id']:02d}] {s['name']} ({s['code']})** 이 1차 목표가(`{s['target_1']:,}원`)에 도달했습니다.\n"
                f"• *현재가:* `{cur_price:,}원`\n"
                f"• *조치:* 50% 분할 익절 후 2차 목표가(`{s['target_2']:,}원`) 추세 유지\n"
            )
            send_telegram_message(msg)

    # 2. 빈자리 스캔 및 편입
    empty_slots = [s for s in slots if s["status"] == "EMPTY"]
    
    if len(empty_slots) > 0:
        url = "https://m.stock.naver.com/api/json/sise/siseListJson.nhn?menu=trade_amt&sosok=0&pageSize=20"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                items = res.json().get("result", {}).get("items", [])
                existing_codes = [s["code"] for s in slots if s["code"] is not None]
                
                for item in items:
                    if len(empty_slots) == 0:
                        break
                    code, name = item.get("cd", ""), item.get("nm", "")
                    if not code or code in existing_codes:
                        continue
                    try:
                        cur = int(str(item.get("nv", "0")).replace(",", ""))
                        cr = float(item.get("cr", "0"))
                    except:
                        continue
                        
                    if cur > 1000 and cr >= 0.0:
                        target_slot = empty_slots.pop(0)
                        t1, t2, sl = int(cur * 1.08), int(cur * 1.16), int(cur * 0.93)
                        news_title = get_stock_news(code)
                        
                        target_slot.update({
                            "code": code,
                            "name": name,
                            "status": "ACTIVE",
                            "entry_price": cur,
                            "target_1": t1,
                            "target_2": t2,
                            "stop_loss": sl,
                            "news": news_title
                        })
                        slot_changed = True
                        
                        add_msg = (
                            f"📥 *[신규 관리 종목 편입]*\n"
                            f"📅 일시: `{now_kst}`\n\n"
                            f"**[Slot {target_slot['slot_id']:02d}] {name} ({code})**\n"
                            f"• *모멘텀 뉴스:* {news_title}\n"
                            f"• *진입가:* `{cur:,}원`\n"
                            f"• *1차 목표가:* `{t1:,}원` | *2차 목표가:* `{t2:,}원`\n"
                            f"• *손절가:* `{sl:,}원`\n\n"
                        ) + format_slots_status(slots)
                        send_telegram_message(add_msg)
        except Exception as e:
            print(f"스캔 오류: {e}")

    if slot_changed:
        save_slots(slots)

if __name__ == "__main__":
    run_slot_manager()
