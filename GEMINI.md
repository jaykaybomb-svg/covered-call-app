# 🌟 커버드콜 자산 및 분배금 자동 관리 시스템 (Covered Call Tracker)
## Antigravity IDE 바이브 코딩 전용 시스템 규칙 (System Rules)

이 파일은 Antigravity IDE가 프로젝트를 열 때 자동으로 읽어들이는 전용 AI 에이전트 지침서입니다.

---

### 1. 사용자 특성 및 커뮤니케이션 원칙 (최우선 준수)
1. **사용자 페르소나**: 비전공자 / 코딩 초보자이며, 직관적이고 친절한 한국어 안내를 원합니다.
2. **코드 생략 절대 금지 (STRICT RULE)**:
   - `// ... 기존 코드 유지`, `// ... 생략` 같은 축약을 **절대로 하지 마십시오.**
   - 언제나 사용자가 복사해서 바로 덮어쓸 수 있는 **100% 완전한 전체 코드**를 제공해야 합니다.
3. **한국어 질문 및 확인**:
   - 명령어 실행이나 중요 확인 시 반드시 **한국어로 친절하게 설명**하고 물어보십시오.
4. **바이브 코딩 모드 (Vibe Coding)**:
   - 사용자가 "이 기능 추가해줘", "색상 바꿔줘" 등 자연어로 요청하면, AI는 즉시 의도를 파악하여 관련 파일(`index.html`, `updater.py` 등)을 정확히 수정하고 결과를 안내합니다.

---

### 2. 프로젝트 핵심 아키텍처 및 철학
1. **금융 핵심 철학**:
   - **배당락 착시 방지 실질 총수익 (Total Return)**:
     `총수익 = 주식 평가손익 + 누적 수령 분배금 + 기실현손익(매도손익)`
   - **분배금 3단계 라이프사이클**:
     ① `CASH`: 미사용 예수금 (순자산에 가산)
     ② `REINVEST`: 주식 재매수 사용 (복리 효과)
     ③ `WITHDRAW`: 생활비 등 외부 계좌 인출
   - **원금 대비 배당수익률 (Yield On Cost, YOC)** 및 복리 FIRE 시뮬레이터 제공.
2. **클라우드 데이터베이스 (Supabase)**:
   - URL: `https://wlavetbnglzrpkeyesqv.supabase.co`
   - 테이블:
     - `daily_prices`: 일별 종가 시세 (`ticker`, `name`, `close_price`, `prev_close`, `change_pct`, `market`, `updated_at`)
     - `transactions`: 매매 원장 (`id`, `trade_type`, `ticker`, `name`, `shares`, `price`, `trade_date`)
     - `dividends`: 분배금 원장 (`id`, `ticker`, `total_received`, `status`, `pay_date`, `shares_held`, `dividend_per_share`)
3. **자동화 파이프라인**:
   - `updater.py`: 등록된 모든 종목의 종가를 네이버 금융에서 긁어와 Supabase에 Upsert.
   - `.github/workflows/daily_update.yml`: 매일 평일 15:45 KST 자동 실행.
4. **프론트엔드 UI**:
   - `index.html`: Vue 3 + Tailwind CSS + FontAwesome 기반 PWA (모바일 친화형 다크 테마).
   - 테마 컬러: `bg-slate-950`, 포인트: `emerald-400`(수익/성장), `amber-400`(배당), `cyan-400`(예수금).

---

### 3. 주요 파일 구조
- `index.html`: 프론트엔드 PWA 앱 (대시보드, 보유종목, 배당캘린더, 매매/분배금 원장, 복리계산기)
- `updater.py`: 백엔드 종가 자동 크롤러
- `.github/workflows/daily_update.yml`: GitHub Actions 자동화 워크플로우
- `requirements.txt`: 파이썬 의존성 설정
- `GEMINI.md`: AI 바이브 코딩 설정 및 프로젝트 컨텍스트
