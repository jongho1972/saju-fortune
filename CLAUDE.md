# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

사주팔자(四柱八字) 조회 웹사이트. 생년월일시를 입력하면 사주를 계산하고 Claude API로 쉬운 언어의 해석을 생성한다.

## 기술 스택

- **백엔드**: FastAPI (Python)
- **프론트엔드**: 정적 HTML/CSS/JS (static/ 디렉토리)
- **AI 해석**: Anthropic Claude API (SSE 스트리밍, 완료 후 한 번에 표시)
- **사주 계산**: 자체 구현 + korean-lunar-calendar (음양력 변환)
- **배포**: Render (`https://saju-fortune.onrender.com`)

## 개발 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 서버 실행 (http://localhost:8000)
# .env 파일에 ANTHROPIC_API_KEY 설정 필요
uvicorn main:app --reload
```

## 아키텍처

### 핵심 모듈

- `main.py` — FastAPI 앱. `POST /api/saju` 엔드포인트에서 사주 계산 → Claude API 스트리밍 → SSE 응답. 정적 파일은 `app.mount("/")` 으로 서빙. AI 해석 프롬프트(`SYSTEM_PROMPT`)가 여기에 정의됨.
- `saju_calculator.py` — 사주팔자 계산 엔진. 년주/월주/일주/시주 계산, 오행 분석, 십신, 대운/세운 산출. `calculate_saju()` 가 진입점.
- `solar_terms.py` — 1920~2050년 절기(절입일) 데이터 테이블. 월주 결정 시 절기 기준 사용.

### 사주 계산 핵심 로직

- **년주**: 입춘 기준 년도 보정. `(year-4) % 10` / `% 12`
- **월주**: 절기(solar_terms.py) 기준 월 결정 → 년상기월법으로 천간
- **일주**: 1900-01-01(경자일) 기준 일수 차이로 계산
- **시주**: 2시간 단위 지지 → 일상기시법으로 천간

### 데이터 흐름

```
프론트엔드 폼 → POST /api/saju → saju_calculator.calculate_saju()
  → Claude API 스트리밍 → SSE → 프론트엔드 (완료 후 한 번에 렌더링)
```

SSE 이벤트 타입: `saju_data` (계산 결과 JSON), `text` (AI 해석 청크), `done` (완료)

프론트엔드는 스트리밍 중에는 로딩 화면만 표시하고, 완료 시 사주표+AI 해석을 한 번에 표시한다.

### AI 해석 항목 (main.py SYSTEM_PROMPT)

1. 사주 총론
2. 타고난 성격과 기질
3. 재물운과 직업운
4. 연애운과 결혼운
5. 건강운
6. 향후 12개월 월별 운세 (양력 기준)
7. 대운 흐름과 종합 조언

해석은 전문 용어 없이 쉬운 일상 언어로 작성된다.

### 개인화 근거 데이터

`build_user_prompt()`가 Claude에 전달하는 핵심 근거:

- **십신**: 년간/년지/월간/월지/**일지(배우자궁)**/시간/시지 — 일간 기준 십신
- **대운**: 10개 기둥 각각에 천간십신·지지십신 표기 + 현재 대운 강조
- **세운**: 올해 간지 + 천간/지지 십신
- **월운**: `calc_wolwoon_next_12()`가 오늘부터 12개월 각 월의 월운 간지(절기 기준, 매월 15일 기준)를 산출하고 일간 대비 십신 계산

이 데이터 덕분에 SYSTEM_PROMPT가 "이 사람의 일간과 해당 운의 십신 관계"를 명시적 근거로 사용할 수 있어 일반론이 아닌 개인화 해석이 생성된다.

### 디자인

복권번호생성기(`lottery-number-generator.onrender.com`)와 동일한 톤앤매너. 밝은 배경(`#f5f5f7`), 흰색 카드, 파란 액센트 버튼(`#007aff`), 노란 왼쪽 보더 카드 헤더.

## 환경변수

- `ANTHROPIC_API_KEY` — Claude API 키 (로컬: `.env` 파일, 배포: Render 대시보드)

## 배포

Render 배포. `render.yaml` 참조. GitHub `jongho1972/saju-fortune` 저장소와 연동되어 push 시 자동 배포.
