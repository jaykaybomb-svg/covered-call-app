-- =========================================================
-- 커버드콜 자산 관리 시스템 Supabase DB 스키마 백업
-- =========================================================

-- 1. 일별 종가 시세 테이블 (daily_prices)
CREATE TABLE IF NOT EXISTS daily_prices (
    ticker TEXT PRIMARY KEY,
    name TEXT,
    close_price NUMERIC,
    prev_close NUMERIC,
    change_pct NUMERIC,
    market TEXT DEFAULT 'KR',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 매매 거래 원장 테이블 (transactions)
CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT PRIMARY KEY,
    trade_type TEXT NOT NULL, -- 'BUY' 또는 'SELL'
    ticker TEXT NOT NULL,
    name TEXT,
    shares NUMERIC NOT NULL,
    price NUMERIC NOT NULL,
    trade_date DATE NOT NULL
);

-- 3. 분배금 수령 및 라이프사이클 원장 테이블 (dividends)
CREATE TABLE IF NOT EXISTS dividends (
    id BIGINT PRIMARY KEY,
    ticker TEXT NOT NULL,
    total_received NUMERIC NOT NULL,
    status TEXT DEFAULT 'CASH', -- 'CASH'(미사용 예수금), 'REINVEST'(재매수), 'WITHDRAW'(인출)
    pay_date DATE NOT NULL,
    shares_held NUMERIC DEFAULT 0,
    dividend_per_share NUMERIC DEFAULT 0
);
