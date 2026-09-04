import os
import yfinance as yf
import FinanceDataReader as fdr
from supabase import create_client, Client
from datetime import datetime

# Supabase 클라우드 DB 연결
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase 환경 변수가 설정되지 않았습니다.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 기본 모니터링 종목 리스트 (필요 시 티커를 자유롭게 추가할 수 있습니다)
DEFAULT_WATCHLIST = [
    {"ticker": "441680", "name": "TIGER 미국나스닥100커버드콜(합성)", "market": "KR"},
    {"ticker": "486290", "name": "KODEX 200커버드콜액티브", "market": "KR"},
    {"ticker": "JEPQ", "name": "JPMorgan Nasdaq Equity Premium Income", "market": "US"},
    {"ticker": "JEPI", "name": "JPMorgan Equity Premium Income", "market": "US"}
]

def get_target_tickers():
    """사용자가 DB에 기록한 보유 종목과 기본 종목을 합쳐서 가져옵니다."""
    ticker_dict = {item["ticker"]: item for item in DEFAULT_WATCHLIST}
    
    try:
        # 사용자가 매수한 종목 내역에서 티커 목록 조회
        response = supabase.table("transactions").select("ticker, name").execute()
        for row in response.data:
            t = row["ticker"]
            if t not in ticker_dict:
                # 숫자 6자리인 경우 한국 주식으로 판별
                market = "KR" if t.isdigit() and len(t) == 6 else "US"
                ticker_dict[t] = {"ticker": t, "name": row.get("name", t), "market": market}
    except Exception as e:
        print(f"보유 종목 조회 중 참고 알림: {e}")

    return list(ticker_dict.values())

def fetch_and_update():
    targets = get_target_tickers()
    print(f"총 {len(targets)}개 종목 시세를 수집합니다.")

    for item in targets:
        ticker = item["ticker"]
        name = item["name"]
        market = item["market"]
        
        try:
            close_price = 0.0
            prev_close = 0.0
            change_pct = 0.0

            if market == "KR":
                # 한국 종목: FinanceDataReader를 통해 최근 5거래일 데이터 호출
                df = fdr.DataReader(ticker).tail(5)
                if not df.empty and len(df) >= 2:
                    close_price = float(df["Close"].iloc[-1])
                    prev_close = float(df["Close"].iloc[-2])
                    change_pct = round(((close_price - prev_close) / prev_close) * 100, 2)
                elif len(df) == 1:
                    close_price = float(df["Close"].iloc[-1])
                    prev_close = close_price
                    change_pct = 0.0
            else:
                # 미국 종목: yfinance를 통해 최근 5거래일 데이터 호출
                stock = yf.Ticker(ticker)
                hist = stock.history(period="5d")
                if not hist.empty and len(hist) >= 2:
                    close_price = round(float(hist["Close"].iloc[-1]), 2)
                    prev_close = round(float(hist["Close"].iloc[-2]), 2)
                    change_pct = round(((close_price - prev_close) / prev_close) * 100, 2)
                elif len(hist) == 1:
                    close_price = round(float(hist["Close"].iloc[-1]), 2)
                    prev_close = close_price
                    change_pct = 0.0

            if close_price > 0:
                payload = {
                    "ticker": ticker,
                    "name": name,
                    "close_price": close_price,
                    "prev_close": prev_close,
                    "change_pct": change_pct,
                    "market": market,
                    "updated_at": datetime.utcnow().isoformat()
                }
                # Supabase의 daily_prices 테이블에 upsert (기존 데이터 덮어쓰기)
                supabase.table("daily_prices").upsert(payload, on_conflict="ticker").execute()
                print(f"✅ [{ticker}] {name}: 종가 {close_price:,} (변동: {change_pct}%) 업데이트 완료")
            else:
                print(f"⚠️ [{ticker}] 종가 데이터를 가져오지 못했습니다.")

        except Exception as e:
            print(f"❌ [{ticker}] 수집 실패 오류: {e}")

if __name__ == "__main__":
    fetch_and_update()
