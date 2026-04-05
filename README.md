# Claude가 알려주는 사주팔자

사주명리학 기반 AI 운세 분석 서비스. 생년월일시를 입력하면 사주팔자를 계산하고, Claude AI가 초등학생도 이해할 수 있는 쉬운 말로 해석해줍니다.

**배포 URL**: https://saju-fortune.onrender.com

## 주요 기능

- 사주팔자 자동 계산 (년주/월주/일주/시주)
- 오행 분포 시각화
- AI 사주 해석 (쉬운 언어, 자연 비유 활용)
- 향후 12개월 양력 기준 월별 운세
- 추가 질문 기능 (사주 맥락 유지한 대화)
- 양력/음력 입력 지원

## 기술 스택

- **백엔드**: Python, FastAPI
- **프론트엔드**: HTML, CSS, JavaScript
- **AI**: Anthropic Claude API (SSE 스트리밍)
- **사주 계산**: 자체 구현 + korean-lunar-calendar
- **배포**: Render

## 로컬 실행

```bash
pip install -r requirements.txt
# .env 파일에 ANTHROPIC_API_KEY 설정
uvicorn main:app --reload
```

http://localhost:8000 에서 확인

## 프로젝트 구조

```
fortune/
├── main.py              # FastAPI 앱 + Claude API 연동
├── saju_calculator.py   # 사주팔자 계산 엔진
├── solar_terms.py       # 절기 데이터 (1920~2050년)
├── requirements.txt
├── render.yaml          # Render 배포 설정
└── static/
    ├── index.html
    ├── style.css
    └── script.js
```
