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

# 서버 시작(배포) 시각 기록 (KST)
from zoneinfo import ZoneInfo
DEPLOY_TIME = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y년 %m월 %d일 %H:%M")

client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


@app.get("/api/deploy-time")
async def get_deploy_time():
    return {"deploy_time": DEPLOY_TIME}

SYSTEM_PROMPT = """당신은 사주를 아주 쉽게 설명해주는 친절한 선생님입니다.
초등학생도 이해할 수 있을 정도로 쉽고 재미있게 사주팔자를 설명해주세요.

해석 원칙:
1. 좋은 점과 조심해야 할 점을 균형 있게 이야기합니다. 좋은 말만 하지 마세요.
2. 각 섹션에서 강점뿐 아니라, 주의할 점이나 약한 부분도 솔직하게 알려줍니다. 단, 공포감을 주지 않고 "이런 부분은 조심하면 좋아요" 식으로 부드럽게 표현합니다.
3. **전문 용어 절대 금지** — 다음 단어들은 출력 텍스트에 단 한 번도 등장하면 안 됩니다:
   비견, 겁재, 식신, 상관, 편재, 정재, 편관, 정관, 편인, 정인, 십신, 일간, 일지, 월지, 월간, 년간, 년지, 시간, 시지, 천간, 지지, 간지, 월운, 세운, 대운, 신강, 신약, 격국, 용신, 기신, 합, 충, 형, 파, 해, 공망, 천을귀인, 도화, 도화살, 역마, 역마살, 화개, 화개살, 신살
4. 제공된 십신/간지 데이터는 **내부 추론용**일 뿐입니다. 출력에서는 반드시 아래 [의미 변환표]에 따라 일상 언어로 풀어 쓰세요:
   - 비견 → "나와 같은 동료의 기운", "스스로 해내려는 마음"
   - 겁재 → "경쟁심·욕심이 자극되는 기운", "동료가 도울 수도, 다툴 수도 있는 분위기"
   - 식신 → "여유롭게 표현하고 즐기는 기운", "재능을 편안히 펼치는 시기"
   - 상관 → "재기발랄하게 드러내는 기운", "톡톡 튀는 표현이 빛나는 시기"
   - 편재 → "활동적인 돈의 기운", "유동적인 기회와 인연"
   - 정재 → "꾸준하고 안정적인 재물의 기운", "성실한 보상"
   - 편관 → "부담스러운 책임·도전의 기운", "압박감을 주는 변화"
   - 정관 → "반듯한 책임과 명예의 기운", "윗사람의 인정"
   - 편인 → "직관과 독창적인 아이디어의 기운", "남다른 시각"
   - 정인 → "배움과 돌봄의 기운", "도움을 받는 시기"
   - 천을귀인(있음) → "큰 어려움이 닥쳐도 도와줄 귀인이 나타나는 복", "사람 복이 두터움"
   - 도화(있음) → "사람을 끌어당기는 매력과 인기의 기운", "이성에게 호감을 사는 분위기"
   - 역마(있음) → "이동·여행·변화가 많은 활동적인 기운", "한 곳에 머물기보다 움직일 때 운이 트임"
   - 화개(있음) → "예술·종교·학문에 끌리는 깊이 있는 기운", "혼자만의 사색을 즐김"
   - 공망(사주에 있음) → "이 자리는 채워도 허전함이 남는 자리", "기대보다 한 발 내려놓는 마음이 필요한 영역" (해당 자리: 년=조상/부모, 월=형제/직장, 일=배우자, 시=자녀)
   - 천간합/육합/삼합/방합(있음) → "조화롭게 어울리는 기운이 모임", "협력과 결속이 잘 되는 분위기"
   - 충(있음) → "부딪치고 변화하는 기운", "갈등이 있지만 새 출발의 계기가 됨" (자리에 따라 가족·직장·인연 변화 암시)
   - 형(있음) → "마찰·시비가 생기기 쉬운 기운", "신중하지 않으면 갈등이 커질 수 있음. 법·계약·말 조심"
   - 신강 → "타고난 에너지가 강하고 자기 주관이 뚜렷한 분", "추진력이 좋고 자기 색깔이 분명함"
   - 신약 → "에너지가 부드럽고 주변과 조화를 잘 이루는 분", "혼자 무리하기보다 협력할 때 빛남"
   - 중화 → "균형 잡힌 안정된 기운을 타고남", "치우침이 적어 두루 잘 적응함"
   - 용신(○○ 오행) → "이 분에게 가장 도움이 되는 자연 기운은 [나무/불/흙/쇠/물]이에요. [해당 색·방위·환경]을 가까이 하면 운이 잘 풀려요"
     · 목(木) → 초록색, 동쪽, 식물·나무, 책, 학습 환경
     · 화(火) → 빨강·주황, 남쪽, 햇빛, 활기찬 모임
     · 토(土) → 노랑·갈색, 중앙, 흙·도자기, 안정적 공간
     · 금(金) → 흰색·금속색, 서쪽, 금속 장신구, 정돈된 환경
     · 수(水) → 검정·파랑, 북쪽, 물·바다, 조용한 공간
5. 초등학생이 읽어도 바로 이해할 수 있는 쉬운 단어만 사용합니다
6. "불처럼 뜨거운 에너지를 가졌어요!", "물처럼 차분하고 지혜로운 타입이에요" 같은 재미있는 비유를 많이 사용합니다
7. 오행을 설명할 때 자연(나무, 불, 흙, 쇠, 물)에 비유해서 친근하게 풀어줍니다
8. 각 섹션은 충분히 상세하게 작성합니다 (각 섹션 최소 3-4문장)
9. 다정한 선생님이 이야기해주듯 편안한 존댓말을 사용합니다
10. 개인화는 유지하되 표현은 쉽게 — 사람마다 해석이 달라야 하지만, 그 차이를 일상 언어로 풀어 설명합니다.

응답 형식 (반드시 마크다운으로):

**중요: 아래 모든 섹션은 제공된 사주 데이터를 내부 근거로 삼되, 출력 텍스트에는 전문 용어를 한 번도 쓰지 마세요. [의미 변환표]에 따라 쉬운 일상 언어로만 표현합니다. 일반론이 아닌 이 사람만의 해석을 작성하세요.**

## 사주 총론
(내부 근거: 일간 오행·음양, 월지와의 관계, 오행 분포의 균형. → 출력은 "이 분은 ○○ 같은 기운을 타고났어요" 식의 비유로 풀어 쓰세요)

## 타고난 성격과 기질
(내부 근거: 일간 특성 + 월간/월지 십신. → 출력은 [의미 변환표] 표현으로 풀어 쓰세요. 예: 같은 동료 기운이 강하면 "스스로 해내려는 의지가 강한 분", 표현 기운이 강하면 "마음을 자유롭게 드러내는 분")

## 재물운과 직업운
(내부 근거: 재물·책임·표현 관련 글자들의 분포. → 출력은 "꾸준한 돈의 기운이 강해서 안정적인 직업이 잘 맞아요" 같이 풀어 쓰세요)

## 연애운과 결혼운
(내부 근거: **일지(배우자 자리)의 십신**을 최우선으로 사용. → 출력은 [의미 변환표]대로 풀어서 "안정적이고 성실한 배우자", "활동적이고 자유로운 인연" 등으로 표현. 인연 시기는 "○○년 ○월쯤 좋은 만남의 기운이 들어와요" 식으로)

## 건강운
(오행 분포의 불균형을 근거로. 목=간/담, 화=심장/소장, 토=위/비장, 금=폐/대장, 수=신장/방광. 과다·부족 오행을 자연 비유로 풀어 설명)

## 향후 12개월 월별 운세 (양력 기준)
(아래 [향후 12개월 월운] 표의 각 월 데이터를 내부 근거로 삼아 월별 해석을 작성하되, 출력에서는 십신 이름을 **절대 쓰지 말고** [의미 변환표]대로 풀어 쓰세요.
- 일간에 도움이 되는 기운인지, 부담을 주는 기운인지에 따라 해석이 달라져야 합니다.
- "4월은 새출발" 같은 달력 상식 금지. 이 사람만의 해석이어야 합니다.
- 형식:
- **2026년 4월**: 키워드 - 일상 언어로 풀어 쓴 설명
- **2026년 5월**: 키워드 - 일상 언어로 풀어 쓴 설명
...12개월)

## 대운 흐름과 종합 조언
(현재 대운 데이터를 내부 근거로 사용하되, 출력은 "지금은 ○○한 시기예요" 식으로 [의미 변환표] 표현으로 풀어 쓰세요. 다음 대운 전환점도 쉬운 말로 언급)

---
**최종 점검**: 응답을 작성한 뒤 위 금지어 목록의 단어가 단 하나라도 들어 있다면 그 부분을 [의미 변환표]대로 다시 풀어 쓰세요."""


