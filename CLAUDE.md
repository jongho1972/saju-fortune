# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

사주팔자(四柱八字) 조회 웹사이트. 생년월일시를 입력하면 사주를 계산하고 Claude API로 전문적인 해석을 생성한다.

## 기술 스��

- **백엔드**: FastAPI (Python)
- **프론트엔드**: 정적 HTML/CSS/JS (static/ 디렉토리)
- **AI 해석**: Anthropic Claude API (SSE 스트리밍)
- **사주 계산**: 자체 구현 + korean-lunar-calendar (음양력 변환)
- **배포**: Render

## 개발 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 서버 실행 (http://localhost:8000)
ANTHROPIC_API_KEY=your-key uvicorn main:app --reload
```

## 아키텍처

### 핵심 모듈

- `main.py` — FastAPI 앱. `POST /api/saju` 엔드포인트에서 사주 계산 → Claude API 스트리밍 → SSE 응답. 정적 파일은 `app.mount("/")` 으로 서빙.
- `saju_calculator.py` �� 사주팔자 계산 엔진. 년주/월주/일주/��주 계산, 오행 분석, 십신, 대운/세운 산출. `calculate_saju()` 가 진입점.
- `solar_terms.py` — 1920~2050년 절기(절입일) 데이터 테이블. 월주 결정 시 절기 기준 사용.

### 사주 계산 핵심 로직

- **년주**: 입춘 기준 년도 보정. `(year-4) % 10` / `% 12`
- **월주**: 절기(solar_terms.py) 기준 월 결정 → 년상기월법으로 천간
- **일주**: 1900-01-01(경자일) 기준 일수 차이로 계산
- **시주**: 2시간 단위 지지 → 일상기시법으로 천간

### 데이터 흐름

```
프론트엔드 폼 → POST /api/saju → saju_calculator.calculate_saju()
  → Claude API 스트리밍 → SSE → 프론트엔드 렌더링 (marked.js)
```

SSE 이벤트 타입: `saju_data` (계산 결과 JSON), `text` (AI 해석 청크), `done` (완료)

## 환경변수

- `ANTHROPIC_API_KEY` — Claude API 키 (Render 대시보드에서 설정)

## 배포

Render 배포. `render.yaml` 참조. 무료 플랜은 비활성 시 콜드스타트 ~50초 소요.
