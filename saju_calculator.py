"""
사주팔자(四柱八字) 계산 엔진

천간지지 기반으로 년주, 월주, 일주, 시주를 계산하고
오행 분석, 십신, 대운 등 부가 데이터를 산출한다.
"""

from datetime import date, timedelta
from korean_lunar_calendar import KoreanLunarCalendar
from solar_terms import get_solar_term_date, JEOLGI_MONTH_JIJI

# ── 기본 상수 ──────────────────────────────────────────

CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
CHEONGAN_HANJA = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
JIJI_HANJA = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 천간 → 오행
CHEONGAN_OHAENG = ["목", "목", "화", "화", "토", "토", "금", "금", "수", "수"]
# 지지 → 오행
JIJI_OHAENG = ["수", "토", "목", "목", "토", "화", "화", "토", "금", "금", "토", "수"]

# 천간 → 음양 (0=양, 1=음)
CHEONGAN_EUMYANG = ["양", "음", "양", "음", "양", "음", "양", "음", "양", "음"]

# 오행 한자
OHAENG_HANJA = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}

# 오행 색상 (프론트엔드용)
OHAENG_COLOR = {"목": "#228B22", "화": "#DC143C", "토": "#DAA520", "금": "#A0A0A0", "수": "#191970"}

# 띠 (지지 대응)
DDI = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]

# ── 십신(十神) ──────────────────────────────────────────

SIPSIN_NAMES = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]

# 십신 계산: 일간 기준 다른 천간과의 오행 관계
# 같은 오행 같은 음양 → 비견, 같은 오행 다른 음양 → 겁재
# 내가 생하는 오행 같은 음양 → 식신, 다른 음양 → 상관
# 내가 극하는 오행 같은 음양 → 편재, 다른 음양 → 정재
# 나를 극하는 오행 같은 음양 → 편관, 다른 음양 → 정관
# 나를 생하는 오행 같은 음양 → 편인, 다른 음양 → 정인

OHAENG_ORDER = ["목", "화", "토", "금", "수"]  # 상생 순서
OHAENG_INDEX = {oh: i for i, oh in enumerate(OHAENG_ORDER)}


def get_sipsin(ilgan_idx: int, target_cheongan_idx: int) -> str:
    """일간 기준 대상 천간의 십신을 구한다."""
    il_oh = OHAENG_INDEX[CHEONGAN_OHAENG[ilgan_idx]]
    tg_oh = OHAENG_INDEX[CHEONGAN_OHAENG[target_cheongan_idx]]
    il_ey = ilgan_idx % 2  # 0=양, 1=음
    tg_ey = target_cheongan_idx % 2

    same_ey = (il_ey == tg_ey)
    diff = (tg_oh - il_oh) % 5

    if diff == 0:  # 같은 오행
        return "비견" if same_ey else "겁재"
    elif diff == 1:  # 내가 생하는 오행
        return "식신" if same_ey else "상관"
    elif diff == 2:  # 내가 극하는 오행
        return "편재" if same_ey else "정재"
    elif diff == 3:  # 나를 극하는 오행
        return "편관" if same_ey else "정관"
    else:  # diff == 4, 나를 생하는 오행
        return "편인" if same_ey else "정인"


# ── 지장간(支藏干) ──────────────────────────────────────

JIJANGGAN = {
    0:  [9, ],         # 자: 계
    1:  [9, 7, 5],     # 축: 계, 신, 기
    2:  [4, 2, 0],     # 인: 무, 병, 갑
    3:  [0, ],         # 묘: 갑 (을이 본기이지만 간략히)
    4:  [1, 9, 4],     # 진: 을, 계, 무
    5:  [4, 6, 2],     # 사: 무, 경, 병
    6:  [5, ],         # 오: 기 (정이 본기)
    7:  [5, 1, 3],     # 미: 기, 을, 정
    8:  [4, 8, 6],     # 신: 무, 임, 경
    9:  [6, ],         # 유: 경 (신이 본기)
    10: [7, 3, 4],     # 술: 신, 정, 무
    11: [4, 0, 8],     # 해: 무, 갑, 임
}

# 지장간 본기 (가장 영향력 큰 천간)
JIJANGGAN_BONGI = {
    0: 9,   # 자 → 계
    1: 5,   # 축 → 기
    2: 0,   # 인 → 갑
    3: 1,   # 묘 → 을
    4: 4,   # 진 → 무
    5: 2,   # 사 → 병
    6: 3,   # 오 → 정
    7: 5,   # 미 → 기
    8: 6,   # 신 → 경
    9: 7,   # 유 → 신
    10: 4,  # 술 → 무
    11: 8,  # 해 → 임
}


