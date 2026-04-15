// ── 폼 초기화 ────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initSelects();
    initCalendarToggle();
    document.getElementById('saju-form').addEventListener('submit', handleSubmit);
    loadDeployTime();
});

function loadDeployTime() {
    fetch('/api/deploy-time')
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('deploy-date');
            if (el && data.deploy_time) el.textContent = '최종 배포: ' + data.deploy_time;
        })
        .catch(() => {});
}

function initSelects() {
    const yearSel = document.getElementById('year');
    const monthSel = document.getElementById('month');
    const daySel = document.getElementById('day');
    const hourSel = document.getElementById('hour');

    // 년도: 1920 ~ 현재년도
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= 1920; y--) {
        const opt = document.createElement('option');
        opt.value = y;
        opt.textContent = y + '년';
        yearSel.appendChild(opt);
    }
    yearSel.value = 1972;

    // 월
    for (let m = 1; m <= 12; m++) {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m + '월';
        monthSel.appendChild(opt);
    }

    // 일
    for (let d = 1; d <= 31; d++) {
        const opt = document.createElement('option');
        opt.value = d;
        opt.textContent = d + '일';
        daySel.appendChild(opt);
    }

    // 시간
    const siNames = [
        '자시 (23:00~01:00)', '축시 (01:00~03:00)', '인시 (03:00~05:00)',
        '묘시 (05:00~07:00)', '진시 (07:00~09:00)', '사시 (09:00~11:00)',
        '오시 (11:00~13:00)', '미시 (13:00~15:00)', '신시 (15:00~17:00)',
        '유시 (17:00~19:00)', '술시 (19:00~21:00)', '해시 (21:00~23:00)'
    ];
    const siHours = [23, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21];
    for (let i = 0; i < 12; i++) {
        const opt = document.createElement('option');
        opt.value = siHours[i];
        opt.textContent = siNames[i];
        hourSel.appendChild(opt);
    }
}

function initCalendarToggle() {
    const radios = document.querySelectorAll('input[name="calendar_type"]');
    const interGroup = document.getElementById('intercalation-group');
    radios.forEach(r => {
        r.addEventListener('change', () => {
            interGroup.style.display = r.value === 'lunar' && r.checked ? 'block' : 'none';
        });
    });
}

// ── 폼 제출 ─────────────────────────────────────────

