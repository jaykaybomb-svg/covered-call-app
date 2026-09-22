# -*- coding: utf-8 -*-
"""
Covered Call Asset Tracker - Daily Price Updater
(야후 파이낸스를 사용하지 않고 100% 네이버 증권/글로벌 공식 실시간 API 연동)
매일 장마감 후 또는 종목 추가 시 Supabase daily_prices 테이블을 자동 갱신하는 크롤러
"""

import os
import sys
import json
import urllib.request
from datetime import datetime

# Supabase 접속 정보 (환경 변수 또는 기본값)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wlavetbnglzrpkeyesqv.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndsYXZldGJuZ2x6cnBrZXllc3F2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1NDQ1MTMsImV4cCI6MjEwNDEyMDUxM30.1hk6OBMoqTcpUHEVxjXlIfr1SKf776sa-65xPPSy35M")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def normalize_ticker(t: str) -> str:
    """티커 오타 및 접미사 정규화 (예: 498400KOSPI -> 498400, A498400 -> 498400, 영문 O198A0 -> 숫자 0198A0)"""
    if not t:
        return ""
    clean = t.strip().upper()
    # 공백 제거
    clean = "".join(clean.split())
    # 접미사 (KOSPI, KOSDAQ, .KS, .KQ, 코스피, 코스닥) 제거
    for suffix in [".KS", ".KQ", "KOSPI", "KOSDAQ", "코스피", "코스닥"]:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)]
            break
    # 7자리이고 'A'로 시작하는 국내 HTS 코드 포맷(A498400) 처리
    if len(clean) == 7 and clean.startswith("A"):
        clean = clean[1:]
    # 영문 O로 시작하는 6자리 종목코드 숫자 0으로 변환
    if clean.startswith("O") and len(clean) == 6:
        clean = "0" + clean[1:]
    return clean

def get_target_tickers():
    """Supabase transactions 테이블에서 등록된 모든 종목 티커를 동적으로 수집"""
    tickers = set()
    raw_map = {}
    
    # 기본 감시 및 주요 커버드콜 종목들
    default_tickers = [
        "498400", "498410", "0198A0", "0219E0", "472150", "472160", "441680", "486290", "482730", "458730", "458740",
        "453850", "484980", "486300", "491620", "491630", "492060", "492070", "482720", "483280", "483290",
        "JEPQ", "JEPI", "TSLY", "CONY", "NVDY", "MSTY", "SPYI", "QQQI", "SCHD", "O"
    ]
    for dt in default_tickers:
        norm = normalize_ticker(dt)
        tickers.add(norm)
        raw_map[norm] = dt.strip().upper()

    try:
        url = f"{SUPABASE_URL}/rest/v1/transactions?select=ticker"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            for row in data:
                raw_t = row.get("ticker", "").strip().upper()
                norm = normalize_ticker(raw_t)
                if norm:
                    tickers.add(norm)
                    if norm not in raw_map or raw_t != norm:
                        raw_map[norm] = raw_t
    except Exception as e:
        print(f"[경고] Supabase 거래내역 조회 실패, 기본 목록 사용: {e}")

    return sorted(list(tickers)), raw_map

