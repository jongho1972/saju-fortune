# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

사주팔자(四柱八字) 조회 웹사이트. 생년월일시를 입력하면 사주를 계산하고 Claude API로 쉬운 언어의 해석을 생성한다.

## 기술 스택

- **백엔드**: FastAPI (Python)
- **프론트엔드**: 정적 HTML/CSS/JS (static/ 디렉토리)
- **AI 해석**: Anthropic Claude API `claude-sonnet-5-5` (SSE 스트리밍, 출력되는 대로 실시간 표시). `thinking: between_tools`(생각 끔 — 생각 토큰이 max_tokens를 잠식해 해석이 잘리던 문제 방지), effort `high`, 서버 측 거절 폴백(`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). 설정은 `main.py`의 `STREAM_OPTIONS` 한 곳
- **사주 계산**: 자체 구현 + korean-lunar-calendar (음양력 변환)
- **배포**: j-hawk VPS (`https://fortune.jhawk.kr` · Docker Compose + Caddy)

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
- **일주**: 1900-01-01(갑술일) 기준 일수 차이로 계산
- **시주**: 2시간 단위 지지 → 일상기시법으로 천간

### 데이터 흐름

```
프론트엔드 폼 → POST /api/saju → saju_calculator.calculate_saju()
  → Claude API 스트리밍 → SSE → 프론트엔드 (출력되는 대로 실시간 렌더링)
```

SSE 이벤트 타입: `saju_data` (계산 결과 JSON), `text` (AI 해석 청크), `notice` (max_tokens로 잘림·거절 안내), `error` (API 오류, 사용자용 문구 — 원문은 서버 로그), `done` (완료). 공통 생성기는 `stream_claude()`이며 매 호출 토큰·캐시 사용량을 uvicorn 로그에 `claude stop=... cache_read=...`로 남긴다.

프론트엔드는 `saju_data` 수신 즉시 사주표를 표시하고, `text` 청크가 들어오는 대로 마크다운을 실시간 렌더링한다(200ms throttle). 해석 중에는 스트리밍 배너(`#streaming-banner`)와 깜빡이는 커서(`#interpretation.streaming`)를 표시하고, 완료 시 배너를 숨기며 공유·PDF 저장 버튼을 활성화한다.

### 보호 장치 (2026-11-11)

- **입력 검증**: 연·월·일·시·분 범위 검사, 존재하지 않는 날짜(ValueError)는 400 + 한국어 안내(`{"error": ...}`). 프론트는 `readErrorMessage()`로 문구를 그대로 표시.
- **호출 제한**: IP당 1시간 사주 10회·추가 질문 30회(`RATE_LIMITS`, 단일 프로세스 메모리). 초과 시 429.
- **추가 질문 상한**: 질문 500자, 이전 해석 3만 자, 대화 이력 최근 20개·2만 자(`_clean_history`).
- **프롬프트 캐싱**: 메인 시스템 프롬프트에 `cache_control`, 추가 질문은 고정 context 블록 + 자동 캐싱.

### 결과 공유 / PDF 저장 (손금풀이와 동일 방식)

- **공유**: `navigator.share`(모바일 네이티브) → 미지원 시 `navigator.clipboard` 복사 폴백. 결과를 서버에 저장하지 않으므로 링크가 아닌 내용(사주표+오행+AI 해석)을 텍스트로 직렬화해 공유한다.
- **PDF 저장**: `window.print()` + `@media print`. 인쇄 시 표지(`.print-cover`)+사주표+해석만 출력하고 입력폼·배너·액션·추가질문·헤더·푸터는 숨긴다. 오행 색상은 `print-color-adjust: exact`로 유지.

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

홈페이지(`jhawk.kr`)와 같은 **다크 고정 톤**(2026-11-11 전환). 배경 `#0b0c0e`, 카드 `#15171a`, 글자 `#f2f3f5`, 링크 `#3d9bff`·버튼 `#0a6fe0`, 노란 왼쪽 보더 카드 헤더 유지. 색은 `style.css` `:root` 토큰으로만 지정하고, `@media print`에서 같은 토큰을 밝은 값으로 재정의해 PDF는 흰 종이로 출력한다.

## 환경변수

- 의존성은 `requirements.txt`에 버전 고정(2026-11-11). 올릴 때는 깨끗한 venv에서 확인 후 변경.
- `ANTHROPIC_API_KEY` — Claude API 키 (로컬: `.env` 파일, 배포: VPS `/opt/j-hawk/deploy/.env.fortune`)

## 배포

- **플랫폼**: j-hawk VPS (Hetzner CAX11 ARM · Docker Compose + Caddy)
- **저장소**: GitHub `jongho1972/saju-fortune`
- **서비스 URL**: https://fortune.jhawk.kr
- GitHub `main` 푸시 시 `deploy.yml`이 VPS SSH → `git reset --hard` → `docker compose build/up fortune` → 헬스체크
- 공통 인프라·롤백·트러블슈팅: 워크스페이스 루트 `deploy/README.md` 또는 `vps-deploy` 스킬
