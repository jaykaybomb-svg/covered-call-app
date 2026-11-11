-- ============================================================================
-- Covered Call Tracker v2.0 (국장 커버드콜 자금 A·B 분리 & 대출/재매수 통합 장부)
-- Supabase DB 마이그레이션 SQL (기존 테이블 데이터 100% 보존)
-- ============================================================================

-- 1. 일별 시세 테이블(daily_prices)에 시초가(open_price), 12시 가격(noon_price), 조회 시점(price_slot) 추가
ALTER TABLE daily_prices ADD COLUMN IF NOT EXISTS open_price numeric DEFAULT 0;
ALTER TABLE daily_prices ADD COLUMN IF NOT EXISTS noon_price numeric DEFAULT 0;
ALTER TABLE daily_prices ADD COLUMN IF NOT EXISTS price_slot text DEFAULT 'CLOSE';

-- 2. 매매 원장(transactions)에 자금 구분(fund_id), 수수료(fee), 혼합매수 원금(principal_mixed_amount) 추가
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS fund_id text DEFAULT 'A';
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS fee numeric DEFAULT 0;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS principal_mixed_amount numeric DEFAULT 0;

-- 3. 분배금 원장(dividends)에 자금 구분(fund_id), 단계(stage), 세전금액(gross_amount), 세금(tax_amount), 확정기준일(record_date) 추가
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS fund_id text DEFAULT 'A';
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS stage text DEFAULT 'RECEIVED';
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS gross_amount numeric DEFAULT 0;
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS tax_amount numeric DEFAULT 0;
ALTER TABLE dividends ADD COLUMN IF NOT EXISTS record_date date;

-- 4. 현금·이체 장부(cash_ledger) 신규 테이블 생성
CREATE TABLE IF NOT EXISTS cash_ledger (
  id bigint PRIMARY KEY,
  fund_id text NOT NULL DEFAULT 'A',
  flow_type text NOT NULL, -- DEPOSIT, WITHDRAW_DIV, WITHDRAW_PRIN, TRANSFER_IN, TRANSFER_OUT, INTEREST_PAY, LOAN_IN, LOAN_REPAY
  bucket text NOT NULL DEFAULT 'PRINCIPAL', -- PRINCIPAL(원금 예수금) 또는 DIVIDEND(미사용 분배금 바구니)
  amount numeric NOT NULL DEFAULT 0,
  flow_date date NOT NULL,
  memo text,
  created_at timestamptz DEFAULT now()
);

-- 5. 대출 원장(loans) 신규 테이블 생성
CREATE TABLE IF NOT EXISTS loans (
  id bigint PRIMARY KEY,
  fund_id text NOT NULL DEFAULT 'A',
  loan_name text NOT NULL,
  principal_balance numeric NOT NULL DEFAULT 0,
  interest_rate numeric NOT NULL DEFAULT 5.0,
  pay_day integer NOT NULL DEFAULT 25,
  maturity_date date,
  created_at timestamptz DEFAULT now()
);
