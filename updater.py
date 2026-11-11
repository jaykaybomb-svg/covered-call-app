#!/usr/bin/env python3
"""
Covered Call Tracker v2.0 - 국내 상장 커버드콜 ETF 시초가 / 12시 정오가 / 마감종가 수집기
표준 라이브러리(urllib, json, os, datetime)만 사용하여 별도 pip 패키지 설치 없이 동작합니다.
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

DEFAULT_KR_TICKERS = [
    ("498400", "KODEX 200타겟위클리커버드콜"),
    ("486290", "TIGER 미국나스닥100타겟데일리커버드콜"),
    ("482730", "TIGER 미국S&P500타겟데일리커버드콜"),
    ("472150", "TIGER 배당커버드콜액티브"),
    ("483290", "KODEX 미국배당다우존스타겟커버드콜"),
    ("475720", "RISE 200위클리커버드콜"),
    ("494300", "KODEX 미국나스닥100데일리커버드콜OTM"),
    ("0198A0", "KIWOOM 코스닥150커버드콜액티브"),
    ("0104N0", "TIGER 200타겟위클리커버드콜"),
    ("0167B0", "SOL 200타겟위클리커버드콜"),
    ("0008S0", "TIGER 미국배당다우존스타겟데일리커버드콜"),
    ("166400", "TIGER 200커버드콜OTM"),
    ("289480", "TIGER 200커버드콜"),
    ("0177R0", "TIGER 반도체TOP10커버드콜액티브"),
]


def parse_num(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _fetch_naver_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://m.stock.naver.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_naver_etf_price(ticker: str):
    """네이버 모바일 증권 API에서 당일 시초가(openPrice), 현재/종가(closePrice), 전일종가 조회"""
    data = _fetch_naver_json(f"https://m.stock.naver.com/api/stock/{ticker}/basic")

    close_price = parse_num(data.get("closePrice"))
    open_price = parse_num(data.get("openPrice"))
    prev_close = parse_num(data.get("compareToPreviousClosePrice"))
    change_pct = parse_num(data.get("fluctuationsRatio"))
    if prev_close != 0 and close_price > 0:
        # compareToPreviousClosePrice가 전일대비 등락폭인 경우 전일종가 역산
        if abs(prev_close) < close_price * 0.5:
            prev_close = close_price - prev_close
    else:
        prev_close = close_price

    # /basic 응답에는 openPrice가 없는 경우가 많아 /integration의 totalInfos에서 시초가 보완
    if open_price <= 0:
        try:
            integ = _fetch_naver_json(f"https://m.stock.naver.com/api/stock/{ticker}/integration")
            infos = {
                item.get("code"): item.get("value")
                for item in integ.get("totalInfos", [])
                if isinstance(item, dict)
            }
            integ_open = parse_num(infos.get("openPrice"))
            if integ_open > 0:
                open_price = integ_open
            if prev_close <= 0:
                integ_prev = parse_num(infos.get("lastClosePrice"))
                if integ_prev > 0:
                    prev_close = integ_prev
        except Exception as e:
            print(f"[WARN] {ticker} 시초가 상세 조회 실패(종가로 대체): {e}")

    if open_price <= 0:
        open_price = close_price

    return {
        "open_price": open_price,
        "close_price": close_price,
        "prev_close": prev_close,
        "change_pct": change_pct,
    }


def determine_price_slot(now_kst: datetime) -> str:
    hhmm = now_kst.hour * 100 + now_kst.minute
    if hhmm < 1130:
        return "OPEN"
    if 1130 <= hhmm < 1500:
        return "NOON"
    return "CLOSE"


def upsert_to_supabase(rows):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[INFO] SUPABASE_URL / SUPABASE_KEY 미설정: 콘솔 출력만 수행합니다.")
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    endpoint = f"{SUPABASE_URL}/rest/v1/daily_prices"
    body = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"[OK] Supabase daily_prices Upsert 완료 (HTTP {resp.status}, {len(rows)}건)")


def main():
    now_kst = datetime.now(KST)
    slot = determine_price_slot(now_kst)
    rows = []

    for ticker, name in DEFAULT_KR_TICKERS:
        try:
            info = fetch_naver_etf_price(ticker)
            row = {
                "ticker": ticker,
                "name": name,
                "open_price": info["open_price"],
                "close_price": info["close_price"],
                "prev_close": info["prev_close"],
                "change_pct": info["change_pct"],
                "market": "KR",
                "price_slot": slot,
                "updated_at": now_kst.isoformat(),
            }
            if slot == "NOON":
                row["noon_price"] = info["close_price"]
            rows.append(row)
        except Exception as e:
            print(f"[WARN] {ticker} ({name}) 조회 실패: {e}")
        time.sleep(0.1)

    if rows:
        upsert_to_supabase(rows)


if __name__ == "__main__":
    main()
