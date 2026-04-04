"""
사주팔자 조회 웹사이트 - FastAPI 백엔드

POST /api/saju : 사주 계산 + Claude AI 해석 (SSE 스트리밍)
GET  /          : 정적 파일 (프론트엔드)
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from anthropic import AsyncAnthropic

from saju_calculator import calculate_saju

load_dotenv()

app = FastAPI(title="사주팔자 조회")

client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """당신은 30년 경력의 한국 사주명리학(四柱命理學) 전문가입니다.
사주팔자를 분석하여 전문적이면서도 이해하기 쉬운 한국어로 해석해주세요.

해석 원칙:
1. 긍정적이고 건설적인 방향으로 해석합니다
2. 전문 용어(편재, 정관, 식신, 겁재 등)는 사용하지 않습니다. 누구나 이해할 수 있는 쉬운 일상 언어로 풀어서 설명합니다
3. "불의 기운이 강해요" 같은 비유적이고 친근한 표현을 사용합니다
4. 구체적이고 실용적인 조언을 포함합니다
5. 미신적이거나 불안감을 조성하는 표현은 피합니다
6. 각 섹션은 충분히 상세하게 작성합니다 (각 섹션 최소 3-4문장)
7. 친구에게 이야기하듯 편안한 말투로 작성합니다 (존댓말 사용)

응답 형식 (반드시 마크다운으로):

## 사주 총론
(전반적인 사주의 특징과 기운 요약. 일간의 특성, 사주 전체 구성의 조화 분석)

## 타고난 성격과 기질
(일간 및 사주 구성 기반 성격 분석. 강점과 주의할 점 포함)

## 재물운과 직업운
(재성, 관성, 식상 등 기반 분석. 적합한 직업군과 재물 관리 조언)

## 연애운과 결혼운
(일지, 배우자궁 등 기반 분석. 이상적인 파트너상과 인연 시기)

## 건강운
(오행 불균형 기반 건강 유의사항. 보완 방법 제시)

## 궁합이 좋은 띠와 사주
(이 사주와 궁합이 좋은 띠 3가지와 그 이유. 궁합이 좋은 일간/오행 조합도 함께 설명)

## 올해의 월별 운세
(올해 남은 기간에 대해 월별로 운세를 분석. 각 월의 핵심 키워드와 조언을 간결하게 작성.
형식 예시:
- **4월**: 키워드 - 설명
- **5월**: 키워드 - 설명
...이런 식으로 12월까지)

## 행운의 숫자·색상·방위
(이 사주에 맞는 행운의 숫자 3개, 행운의 색상 2가지, 행운의 방위를 오행 분석에 기반하여 제시. 각각 왜 그런지 간단히 설명)