def fetch_kr_stock(ticker: str):
    """국내 주식/ETF 실시간 시세 및 공식 종목명 수집 (네이버 모바일 + 네이버 폴링 + 야후 파이낸스 3중 백업)"""
    norm = normalize_ticker(ticker)
    
    # 1차 시도: 네이버 모바일 증권 API (해외 클라우드 IP 차단 없음)
    try:
        m_url = f"https://m.stock.naver.com/api/stock/{norm}/basic"
        m_req = urllib.request.Request(m_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://m.stock.naver.com/"
        })
        with urllib.request.urlopen(m_req, timeout=8) as resp:
            d = json.loads(resp.read().decode())
            if d and d.get("closePrice"):
                close_price = float(str(d["closePrice"]).replace(",", ""))
                change_amt = float(str(d.get("compareToPreviousClosePrice", 0)).replace(",", ""))
                change_pct = float(str(d.get("fluctuationsRatio", 0)).replace(",", ""))
                stock_name = d.get("stockName", norm)
                prev_close = close_price - change_amt if close_price > 0 else close_price
                return {
                    "ticker": norm,
                    "name": stock_name,
                    "close_price": close_price,
                    "prev_close": prev_close,
                    "change_pct": round(change_pct, 2),
                    "market": "KR",
                    "updated_at": datetime.utcnow().isoformat()
                }
    except Exception:
        pass

    # 2차 시도: 네이버 폴링 API
    try:
        url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{norm}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://finance.naver.com/item/main.naver?code={norm}"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            res_json = json.loads(resp.read().decode())
            datas = res_json.get("datas", [])
            if datas:
                item = datas[0]
                close_price = float(str(item.get("closePriceRaw", item.get("closePrice", 0))).replace(",", ""))
                change_amt = float(str(item.get("compareToPreviousClosePriceRaw", item.get("compareToPreviousClosePrice", 0))).replace(",", ""))
                change_pct = float(str(item.get("fluctuationsRatioRaw", item.get("fluctuationsRatio", 0))).replace(",", ""))
                stock_name = item.get("stockName", norm)
                prev_close = close_price - change_amt if close_price > 0 else close_price
                return {
                    "ticker": norm,
                    "name": stock_name,
                    "close_price": close_price,
                    "prev_close": prev_close,
                    "change_pct": round(change_pct, 2),
                    "market": "KR",
                    "updated_at": datetime.utcnow().isoformat()
                }
    except Exception:
        pass

    # 3차 시도: 야후 파이낸스 글로벌 백업 (.KS)
    try:
        y_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{norm}.KS"
        y_req = urllib.request.Request(y_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(y_req, timeout=8) as resp:
            y_data = json.loads(resp.read().decode())
            meta = y_data["chart"]["result"][0]["meta"]
            close_price = float(meta["regularMarketPrice"])
            prev_close = float(meta.get("previousClose", close_price))
            change_pct = round(((close_price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0
            stock_name = meta.get("shortName", norm)
            return {
                "ticker": norm,
                "name": stock_name,
                "close_price": close_price,
                "prev_close": prev_close,
                "change_pct": change_pct,
                "market": "KR",
                "updated_at": datetime.utcnow().isoformat()
            }
    except Exception as e:
        print(f"[{ticker}] 국내 종가 수집 전체 실패: {e}")
        return None

def fetch_us_stock(ticker: str):
    """미국 ETF/주식 실시간 시세 수집 (네이버 글로벌 증권 공식 API)"""
    t = ticker.strip().upper()
    for suffix in [".O", ".N", ".K", ""]:
        url = f"https://polling.finance.naver.com/api/realtime/worldstock/stock/{t}{suffix}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                res_json = json.loads(resp.read().decode())
                datas = res_json.get("datas", [])
                if datas:
                    item = datas[0]
                    close_price = float(str(item.get("closePriceRaw", item.get("closePrice", 0))).replace(",", ""))
                    change_pct = float(str(item.get("fluctuationsRatioRaw", item.get("fluctuationsRatio", 0))).replace(",", ""))
                    change_amt = float(str(item.get("compareToPreviousClosePriceRaw", item.get("compareToPreviousClosePrice", 0))).replace(",", ""))
                    stock_name = item.get("stockName", t)
                    prev_close = close_price - change_amt if close_price > 0 else close_price
                    
                    return {
                        "ticker": t,
                        "name": stock_name,
                        "close_price": close_price,
                        "prev_close": prev_close,
                        "change_pct": round(change_pct, 2),
                        "market": "US",
                        "updated_at": datetime.utcnow().isoformat()
                    }
        except Exception:
            continue
    return None

def upsert_to_supabase(records):
    """수집된 종가 정보를 Supabase daily_prices 테이블에 Upsert"""
    if not records:
        print("저장할 종가 데이터가 없습니다.")
        return

    url = f"{SUPABASE_URL}/rest/v1/daily_prices"
    req = urllib.request.Request(url, data=json.dumps(records).encode("utf-8"), headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"✅ Supabase daily_prices {len(records)}건 업데이트 완료 (응답코드: {resp.status})")
    except Exception as e:
        print(f"❌ Supabase daily_prices 저장 중 에러 발생: {e}")

def main():
    print(f"=== 커버드콜 네이버 금융 종가 자동 수집 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    tickers, raw_map = get_target_tickers()
    print(f"총 수집 대상 종목: {len(tickers)}개 -> {tickers}")

    results = []
    for ticker in tickers:
        is_us = ticker.isalpha() and len(ticker) <= 5
        if is_us:
            data = fetch_us_stock(ticker)
        else:
            data = fetch_kr_stock(ticker)

        if data:
            results.append(data)
            print(f"  ✓ [{data['ticker']}] {data['name']} : {data['close_price']:,} (전일비 {data['change_pct']}%)")
            
            # 혹시 사용자가 'O198A0' 처럼 영문 O로 등록한 거래내역이 있으면 그 키로도 함께 보존
            orig_t = raw_map.get(ticker)
            if orig_t and orig_t != data["ticker"]:
                alias = dict(data)
                alias["ticker"] = orig_t
                results.append(alias)
                print(f"    -> 별칭 티커 매핑 [{orig_t}] 동기화 추가")
        else:
            print(f"  ✗ [{ticker}] 시세 수집 실패")

    if results:
        upsert_to_supabase(results)
    print("=== 모든 종가 갱신 작업 완료 ===")

if __name__ == "__main__":
    main()