# ── 년상기월법 (年上起月法) ────────────────────────────

# 년간에 따른 인월(1월) 시작 천간 인덱스
YEAR_MONTH_START = {
    0: 2, 1: 4, 2: 6, 3: 8, 4: 0,  # 갑→병, 을→무, 병→경, 정→임, 무→갑
    5: 2, 6: 4, 7: 6, 8: 8, 9: 0,  # 기→병, 경→무, 신→경, 임→임, 계→갑
}


# ── 일상기시법 (日上起時法) ────────────────────────────

# 일간에 따른 자시(子時) 시작 천간 인덱스
DAY_HOUR_START = {
    0: 0, 1: 2, 2: 4, 3: 6, 4: 8,  # 갑→갑, 을→병, 병→무, 정→경, 무→임
    5: 0, 6: 2, 7: 4, 8: 6, 9: 8,  # 기→갑, 경→병, 신→무, 임→경, 계→임
}


# ── 음양력 변환 ────────────────────────────────────────

def lunar_to_solar(year: int, month: int, day: int, is_intercalation: bool = False) -> date:
    """음력 날짜를 양력으로 변환한다."""
    cal = KoreanLunarCalendar()
    cal.setLunarDate(year, month, day, is_intercalation)
    result = cal.SolarIsoFormat()
    parts = result.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


# ── 년주 계산 ──────────────────────────────────────────

def calc_year_pillar(solar_date: date) -> tuple[int, int]:
    """
    년주(年柱)를 계산한다.
    입춘 기준으로 년도를 보정한다.

    Returns:
        (천간인덱스, 지지인덱스) 튜플
    """
    year = solar_date.year
    # 해당 년도 입춘일 확인
    ipchun = get_solar_term_date(year, 0)  # 0 = 입춘
    ipchun_date = date(year, ipchun[0], ipchun[1])

    # 입춘 전이면 전년도 간지
    if solar_date < ipchun_date:
        year -= 1

    cheongan_idx = (year - 4) % 10
    jiji_idx = (year - 4) % 12
    return cheongan_idx, jiji_idx


# ── 월주 계산 ──────────────────────────────────────────

def calc_month_pillar(solar_date: date, year_cheongan_idx: int) -> tuple[int, int]:
    """
    월주(月柱)를 계산한다.
    절기 기준으로 월을 결정하고, 년상기월법으로 천간을 정한다.

    Returns:
        (천간인덱스, 지지인덱스) 튜플
    """
    year = solar_date.year
    month_idx = _get_month_index(solar_date, year)
    jiji_idx = JEOLGI_MONTH_JIJI[month_idx]

    # 년상기월법: 년간에 따른 인월(1월) 시작 천간
    start = YEAR_MONTH_START[year_cheongan_idx]
    cheongan_idx = (start + month_idx) % 10

    return cheongan_idx, jiji_idx


def _get_month_index(solar_date: date, year: int) -> int:
    """절기 기준으로 몇 월인지 인덱스를 반환한다 (0=인월 ~ 11=축월)."""
    # 소한(11번 절기)은 다음해 1월이므로 별도 처리
    # 역순으로 절기를 확인하여 해당 월 결정
    for i in range(11, -1, -1):
        term = get_solar_term_date(year, i)
        term_month, term_day = term

        # 소한(idx=11)은 다음해 1월
        if i == 11:
            term_date = date(year + 1, term_month, term_day)
        else:
            term_date = date(year, term_month, term_day)

        if solar_date >= term_date:
            return i

    # 입춘 이전이면 전년도 소한~입춘 사이 = 축월(12월)
    # 전년도 소한 확인
    prev_sohan = get_solar_term_date(year - 1, 11)
    prev_sohan_date = date(year, prev_sohan[0], prev_sohan[1])
    if solar_date >= prev_sohan_date:
        return 11  # 축월

    # 그 이전이면 전년도 대설~소한 = 자월(11월)
    return 10  # 자월


# ── 일주 계산 ──────────────────────────────────────────

# 기준일: 1900년 1월 1일 = 갑술(甲戌)일
_BASE_DATE = date(1900, 1, 1)
_BASE_CHEONGAN = 0   # 갑(甲) = 0
_BASE_JIJI = 10      # 술(戌) = 10


