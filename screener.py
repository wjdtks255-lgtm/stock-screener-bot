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

def load_slots():
    """저장된 슬롯 데이터 로드 (없으면 8개 빈 슬롯 생성)"""
    if os.path.exists(SLOTS_FILE):
        try:
            with open(SLOTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    
    slots = []
    for i in range(1, MAX_SLOTS + 1):
        slots.append({
            "slot_id": i,
            "code": None,
            "name": None,
            "status": "EMPTY", # EMPTY, ACTIVE, TARGET_1_ACHIEVED
            "entry_price": 0,
            "target_1": 0,
            "target_2": 0,
            "stop_loss": 0,
            "news": ""
        })
    return slots

def save_slots(slots):
    """슬롯 데이터 저장"""
    with open(SLOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(slots, f, ensure_ascii=False, indent=4)

def get_stock_news(stock_code):
    """종목별 최신 뉴스 헤드라인 파싱"""
    url = f"https://m.stock.naver.com/api/news/stock/{stock_code}?pageSize=1&page=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            news_data = res.json()
            if news_data and len(news_data) > 0:
                title = news_data[0].get("tit", "관련 뉴스 확인 중")
                return re.sub('<[^<]+?>', '', title)
    except:
        pass
    return "신규 모멘텀 및 수급 분석 중"

def get_current_price(code):
    """네이버 금융에서 종목의 현재가 조회"""
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
    """현재 8칸 슬롯 현황 텍스트 생성"""
    status_text = "📊 *[현재 8칸 슬롯 현황]*\n"
    for s in slots:
        if s["status"] == "EMPTY":
            status_text += f"• `[Slot {s['slot_id']:02d}]` 비어있음 (예수금 대기)\n"
        else:
            status_text += f"• `[Slot {s['slot_id']:02d}]` {s['name']} ({s['status']})\n"
    return status_text

def run_slot_manager():
    slots = load_slots()
    now_kst = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M')
    
    # 1단계: 기존 슬롯 종목들의 가격 추적 (목표가/손절가 체크)
    slot_changed = False
    for s in slots:
        if s["status"] == "EMPTY":
            continue
            
        cur_price = get_current_price(s["code"])
        if not cur_price:
            continue
            
        # 손절가 이탈 체크
        if cur_price <= s["stop_loss"]:
            msg = (
                f"🛡️ *[⚠️ 종목 슬롯 손절 이탈 & 슬롯 비움]*\n"
                f"📅 일시: `{now_kst}`\n\n"
                f"**[Slot {s['slot_id']:02d}] {s['name']} ({s['code']})** 가 손절가를 이탈했습니다!\n"
                f"• *현재가:* `{cur_price:,}원` (손절 기준: `{s['stop_loss']:,}원` 이탈)\n"
                f"• *조치:* 원칙에 따라 슬롯을 비우고 현금 회수\n\n"
            )
            msg += format_slots_status(slots)
            send_telegram_message(msg)
            
            s.update({"code": None, "name": None, "status": "EMPTY", "entry_price": 0, "target_1": 0, "target_2": 0, "stop_loss": 0, "news": ""})
            slot_changed = True
            
        # 2차 목표가 달성 체크 (최종 익절)
        elif cur_price >= s["target_2"]:
            msg = (
                f"🚀 *[종목 슬롯 최종 익절 마감 & 슬롯 비움]*\n"
                f"📅 일시: `{now_kst}`\n\n"
                f"**[Slot {s['slot_id']:02d}] {s['name']} ({s['code']})** 이 2차 목표가를 달성했습니다!\n"
                f"• *현재가:* `{cur_price:,}원` (2차 목표: `{s['target_2']:,}원` 돌파)\n"
                f"• *조치:* 전량 익절 완료 후 슬롯 비움 (예수금 전환)\n\n"
            )
            msg += format_slots_status(slots)
            send_telegram_message(msg)
            
            s.update({"code": None, "name": None, "status": "EMPTY", "entry_price": 0, "target_1": 0, "target_2": 0, "stop_loss": 0, "news": ""})
            slot_changed = True
            
        # 1차 목표가 달성 체크
        elif cur_price >= s["target_1"] and s["status"] != "TARGET_1_ACHIEVED":
            s["status"] = "TARGET_1_ACHIEVED"
            slot_changed = True
            msg = (
                f"🎯 *[종목 슬롯 1차 목표가 도달]*\n"
                f"📅 일시: `{now_kst}`\n\n"
                f"**[Slot {s['slot_id']:02d}] {s['name']} ({s['code']})** 이 1차 목표가(`{s['target_1']:,}원`)에 도달했습니다!\n"
                f"• *현재가:* `{cur_price:,}원`\n"
                f"• *조치:* 50% 분할 익절 후 2차 목표가(`{s['target_2']:,}원`) 추세 대기\n"
            )
            send_telegram_message(msg)

    # 2단계: 빈칸(EMPTY) 개수 확인
    empty_slots = [s for s in slots if s["status"] == "EMPTY"]
    
    if len(empty_slots) == 0:
        print(f"[{now_kst}] 8개 슬롯이 모두 가득 차 있어 신규 종목 탐색을 대기합니다.")
        if slot_changed:
            save_slots(slots)
        return

    print(f"[{now_kst}] 현재 빈 슬롯 {len(empty_slots)}개 발견. 밥그릇 기법 종목 스캔 중...")

    # 3단계: 빈칸이 있다면 새로운 밥그릇 종목 스캔 후 채우기
    url = "https://m.stock.naver.com/api/json/sise/siseListJson.nhn?menu=trade_amt&sosok=0&pageSize=20"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            items = data.get("result", {}).get("items", [])
            
            existing_codes = [s["code"] for s in slots if s["code"] is not None]
            
            for item in items:
                if len(empty_slots) == 0:
                    break
                    
                code = item.get("cd", "")
                name = item.get("nm", "")
                
                if code in existing_codes:
                    continue
                    
                try:
                    cur = int(str(item.get("nv", "0")).replace(",", ""))
                    change_rate = float(item.get("cr", "0"))
                except:
                    continue
                    
                if cur > 1000 and change_rate >= 0.0:
                    target_slot = empty_slots.pop(0)
                    
                    entry = cur
                    t1 = int(cur * 1.08)
                    t2 = int(cur * 1.16)
                    sl = int(cur * 0.93)
                    news_title = get_stock_news(code)
                    
                    target_slot.update({
                        "code": code,
                        "name": name,
                        "status": "ACTIVE",
                        "entry_price": entry,
                        "target_1": t1,
                        "target_2": t2,
                        "stop_loss": sl,
                        "news": news_title
                    })
                    
                    slot_changed = True
                    
                    add_msg = (
                        f"📥 *[신규 종목 슬롯 편입 (Slot Assigned)]*\n"
                        f"📅 일시: `{now_kst}`\n\n"
                        f"**새로운 종목이 [Slot {target_slot['slot_id']:02d}]에 편입되었습니다!**\n\n"
                        f"• *종목명:* `{name} ({code})`\n"
                        f"• *🔥 핵심 뉴스:* {news_title}\n"
                        f"• *매수 진입가:* `{entry:,}원`\n"
                        f"• *🎯 1차 목표가:* `{t1:,}원` | *🎯 2차 목표가:* `{t2:,}원`\n"
                        f"• *🛡️ 손절 기준가:* `{sl:,}원`\n\n"
                    )
                    add_msg += format_slots_status(slots)
                    send_telegram_message(add_msg)

    except Exception as e:
        print(f"신규 종목 스캔 중 오류: {e}")

    if slot_changed:
        save_slots(slots)
        print("슬롯 상태가 업데이트되어 저장되었습니다.")

if __name__ == "__main__":
    run_slot_manager()