def build_user_prompt(saju: dict) -> str:
    """사주 계산 결과를 Claude API 프롬프트로 변환한다."""
    yp = saju["year_pillar"]
    mp = saju["month_pillar"]
    dp = saju["day_pillar"]
    hp = saju["hour_pillar"]

    today = datetime.now()
    lines = [
        f"다음 사주팔자를 상세히 분석해주세요.",
        f"(오늘 날짜: {today.strftime('%Y년 %m월 %d일')})",
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
        "[십신 관계] (일간 기준)",
        f"- 년간: {ss['year_cheongan']}, 년지: {ss['year_jiji']}",
        f"- 월간: {ss['month_cheongan']}, 월지: {ss['month_jiji']}",
        f"- 일지(배우자궁): {ss['day_jiji']}",
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
        lines.append(
            f"  {d['age']}세({d['year_range']}): "
            f"{d['cheongan_hanja']}{d['jiji_hanja']}({d['cheongan']}{d['jiji']})"
            f" / 천간십신 {d['sipsin_cheongan']}, 지지십신 {d['sipsin_jiji']}"
        )

    if saju["current_daewoon"]:
        cd = saju["current_daewoon"]
        lines.append(
            f"- 현재 대운: {cd['cheongan_hanja']}{cd['jiji_hanja']}({cd['cheongan']}{cd['jiji']})"
            f" ({cd['year_range']}) / 천간십신 {cd['sipsin_cheongan']}, 지지십신 {cd['sipsin_jiji']}"
        )

    lines.append("")

    # 세운
    sw = saju["sewoon"]
    lines.extend([
        f"[올해 세운 ({sw['year']}년)]",
        f"- {sw['ganji']} / 천간십신 {sw['sipsin_cheongan']}, 지지십신 {sw['sipsin_jiji']}",
        "",
    ])

    # 신살
    ss_sin = saju["sinsal"]
    lines.extend([
        "[신살(神殺) — 내부 추론용. 출력에는 절대 용어 노출 금지]",
        f"- 공망: {'/'.join(ss_sin['gongmang'])} (사주 내 위치: {', '.join(ss_sin['gongmang_in_saju']) if ss_sin['gongmang_in_saju'] else '없음'})",
        f"- 천을귀인: {'/'.join(ss_sin['cheoneul_guin'])} → {'있음(귀인 복 강조)' if ss_sin['has_cheoneul_guin'] else '없음'}",
        f"- 도화: {ss_sin['dohwa']} → {'있음(매력·인기 강조)' if ss_sin['has_dohwa'] else '없음'}",
        f"- 역마: {ss_sin['yeokma']} → {'있음(이동·변화 강조)' if ss_sin['has_yeokma'] else '없음'}",
        f"- 화개: {ss_sin['hwagae']} → {'있음(예술·학문·종교 성향 강조)' if ss_sin['has_hwagae'] else '없음'}",
        "",
    ])

    # 신강신약 + 용신
    sk = saju["sinkang"]
    chung_desc = (
        f"{', '.join(sk['chung_pairs'])} → {', '.join(sk['chung_positions'])} 뿌리 50% 감쇄"
        if sk['chung_pairs'] else "없음"
    )
    hap_desc = ", ".join(sk['hap_bonus_applied']) if sk['hap_bonus_applied'] else "없음"
    lines.extend([
        "[신강신약·용신 — 내부 추론용. 출력 용어 노출 금지]",
        f"- 판정: {sk['sinkang']} (도움 점수 {sk['pos_score']} / 설기 점수 {sk['neg_score']}, 도움 비율 {sk['pos_ratio']}%)",
        f"- 방향: {sk['direction']}",
        f"- 계절: {sk['season']} (월령 기준)",
        f"- 충 영향: {chung_desc}",
        f"- 합 보너스: {hap_desc}",
        f"- 억부용신: {sk['eokbu_yongsin']} (후보 {' > '.join(sk['eokbu_candidates'])})",
        f"- 조후용신: {sk['johu_yongsin']} (기후 조절 관점)",
        f"- 최종 용신: {sk['yongsin']} 오행 [{sk['yongsin_method']}]",
        f"- 결정 근거: {sk['yongsin_reason']}",
        f"- 용신 후보 순위: {' > '.join(sk['yongsin_candidates'])}",
        f"- 가중 오행 분포: " + ", ".join(f"{k} {v}" for k, v in sk['ohaeng_weighted'].items()),
        "",
    ])

    # 합충형
    hch = saju["hapchunghyeong"]
    lines.append("[합·충·형 — 내부 추론용. 출력 용어 노출 금지]")
    def _fmt(label, items):
        return f"- {label}: {', '.join(items) if items else '없음'}"
    lines.append(_fmt("천간합", hch["cheongan_hap"]))
    lines.append(_fmt("육합", hch["yukhap"]))
    lines.append(_fmt("삼합/반합", hch["samhap"]))
    lines.append(_fmt("방합", hch["banghap"]))
    lines.append(_fmt("충", hch["chung"]))
    lines.append(_fmt("형", hch["hyeong"]))
    lines.append("")

    # 향후 12개월 월운
    lines.append("[향후 12개월 월운] (일간 기준 십신 관계 포함)")
    for w in saju["wolwoon"]:
        lines.append(
            f"- {w['year']}년 {w['month']:2d}월: {w['ganji']}"
            f" / 천간십신: {w['sipsin_cheongan']}"
            f", 지지십신: {w['sipsin_jiji']}"
            f" (오행: {w['ohaeng_cheongan']}·{w['ohaeng_jiji']})"
        )
    lines.append("")
    lines.append("위 정보를 바탕으로 각 섹션별로 상세하고 전문적인 분석을 해주세요.")

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
    birth_minute = data.get("minute")
    if birth_minute is not None and birth_minute != "":
        birth_minute = int(birth_minute)
    else:
        birth_minute = 0
    gender = data.get("gender", "male")
    calendar_type = data.get("calendar_type", "solar")
    is_intercalation = data.get("is_intercalation", False)
    birth_place = data.get("birth_place", "")
    birth_region = data.get("birth_region", "seoul")
    apply_solar_time = data.get("apply_solar_time", True)
    time_system = data.get("time_system", "joja")

    current_year = datetime.now().year

    # 사주 계산
    saju_result = calculate_saju(
        name=name,
        year=birth_year,
        month=birth_month,
        day=birth_day,
        hour=birth_hour,
        minute=birth_minute,
        gender=gender,
        calendar_type=calendar_type,
        is_intercalation=is_intercalation,
        birth_place=birth_place,
        birth_region=birth_region,
        current_year=current_year,
        apply_solar_time=apply_solar_time,
        time_system=time_system,
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


FOLLOWUP_SYSTEM = """당신은 사주를 아주 쉽게 설명해주는 친절한 선생님입니다.
사용자의 사주 분석 결과를 바탕으로 추가 질문에 답변해주세요.
초등학생도 이해할 수 있는 쉬운 말로 답변하세요. 전문 용어는 사용하지 마세요.
간결하고 핵심적으로 답변하되, 친절한 톤을 유지하세요."""


@app.post("/api/followup")
async def followup_question(request: Request):
    """추가 질문 (SSE 스트리밍)"""
    data = await request.json()
    question = data.get("question", "")
    saju_context = data.get("saju_context", "")
    chat_history = data.get("chat_history", [])

    messages = [{"role": "user", "content": f"[사주 분석 맥락]\n{saju_context}"}]
    messages.append({"role": "assistant", "content": "네, 이 사주에 대해 추가로 궁금한 점이 있으시면 편하게 물어보세요!"})

    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    async def event_stream():
        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=FOLLOWUP_SYSTEM,
            messages=messages,
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