## 대운 흐름과 종합 조언
(현재 대운 분석 및 향후 흐름. 인생 전반에 대한 조언)"""


def build_user_prompt(saju: dict) -> str:
    """사주 계산 결과를 Claude API 프롬프트로 변환한다."""
    yp = saju["year_pillar"]
    mp = saju["month_pillar"]
    dp = saju["day_pillar"]
    hp = saju["hour_pillar"]

    lines = [
        f"다음 사주팔자를 상세히 분석해주세요.",
        "",
        f"[기본 정보]",
        f"- 이름: {saju['name']}",
        f"- 성별: {saju['gender']}",
        f"- 생년월일: {saju['birth_date']}",
    ]

    if saju["birth_hour"] is not None:
        lines.append(f"- 태어난 시각: {saju['birth_hour']}시")
    else:
        lines.append(f"- 태어난 시각: 미상")

    if saju["birth_place"]:
        lines.append(f"- 출생지: {saju['birth_place']}")

    lines.append(f"- 띠: {saju['ddi']}띠")
    lines.append("")

    # 사주팔자 표
    if hp:
        lines.extend([
            "[사주팔자]",
            f"        시주      일주      월주      년주",
            f"천간:   {hp['cheongan_hanja']}({hp['cheongan']})   {dp['cheongan_hanja']}({dp['cheongan']})   {mp['cheongan_hanja']}({mp['cheongan']})   {yp['cheongan_hanja']}({yp['cheongan']})",
            f"지지:   {hp['jiji_hanja']}({hp['jiji']})   {dp['jiji_hanja']}({dp['jiji']})   {mp['jiji_hanja']}({mp['jiji']})   {yp['jiji_hanja']}({yp['jiji']})",
        ])
    else:
        lines.extend([
            "[사주팔자] (시주 미상)",
            f"        일주      월주      년주",
            f"천간:   {dp['cheongan_hanja']}({dp['cheongan']})   {mp['cheongan_hanja']}({mp['cheongan']})   {yp['cheongan_hanja']}({yp['cheongan']})",
            f"지지:   {dp['jiji_hanja']}({dp['jiji']})   {mp['jiji_hanja']}({mp['jiji']})   {yp['jiji_hanja']}({yp['jiji']})",
        ])

    lines.append("")

    # 오행 분석
    oh = saju["ohaeng"]
    lines.extend([
        "[오행 분석]",
        f"- 목(木): {oh['목']}개",
        f"- 화(火): {oh['화']}개",
        f"- 토(土): {oh['토']}개",
        f"- 금(金): {oh['금']}개",
        f"- 수(水): {oh['수']}개",
        "",
    ])

    # 일간
    il = saju["ilgan"]
    lines.extend([
        f"[일간(나를 나타내는 글자)]",
        f"- {il['hanja']}({il['name']}) - {il['ohaeng']}({il['eumyang']})",
        "",
    ])

    # 십신
    ss = saju["sipsin"]
    lines.extend([
        "[십신 관계]",
        f"- 년간: {ss['year_cheongan']}, 년지: {ss['year_jiji']}",
        f"- 월간: {ss['month_cheongan']}, 월지: {ss['month_jiji']}",
    ])
    if "hour_cheongan" in ss:
        lines.append(f"- 시간: {ss['hour_cheongan']}, 시지: {ss['hour_jiji']}")
    lines.append("")

    # 대운
    dw = saju["daewoon"]
    lines.extend([
        f"[대운] ({dw['direction']})",
        f"- 대운 시작 나이: {dw['start_age']}세",
    ])
    for d in dw["list"]:
        lines.append(f"  {d['age']}세({d['year_range']}): {d['cheongan_hanja']}{d['jiji_hanja']}({d['cheongan']}{d['jiji']})")

    if saju["current_daewoon"]:
        cd = saju["current_daewoon"]
        lines.append(f"- 현재 대운: {cd['cheongan_hanja']}{cd['jiji_hanja']}({cd['cheongan']}{cd['jiji']}) ({cd['year_range']})")

    lines.append("")

    # 세운
    sw = saju["sewoon"]
    lines.extend([
        f"[올해 세운 ({sw['year']}년)]",
        f"- {sw['ganji']}",
        "",
        "위 정보를 바탕으로 각 섹션별로 상세하고 전문적인 분석을 해주세요.",
    ])

    return "\n".join(lines)


@app.post("/api/saju")
async def analyze_saju(request: Request):
    """사주 계산 + AI 해석 (SSE 스트리밍)"""
    data = await request.json()

    name = data.get("name", "")
    birth_year = int(data["year"])
    birth_month = int(data["month"])
    birth_day = int(data["day"])
    birth_hour = data.get("hour")
    if birth_hour is not None and birth_hour != "":
        birth_hour = int(birth_hour)
    else:
        birth_hour = None
    gender = data.get("gender", "male")
    calendar_type = data.get("calendar_type", "solar")
    is_intercalation = data.get("is_intercalation", False)
    birth_place = data.get("birth_place", "")

    current_year = datetime.now().year

    # 사주 계산
    saju_result = calculate_saju(
        name=name,
        year=birth_year,
        month=birth_month,
        day=birth_day,
        hour=birth_hour,
        gender=gender,
        calendar_type=calendar_type,
        is_intercalation=is_intercalation,
        birth_place=birth_place,
        current_year=current_year,
    )

    user_prompt = build_user_prompt(saju_result)

    async def event_stream():
        # 먼저 사주 계산 결과를 전송
        yield f"data: {json.dumps({'type': 'saju_data', 'data': saju_result}, ensure_ascii=False)}\n\n"

        # Claude API 스트리밍 해석
        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 정적 파일 서빙 (프론트엔드)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