def calc_day_pillar(solar_date: date) -> tuple[int, int]:
    """
    일주(日柱)를 계산한다.
    기준일(1900-01-01 경자일)로부터의 일수 차이로 산출한다.

    Returns:
        (천간인덱스, 지지인덱스) 튜플
    """
    days_diff = (solar_date - _BASE_DATE).days
    cheongan_idx = (_BASE_CHEONGAN + days_diff) % 10
    jiji_idx = (_BASE_JIJI + days_diff) % 12
    return cheongan_idx, jiji_idx


# ── 시주 계산 ──────────────────────────────────────────

def get_hour_jiji(hour: int) -> int:
    """태어난 시각(0~23)에 대응하는 지지 인덱스를 반환한다."""
    if hour == 23 or hour == 0:
        return 0   # 자시
    return ((hour + 1) // 2) % 12


def calc_hour_pillar(hour: int, day_cheongan_idx: int) -> tuple[int, int]:
    """
    시주(時柱)를 계산한다.

    Args:
        hour: 태어난 시각 (0~23)
        day_cheongan_idx: 일간 인덱스

    Returns:
        (천간인덱스, 지지인덱스) 튜플
    """
    jiji_idx = get_hour_jiji(hour)
    start = DAY_HOUR_START[day_cheongan_idx]
    cheongan_idx = (start + jiji_idx) % 10
    return cheongan_idx, jiji_idx


# ── 오행 분석 ──────────────────────────────────────────

def analyze_ohaeng(pillars: list[tuple[int, int]]) -> dict[str, int]:
    """사주 기둥들의 오행 분포를 분석한다."""
    count = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    for cheongan_idx, jiji_idx in pillars:
        count[CHEONGAN_OHAENG[cheongan_idx]] += 1
        count[JIJI_OHAENG[jiji_idx]] += 1
    return count


# ── 대운 계산 ──────────────────────────────────────────

def calc_daewoon(solar_date: date, gender: str, year_cheongan_idx: int,
                 month_cheongan_idx: int, month_jiji_idx: int,
                 ilgan_idx: int) -> dict:
    """
    대운(大運)을 계산한다.

    대운 방향:
    - 남자 양년생 / 여자 음년생 → 순행 (절기 순방향)
    - 남자 음년생 / 여자 양년생 → 역행 (절기 역방향)

    Returns:
        대운 정보 딕셔너리
    """
    year_eumyang = year_cheongan_idx % 2  # 0=양, 1=음
    is_male = (gender == "male")

    # 순행: 양남음녀, 역행: 음남양녀
    forward = (is_male and year_eumyang == 0) or (not is_male and year_eumyang == 1)

    # 대운 시작 나이 계산 (절입일까지의 일수 / 3 = 대운수)
    year = solar_date.year
    if forward:
        # 다음 절기까지의 일수
        target_date = _find_next_jeolgi(solar_date, year)
    else:
        # 이전 절기까지의 일수
        target_date = _find_prev_jeolgi(solar_date, year)

    days_diff = abs((target_date - solar_date).days)
    start_age = max(1, round(days_diff / 3))  # 3일 = 1년

    # 대운 기둥 생성 (10개)
    daewoon_list = []
    mc = month_cheongan_idx
    mj = month_jiji_idx

    for i in range(10):
        if forward:
            mc = (month_cheongan_idx + (i + 1)) % 10
            mj = (month_jiji_idx + (i + 1)) % 12
        else:
            mc = (month_cheongan_idx - (i + 1)) % 10
            mj = (month_jiji_idx - (i + 1)) % 12

        age = start_age + (i * 10)
        birth_year = solar_date.year
        daewoon_list.append({
            "age": age,
            "year_range": f"{birth_year + age}~{birth_year + age + 9}",
            "cheongan": CHEONGAN[mc],
            "cheongan_hanja": CHEONGAN_HANJA[mc],
            "jiji": JIJI[mj],
            "jiji_hanja": JIJI_HANJA[mj],
            "ohaeng_cheongan": CHEONGAN_OHAENG[mc],
            "ohaeng_jiji": JIJI_OHAENG[mj],
            "sipsin_cheongan": get_sipsin(ilgan_idx, mc),
            "sipsin_jiji": get_sipsin(ilgan_idx, JIJANGGAN_BONGI[mj]),
        })

    return {
        "direction": "순행" if forward else "역행",
        "start_age": start_age,
        "list": daewoon_list,
    }


def _find_next_jeolgi(solar_date: date, year: int) -> date:
    """주어진 날짜 이후 가장 가까운 절기 날짜를 찾는다."""
    for m in range(12):
        term = get_solar_term_date(year, m)
        if m == 11:
            term_date = date(year + 1, term[0], term[1])
        else:
            term_date = date(year, term[0], term[1])
        if term_date > solar_date:
            return term_date

    # 다음 해 입춘
    term = get_solar_term_date(year + 1, 0)
    return date(year + 1, term[0], term[1])


def _find_prev_jeolgi(solar_date: date, year: int) -> date:
    """주어진 날짜 이전 가장 가까운 절기 날짜를 찾는다."""
    for m in range(11, -1, -1):
        term = get_solar_term_date(year, m)
        if m == 11:
            term_date = date(year + 1, term[0], term[1])
        else:
            term_date = date(year, term[0], term[1])
        if term_date <= solar_date:
            return term_date

    # 전년도 소한
    term = get_solar_term_date(year - 1, 11)
    return date(year, term[0], term[1])


# ── 세운(歲運) 계산 ────────────────────────────────────

def calc_sewoon(current_year: int, ilgan_idx: int) -> dict:
    """현재 년도의 세운(歲運)을 일간 기준 십신과 함께 계산한다."""
    c_idx = (current_year - 4) % 10
    j_idx = (current_year - 4) % 12
    return {
        "year": current_year,
        "cheongan": CHEONGAN[c_idx],
        "cheongan_hanja": CHEONGAN_HANJA[c_idx],
        "jiji": JIJI[j_idx],
        "jiji_hanja": JIJI_HANJA[j_idx],
        "ohaeng_cheongan": CHEONGAN_OHAENG[c_idx],
        "ohaeng_jiji": JIJI_OHAENG[j_idx],
        "ganji": f"{CHEONGAN[c_idx]}{JIJI[j_idx]}({CHEONGAN_HANJA[c_idx]}{JIJI_HANJA[j_idx]})",
        "sipsin_cheongan": get_sipsin(ilgan_idx, c_idx),
        "sipsin_jiji": get_sipsin(ilgan_idx, JIJANGGAN_BONGI[j_idx]),
    }


# ── 월운(月運) 계산 ────────────────────────────────────

def calc_wolwoon_next_12(base_date: date, ilgan_idx: int) -> list[dict]:
    """
    base_date가 속한 달부터 향후 12개월간의 월운(月運)을 계산한다.
    각 월의 간지는 해당 월 15일을 기준으로 절기에 따라 산출하며,
    일간 기준 십신 관계까지 포함한다.
    """
    results = []
    y, m = base_date.year, base_date.month
    for _ in range(12):
        ref = date(y, m, 15)
        yc, _yj = calc_year_pillar(ref)
        mc, mj = calc_month_pillar(ref, yc)
        results.append({
            "year": y,
            "month": m,
            "cheongan": CHEONGAN[mc],
            "cheongan_hanja": CHEONGAN_HANJA[mc],
            "jiji": JIJI[mj],
            "jiji_hanja": JIJI_HANJA[mj],
            "ganji": f"{CHEONGAN_HANJA[mc]}{JIJI_HANJA[mj]}({CHEONGAN[mc]}{JIJI[mj]})",
            "ohaeng_cheongan": CHEONGAN_OHAENG[mc],
            "ohaeng_jiji": JIJI_OHAENG[mj],
            "sipsin_cheongan": get_sipsin(ilgan_idx, mc),
            "sipsin_jiji": get_sipsin(ilgan_idx, JIJANGGAN_BONGI[mj]),
        })
        m += 1
        if m > 12:
            m = 1
            y += 1
    return results


# ── 현재 대운 찾기 ────────────────────────────────────

def find_current_daewoon(daewoon: dict, birth_year: int, current_year: int) -> dict | None:
    """현재 나이에 해당하는 대운을 찾는다."""
    age = current_year - birth_year
    for dw in daewoon["list"]:
        if dw["age"] <= age < dw["age"] + 10:
            return dw
    return daewoon["list"][-1] if daewoon["list"] else None


# ── 메인 계산 함수 ────────────────────────────────────

def calculate_saju(
    name: str,
    year: int,
    month: int,
    day: int,
    hour: int | None,
    gender: str,
    calendar_type: str = "solar",
    is_intercalation: bool = False,
    birth_place: str = "",
    current_year: int = 2026,
) -> dict:
    """
    사주팔자를 종합 계산한다.

    Args:
        name: 이름
        year, month, day: 생년월일
        hour: 태어난 시각 (0~23, None이면 시주 제외)
        gender: "male" 또는 "female"
        calendar_type: "solar" 또는 "lunar"
        is_intercalation: 윤달 여부 (음력일 때만)
        birth_place: 출생지
        current_year: 현재 년도 (세운 계산용)

    Returns:
        사주 분석 결과 딕셔너리
    """
    # 1. 양력 날짜 확정
    if calendar_type == "lunar":
        solar_date = lunar_to_solar(year, month, day, is_intercalation)
    else:
        solar_date = date(year, month, day)

    # 2. 사주 계산
    year_c, year_j = calc_year_pillar(solar_date)
    month_c, month_j = calc_month_pillar(solar_date, year_c)
    day_c, day_j = calc_day_pillar(solar_date)

    pillars = [(year_c, year_j), (month_c, month_j), (day_c, day_j)]
    has_hour = hour is not None

    if has_hour:
        hour_c, hour_j = calc_hour_pillar(hour, day_c)
        pillars.append((hour_c, hour_j))
    else:
        hour_c, hour_j = None, None

    # 3. 오행 분석
    ohaeng = analyze_ohaeng(pillars)

    # 4. 십신 계산 (일간 기준)
    ilgan_idx = day_c
    sipsin = {
        "year_cheongan": get_sipsin(ilgan_idx, year_c),
        "year_jiji": get_sipsin(ilgan_idx, JIJANGGAN_BONGI[year_j]),
        "month_cheongan": get_sipsin(ilgan_idx, month_c),
        "month_jiji": get_sipsin(ilgan_idx, JIJANGGAN_BONGI[month_j]),
        "day_jiji": get_sipsin(ilgan_idx, JIJANGGAN_BONGI[day_j]),  # 배우자궁
    }
    if has_hour:
        sipsin["hour_cheongan"] = get_sipsin(ilgan_idx, hour_c)
        sipsin["hour_jiji"] = get_sipsin(ilgan_idx, JIJANGGAN_BONGI[hour_j])

    # 5. 대운 계산
    daewoon = calc_daewoon(solar_date, gender, year_c, month_c, month_j, ilgan_idx)
    current_dw = find_current_daewoon(daewoon, solar_date.year, current_year)

    # 6. 세운 계산
    sewoon = calc_sewoon(current_year, ilgan_idx)

    # 6-1. 향후 12개월 월운 계산 (오늘 기준)
    wolwoon = calc_wolwoon_next_12(date.today(), ilgan_idx)

    # 7. 결과 조합
    def pillar_info(c_idx, j_idx):
        return {
            "cheongan": CHEONGAN[c_idx],
            "cheongan_hanja": CHEONGAN_HANJA[c_idx],
            "jiji": JIJI[j_idx],
            "jiji_hanja": JIJI_HANJA[j_idx],
            "ohaeng_cheongan": CHEONGAN_OHAENG[c_idx],
            "ohaeng_jiji": JIJI_OHAENG[j_idx],
            "eumyang_cheongan": CHEONGAN_EUMYANG[c_idx],
            "eumyang_jiji": CHEONGAN_EUMYANG[j_idx % 10] if j_idx < 10 else "양" if j_idx % 2 == 0 else "음",
        }

    result = {
        "name": name,
        "gender": "남" if gender == "male" else "여",
        "birth_date": solar_date.isoformat(),
        "birth_hour": hour,
        "calendar_type": calendar_type,
        "birth_place": birth_place,
        "ddi": DDI[year_j],  # 띠

        "year_pillar": pillar_info(year_c, year_j),
        "month_pillar": pillar_info(month_c, month_j),
        "day_pillar": pillar_info(day_c, day_j),
        "hour_pillar": pillar_info(hour_c, hour_j) if has_hour else None,

        "ilgan": {
            "name": CHEONGAN[day_c],
            "hanja": CHEONGAN_HANJA[day_c],
            "ohaeng": CHEONGAN_OHAENG[day_c],
            "eumyang": CHEONGAN_EUMYANG[day_c],
        },

        "ohaeng": ohaeng,
        "ohaeng_total": sum(ohaeng.values()),
        "sipsin": sipsin,
        "daewoon": daewoon,
        "current_daewoon": current_dw,
        "sewoon": sewoon,
        "wolwoon": wolwoon,
        "has_hour": has_hour,
    }

    return result
