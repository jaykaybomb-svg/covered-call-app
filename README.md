# 커버드콜 자산 및 분배금 자동 관리 시스템 (Covered Call Asset Tracker)

개인용 커버드콜 ETF 자산 평가 및 분배금 캐시플로우 통합 관리 PWA 시스템입니다.

## 📁 프로젝트 파일 구조

- `index.html`: 프론트엔드 모바일 PWA 웹앱 (Supabase 연동, 포트폴리오 평가, 배당 캘린더, 복리 시뮬레이터)
- `updater.py`: 등록된 모든 종목의 종가를 네이버 금융에서 긁어와 Supabase `daily_prices`에 자동 Upsert하는 파이썬 크롤러
- `.github/workflows/daily_update.yml`: 매일 평일 장마감 시 자동으로 `updater.py`를 실행하는 GitHub Actions 워크플로우

## 🚀 Antigravity IDE에서 이어서 작업하는 방법

1. Antigravity IDE 상단 메뉴에서 **File(파일) > Open Folder(폴더 열기)**를 클릭합니다.
2. `C:\Users\김희진\.gemini\antigravity\scratch\CoveredCallTracker` 폴더를 선택합니다.
3. 이제 IDE 사이드바의 AI 에이전트와 대화하며 실시간으로 코드를 수정하고, 터미널에서 `python updater.py`를 실행할 수 있습니다.