async function handleSubmit(e) {
    e.preventDefault();

    const formData = {
        name: document.getElementById('name').value.trim(),
        year: document.getElementById('year').value,
        month: document.getElementById('month').value,
        day: document.getElementById('day').value,
        hour: document.getElementById('hour').value || null,
        minute: document.getElementById('minute').value || 0,
        gender: document.querySelector('input[name="gender"]:checked').value,
        calendar_type: document.querySelector('input[name="calendar_type"]:checked').value,
        is_intercalation: document.getElementById('is_intercalation').checked,
        birth_place: "",
        birth_region: document.getElementById('birth_region').value,
        apply_solar_time: true,
        time_system: document.querySelector('input[name="time_system"]:checked').value,
    };

    if (!formData.name) {
        alert('이름을 입력해주세요.');
        return;
    }

    // UI 상태 전환
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = true;

    document.getElementById('input-section').style.display = 'none';
    document.getElementById('loading-section').style.display = 'block';
    document.getElementById('result-section').style.display = 'none';

    try {
        const response = await fetch('/api/saju', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData),
        });

        if (!response.ok) {
            throw new Error(`서버 오류: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullText = '';
        const interpEl = document.getElementById('interpretation');
        interpEl.innerHTML = '';

        // AI 해석 로딩 표시 (진행 바)
        const interpCard = document.getElementById('interpretation-card');
        interpCard.querySelector('h2').textContent = 'AI 사주 해석';
        interpEl.innerHTML = `
            <div class="ai-progress">
                <div class="ai-progress-bar"><div class="ai-progress-fill" id="ai-progress-fill"></div></div>
                <p class="ai-progress-text" id="ai-progress-text">당신의 운명을 확인하고 있습니다...</p>
            </div>`;
        const EXPECTED_LENGTH = 3000;
        const progressFill = document.getElementById('ai-progress-fill');
        const progressText = document.getElementById('ai-progress-text');
        const progressMessages = [
            '사주팔자를 읽고 있습니다...',
            '오행의 균형을 살펴보고 있습니다...',
            '운세를 분석하고 있습니다...',
            '월별 운세를 작성하고 있습니다...',
            '거의 다 되었습니다...',
        ];

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                    const data = JSON.parse(jsonStr);
                    if (data.type === 'saju_data') {
                        // 사주 표를 즉시 표시
                        document.getElementById('loading-section').style.display = 'none';
                        document.getElementById('result-section').style.display = 'block';
                        renderSajuTable(data.data);
                        document.getElementById('saju-table-card').scrollIntoView({ behavior: 'smooth' });
                    } else if (data.type === 'text') {
                        fullText += data.content;
                        // 진행 바 업데이트
                        if (progressFill) {
                            const pct = Math.min(95, (fullText.length / EXPECTED_LENGTH) * 100);
                            progressFill.style.width = pct + '%';
                            const msgIdx = Math.min(Math.floor(pct / 20), progressMessages.length - 1);
                            progressText.textContent = progressMessages[msgIdx];
                        }
                    }
                } catch (parseErr) {
                    // JSON 파싱 실패 시 무시
                }
            }
        }

        // AI 해석 완료 → 한 번에 표시
        document.getElementById('interpretation-card').querySelector('h2').textContent = 'AI 사주 해석';
        if (fullText) {
            interpEl.innerHTML = marked.parse(fullText);
            // 추가 질문 영역 표시
            sajuContext = fullText;
            chatHistory = [];
            document.getElementById('followup-card').style.display = 'block';
            document.getElementById('followup-chat').innerHTML = '';
        } else {
            interpEl.innerHTML = '<p>해석 결과를 불러오지 못했습니다.</p>';
        }

    } catch (err) {
        document.getElementById('loading-section').style.display = 'none';
        document.getElementById('input-section').style.display = 'block';
        alert('분석 중 오류가 발생했습니다: ' + err.message);
    } finally {
        submitBtn.disabled = false;
    }
}

// ── 추가 질문 ───────────────────────────────────────

let sajuContext = '';
let chatHistory = [];

async function sendFollowup() {
    const input = document.getElementById('followup-input');
    const question = input.value.trim();
    if (!question) return;

    const chatEl = document.getElementById('followup-chat');
    const btn = document.getElementById('followup-btn');

    // 질문 표시
    chatEl.innerHTML += `<div class="chat-msg chat-user"><strong>Q.</strong> ${escapeHtml(question)}</div>`;
    input.value = '';
    btn.disabled = true;
    btn.textContent = '답변 중...';

    // 답변 영역
    const answerDiv = document.createElement('div');
    answerDiv.className = 'chat-msg chat-ai';
    answerDiv.innerHTML = '<strong>A.</strong> <span class="chat-loading">답변을 작성하고 있습니다...</span>';
    chatEl.appendChild(answerDiv);
    chatEl.scrollTop = chatEl.scrollHeight;

    try {
        const response = await fetch('/api/followup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                saju_context: sajuContext,
                chat_history: chatHistory,
            }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let answerText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6).trim());
                    if (data.type === 'text') {
                        answerText += data.content;
                        answerDiv.innerHTML = '<strong>A.</strong> ' + marked.parse(answerText);
                        chatEl.scrollTop = chatEl.scrollHeight;
                    }
                } catch (e) {}
            }
        }

        if (answerText) {
            answerDiv.innerHTML = '<strong>A.</strong> ' + marked.parse(answerText);
            chatHistory.push({ role: 'user', content: question });
            chatHistory.push({ role: 'assistant', content: answerText });
        }
    } catch (err) {
        answerDiv.innerHTML = '<strong>A.</strong> 답변을 가져오지 못했습니다.';
    } finally {
        btn.disabled = false;
        btn.textContent = '질문';
        chatEl.scrollTop = chatEl.scrollHeight;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Enter 키로 질문 전송
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('followup-input');
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.isComposing) sendFollowup();
        });
    }
});

// ── 사주 표 렌더링 ──────────────────────────────────

const OHAENG_CLASS = {
    '목': 'oh-wood', '화': 'oh-fire', '토': 'oh-earth',
    '금': 'oh-metal', '수': 'oh-water'
};

const OHAENG_LABELS = {
    '목': '木 목', '화': '火 화', '토': '土 토',
    '금': '金 금', '수': '水 수'
};

function renderSajuTable(saju) {
    // 기본 정보
    const infoEl = document.getElementById('saju-info');
    let timeNote = '';
    if (saju.has_hour && saju.solar_time_offset !== 0) {
        const eh = saju.effective_hour;
        const em = String(saju.effective_minute).padStart(2, '0');
        const regionName = saju.birth_region_name || '서울';
        timeNote = `<div class="solar-note">출생 시각을 ${regionName} 기준 진태양시로 보정해 ${eh}시 ${em}분으로 계산했어요.</div>`;
    }
    infoEl.innerHTML = `
        <strong>${saju.name}</strong>님 (${saju.gender}) |
        ${saju.birth_date} |
        ${saju.ddi}띠
        ${timeNote}
    `;

    // 사주 표
    const tableEl = document.getElementById('saju-table');
    const hasHour = saju.has_hour;
    const pillars = [];

    if (hasHour) pillars.push({ label: '시주', data: saju.hour_pillar });
    pillars.push({ label: '일주', data: saju.day_pillar });
    pillars.push({ label: '월주', data: saju.month_pillar });
    pillars.push({ label: '년주', data: saju.year_pillar });

    let html = `<div class="saju-grid ${hasHour ? '' : 'no-hour'}">`;

    // 헤더 행
    html += `<div class="saju-cell header"></div>`;
    pillars.forEach(p => {
        html += `<div class="saju-cell header">${p.label}</div>`;
    });

    // 천간 행
    html += `<div class="saju-cell row-label">천간</div>`;
    pillars.forEach(p => {
        const d = p.data;
        html += `<div class="saju-cell">
            <span class="hanja">${d.cheongan_hanja}</span>
            <span class="hangul">${d.cheongan}</span>
            <span class="ohaeng-badge ${OHAENG_CLASS[d.ohaeng_cheongan]}">${d.ohaeng_cheongan}</span>
        </div>`;
    });

    // 지지 행
    html += `<div class="saju-cell row-label">지지</div>`;
    pillars.forEach(p => {
        const d = p.data;
        html += `<div class="saju-cell">
            <span class="hanja">${d.jiji_hanja}</span>
            <span class="hangul">${d.jiji}</span>
            <span class="ohaeng-badge ${OHAENG_CLASS[d.ohaeng_jiji]}">${d.ohaeng_jiji}</span>
        </div>`;
    });

    html += '</div>';
    tableEl.innerHTML = html;

    // 오행 차트
    renderOhaengChart(saju.ohaeng, saju.ohaeng_total);
}

function renderOhaengChart(ohaeng, total) {
    const chartEl = document.getElementById('ohaeng-chart');
    const maxCount = Math.max(...Object.values(ohaeng), 1);

    let html = '<div class="ohaeng-chart"><h3>오행 분포</h3>';
    const order = ['목', '화', '토', '금', '수'];

    order.forEach(oh => {
        const count = ohaeng[oh];
        const pct = total > 0 ? (count / total * 100) : 0;
        const barPct = maxCount > 0 ? (count / maxCount * 100) : 0;

        html += `
        <div class="ohaeng-bar-row">
            <div class="ohaeng-bar-label">${OHAENG_LABELS[oh]}</div>
            <div class="ohaeng-bar-track">
                <div class="ohaeng-bar-fill ${OHAENG_CLASS[oh]}"
                     style="width: ${barPct}%">
                    ${count > 0 ? Math.round(pct) + '%' : ''}
                </div>
            </div>
            <div class="ohaeng-bar-count">${count}</div>
        </div>`;
    });

    html += '</div>';
    chartEl.innerHTML = html;
}
