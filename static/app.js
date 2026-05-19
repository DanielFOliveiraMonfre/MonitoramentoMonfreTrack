const state = {
    selectedOccurrenceId: null,
    selectedOperator: null,
    filter: "todas",
    lastData: null,
    trocaTurno: null,
    occurrenceDrafts: {},
    handoverDraft: "",
    handoverReference: "GERAL",
};

const currentUser = window.MONFRETRACK_USER || {nome: "daniel.oliveira", admin: false};
const DEFAULT_OPERATOR = currentUser.nome || "daniel.oliveira";
const qs = (selector) => document.querySelector(selector);

function setClock() {
    const el = qs("#clock");
    if (el) el.textContent = new Date().toLocaleTimeString("pt-BR");
}

function statusClass(status, online) {
    if (!online) return "offline";
    if (status === "RODANDO") return "running";
    if (status === "TRAVADO" || status === "PAUSADO") return "stopped";
    return "online";
}

function statusLabel(texto) {
    return String(texto || "-").replaceAll("_", " ");
}

function isFadiga(oc) {
    return String(oc.tipo || "").toUpperCase() === "FADIGA";
}

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function rolePill(op) {
    return `<span class="role-pill ${op.admin ? "" : "user"}">${op.admin ? "Admin" : "Usuario"}</span>`;
}

function operatorCard(op) {
    const selected = state.selectedOperator === op.operador ? "selected" : "";
    const onlineText = op.online ? "Online" : "Offline";
    const tempo = op.online ? op.tempo_aberto : "-";

    return `
        <article class="operator-card ${selected}" data-operator="${op.operador}">
            <div class="operator-card-head">
                <div>
                    <strong>${op.operador}</strong>
                    <span>${op.turno || "-"} / ${op.maquina || "-"}</span>
                </div>
                <span class="status-pill ${statusClass(op.status, op.online)}">${onlineText}</span>
            </div>
            <div class="operator-card-stats">
                <div><span>Status</span><b>${statusLabel(op.status)}</b></div>
                <div><span>Tratados</span><b>${op.tratados_hoje || 0}</b></div>
                <div><span>Tempo</span><b>${tempo}</b></div>
            </div>
            <div class="operator-card-foot">
                ${rolePill(op)}
                <small>${op.ultimo_heartbeat || "sem heartbeat"}</small>
            </div>
            ${selected ? `
                <div class="operator-expanded">
                    <button class="ghost-button" data-operator-filter="${op.operador}">Ver ocorrências</button>
                    <span>Versão: ${op.versao || "-"}</span>
                    <span>Aberto em: ${op.app_aberto_em || "-"}</span>
                </div>
            ` : ""}
        </article>
    `;
}

function renderOperators(data) {
    const grid = qs("#operadores-grid");
    if (!grid) return;

    const operadores = data.operadores || [];
    grid.innerHTML = operadores.length
        ? operadores.map(operatorCard).join("")
        : `<div class="empty-block">Nenhum operador cadastrado.</div>`;

    grid.querySelectorAll(".operator-card").forEach((card) => {
        card.addEventListener("click", (event) => {
            if (event.target.dataset.operatorFilter) return;
            const operador = card.dataset.operator;
            state.selectedOperator = state.selectedOperator === operador ? null : operador;
            renderOperators(data);
        });
    });

    grid.querySelectorAll("[data-operator-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            state.filter = "todas";
            state.selectedOccurrenceId = null;
            const ocorrencias = (data.ocorrencias_abertas || []).filter((oc) => oc.operador === button.dataset.operatorFilter);
            const lista = qs("#ocorrencias-operacao") || qs("#ocorrencias-resumo");
            if (lista) {
                lista.innerHTML = ocorrencias.length
                    ? ocorrencias.map((oc) => occurrenceCard(oc, false)).join("")
                    : `<div class="empty-block">Nenhuma ocorrência aberta para este operador.</div>`;
            }
        });
    });
}

function turnoCard(turno) {
    const pct = Math.min(100, Math.round((turno.online / Math.max(1, turno.total)) * 100));

    return `
        <article class="turno-card">
            <div class="turno-card-head">
                <strong>${turno.turno}</strong>
                <span>${turno.online}/${turno.total} online</span>
            </div>
            <div class="turno-bar"><span style="width:${pct}%"></span></div>
            <div class="turno-grid">
                <div><span>Tratados</span><b>${turno.tratados_hoje}</b></div>
                <div><span>Fadigas</span><b>${turno.fadigas_abertas}</b></div>
                <div><span>Pendências</span><b>${turno.ocorrencias_abertas}</b></div>
                <div><span>Média</span><b>${turno.produtividade}</b></div>
            </div>
        </article>
    `;
}

function renderTurnos(data) {
    const grid = qs("#turnos-grid");
    if (!grid) return;

    grid.innerHTML = (data.turnos || []).length
        ? data.turnos.map(turnoCard).join("")
        : `<div class="empty-block">Nenhum turno carregado.</div>`;
}

function occurrenceBadge(oc) {
    const cls = oc.status === "FINALIZADA" ? "online" :
        oc.status === "EM_ACOMPANHAMENTO" ? "running" :
        oc.status === "CANCELADA" ? "stopped" :
        oc.status === "ABERTA" ? "stopped" : "offline";

    return `<span class="status-pill ${cls}">${statusLabel(oc.status)}</span>`;
}

function occurrenceTitle(oc) {
    if (isFadiga(oc)) {
        const placa = oc.placa && oc.placa !== "-" ? ` / ${oc.placa}` : "";
        return `FADIGA #${oc.id}${placa}`;
    }

    return `${statusLabel(oc.tipo || "OCORRENCIA")} #${oc.id}`;
}

function occurrenceSubtitle(oc) {
    if (isFadiga(oc)) {
        const motorista = oc.motorista && oc.motorista !== "Nao informado" ? oc.motorista : "Motorista não informado";
        return `${motorista} / tratando: ${oc.operador || "-"}`;
    }

    return `Tratando: ${oc.operador || "-"} / ${oc.maquina || "-"}`;
}

function occurrenceCard(oc, compact = false) {
    const selected = state.selectedOccurrenceId === oc.id ? "selected" : "";
    const timer = oc.timer_restante || "-";
    const percent = oc.timer_percentual || 0;
    const note = Number(oc.observacoes_qtd || 0) > 0
        ? `<span class="note-pill" title="Possui observações">Obs. ${oc.observacoes_qtd}</span>`
        : "";
    const fatigueCount = isFadiga(oc) && Number(oc.alertas_qtd || 1) > 1
        ? `<span class="fatigue-count" title="Alertas de fadiga agrupados">x${oc.alertas_qtd}</span>`
        : "";

    return `
        <article class="occurrence-card ${selected}" data-occurrence-id="${oc.id}">
            <div class="occurrence-top">
                <div>
                    <div class="plate">${occurrenceTitle(oc)}</div>
                    <div class="motorista">${occurrenceSubtitle(oc)}</div>
                </div>
                <div class="occurrence-flags">
                    ${fatigueCount}
                    ${note}
                    ${occurrenceBadge(oc)}
                </div>
            </div>
            ${compact ? "" : `
                <div class="timer-track">
                    <div class="timer-fill" style="width:${percent}%"></div>
                </div>
                <div class="timer-row">
                    <span>${statusLabel(oc.etapa)}</span>
                    <strong>${timer}</strong>
                </div>
            `}
            <div class="occurrence-meta">
                <span>${oc.idade || "-"}</span>
                <span>${oc.atualizado_em || "-"}</span>
            </div>
            ${oc.ultima_observacao && !compact ? `<p class="last-note">${escapeHtml(oc.ultima_observacao)}</p>` : ""}
        </article>
    `;
}

function renderDashboard(data) {
    if (qs("#metric-online")) qs("#metric-online").textContent = data.operadores_online;
    if (qs("#metric-offline")) qs("#metric-offline").textContent = data.operadores_offline;
    if (qs("#metric-tratados")) qs("#metric-tratados").textContent = data.alertas_tratados_hoje;
    if (qs("#metric-fadigas")) qs("#metric-fadigas").textContent = data.ocorrencias_abertas.length;

    const resumo = qs("#ocorrencias-resumo");
    if (resumo) {
        resumo.innerHTML = data.ocorrencias_abertas.length
            ? data.ocorrencias_abertas.map((oc) => occurrenceCard(oc, true)).join("")
            : `<div class="empty-block">Nenhuma ocorrência aberta.</div>`;
    }

    renderOperators(data);
    renderTurnos(data);
}

function filteredOccurrences(ocorrencias) {
    if (state.filter === "todas") return ocorrencias;
    return ocorrencias.filter((oc) => oc.status === state.filter);
}

function renderOperation(data) {
    const lista = qs("#ocorrencias-operacao");
    if (!lista) return;

    const ocorrencias = filteredOccurrences(data.ocorrencias_abertas.concat([]));
    lista.innerHTML = ocorrencias.length
        ? ocorrencias.map((oc) => occurrenceCard(oc, false)).join("")
        : `<div class="empty-block">Nenhuma ocorrência nesta visão.</div>`;

    lista.querySelectorAll(".occurrence-card").forEach((card) => {
        card.addEventListener("click", () => {
            state.selectedOccurrenceId = Number(card.dataset.occurrenceId);
            renderOperation(data);
            renderDetail(data);
        });
    });

    if (!state.selectedOccurrenceId && ocorrencias.length) {
        state.selectedOccurrenceId = ocorrencias[0].id;
    }

    renderDetail(data);
}

function renderDetail(data) {
    const box = qs("#detail-box");
    if (!box) return;

    const oc = data.ocorrencias_abertas.find((item) => item.id === state.selectedOccurrenceId);
    if (!oc) {
        box.className = "detail-box empty-detail";
        box.innerHTML = `
            <div>
                <strong>Nenhuma ocorrência selecionada</strong>
                <span>A fila será atualizada automaticamente.</span>
            </div>
        `;
        return;
    }

    const dadosFadiga = isFadiga(oc)
        ? `
            <div class="detail-row"><span>Placa</span><strong>${oc.placa || "-"}</strong></div>
            <div class="detail-row"><span>Motorista</span><strong>${oc.motorista || "-"}</strong></div>
            <div class="detail-row"><span>Alertas de fadiga</span><strong>${oc.alertas_qtd || 1}</strong></div>
        `
        : "";
    const notas = Array.isArray(oc.notas) ? oc.notas : [];
    const notasHtml = notas.length
        ? `
            <div class="saved-notes">
                <strong>Observações salvas</strong>
                ${notas.map((nota) => `
                    <article>
                        <span>${escapeHtml(nota.operador)} / ${escapeHtml(nota.criado_em)}</span>
                        <p>${escapeHtml(nota.mensagem)}</p>
                    </article>
                `).join("")}
            </div>
        `
        : "";

    box.className = "detail-box";
    box.innerHTML = `
        <div class="detail-title">
            <div>
                <div class="plate">${occurrenceTitle(oc)}</div>
                <div class="motorista">${occurrenceSubtitle(oc)}</div>
            </div>
            ${occurrenceBadge(oc)}
        </div>

        <div class="detail-grid">
            ${dadosFadiga}
            <div class="detail-row"><span>Tratando</span><strong>${oc.operador || "-"}</strong></div>
            <div class="detail-row"><span>Etapa</span><strong>${statusLabel(oc.etapa)}</strong></div>
            <div class="detail-row"><span>Contato</span><strong>${statusLabel(oc.contato_status)}</strong></div>
            <div class="detail-row"><span>Parada</span><strong>${statusLabel(oc.parada_status)}</strong></div>
            <div class="detail-row"><span>Timer</span><strong>${oc.timer_restante || "-"}</strong></div>
            <div class="detail-row"><span>Observações</span><strong>${oc.observacoes_qtd || 0}</strong></div>
        </div>

        <div class="detail-actions">
            <button class="primary" data-action="contato">Contato feito</button>
            <button class="warning" data-action="sem-contato">Sem contato</button>
            <button class="success" data-action="aceitou">Aceitou parar</button>
            <button class="danger" data-action="recusou">Recusou</button>
            <button data-action="timer10">Timer 10 min</button>
            <button data-action="finalizar">Finalizar</button>
        </div>

        <div class="note-compose">
            <label>
                Observação / anexo
                <textarea id="occurrence-note" rows="4" placeholder="Adicione observações, combinado, pendência ou anexo textual."></textarea>
            </label>
            <button class="primary-button" id="send-occurrence-note">Anexar observação</button>
            ${notasHtml}
        </div>
    `;

    box.querySelectorAll("button[data-action]").forEach((button) => {
        button.addEventListener("click", () => handleOccurrenceAction(oc.id, button.dataset.action));
    });

    const noteButton = qs("#send-occurrence-note");
    if (noteButton) noteButton.addEventListener("click", () => sendOccurrenceNote(oc.id));

    const noteField = qs("#occurrence-note");
    if (noteField) {
        noteField.value = state.occurrenceDrafts[oc.id] || "";
        noteField.addEventListener("input", () => {
            state.occurrenceDrafts[oc.id] = noteField.value;
        });
    }
}

async function sendOccurrenceNote(id) {
    const note = qs("#occurrence-note");
    if (!note || !note.value.trim()) return;

    const response = await fetch(`/api/ocorrencias/${id}/notas`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({operador: DEFAULT_OPERATOR, mensagem: note.value.trim()}),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok || !data.ok) {
        note.focus();
        return;
    }

    delete state.occurrenceDrafts[id];
    note.value = "";
    await refreshAll();
}

async function handleOccurrenceAction(id, action) {
    if (action === "timer10") {
        await fetch(`/api/ocorrencias/${id}/timer`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({minutos: 10}),
        });
        return refreshAll();
    }

    const payloads = {
        contato: {status: "EM_CONTATO", etapa: "CONTATO_FEITO", contato_status: "CONTATO_FEITO"},
        "sem-contato": {status: "EM_CONTATO", etapa: "SEM_CONTATO", contato_status: "SEM_CONTATO"},
        aceitou: {status: "EM_ACOMPANHAMENTO", etapa: "ACOMPANHAMENTO", parada_status: "ACEITOU_PARAR"},
        recusou: {status: "EM_ACOMPANHAMENTO", etapa: "ACOMPANHAMENTO", parada_status: "RECUSOU_PARAR"},
        finalizar: {status: "FINALIZADA", etapa: "FINALIZADA"},
    };

    await fetch(`/api/ocorrencias/${id}`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payloads[action] || {}),
    });

    return refreshAll();
}

function pendingCard(item) {
    const note = Number(item.observacoes_qtd || 0) > 0 ? `<span class="note-pill">Obs. ${item.observacoes_qtd}</span>` : "";
    return `
        <article class="handover-card" data-ref="OCORRENCIA:${item.id}">
            <strong>${occurrenceTitle(item)}</strong>
            <span>Tratando: ${item.operador || "-"} / ${statusLabel(item.status)}</span>
            ${note}
        </article>
    `;
}

function renderTrocaTurno() {
    if (!qs("#handover-pending")) return;

    const data = state.trocaTurno || {ocorrencias: [], notas: []};
    qs("#handover-pending").innerHTML = data.ocorrencias.length
        ? data.ocorrencias.map(pendingCard).join("")
        : `<div class="empty-block">Nenhuma ocorrência aberta para repasse.</div>`;

    const refSelect = qs("#handover-reference");
    if (refSelect) {
        refSelect.innerHTML = `<option value="GERAL">Geral</option>` + data.ocorrencias
            .map((item) => `<option value="OCORRENCIA:${item.id}">${occurrenceTitle(item)} / ${item.operador || "-"}</option>`)
            .join("");
        if ([...refSelect.options].some((option) => option.value === state.handoverReference)) {
            refSelect.value = state.handoverReference;
        }
        refSelect.onchange = () => {
            state.handoverReference = refSelect.value || "GERAL";
        };
    }

    qs("#handover-pending").querySelectorAll(".handover-card").forEach((card) => {
        card.addEventListener("click", () => {
            state.handoverReference = card.dataset.ref || "GERAL";
            if (refSelect) refSelect.value = state.handoverReference;
        });
    });

    const chat = qs("#handover-chat");
    if (chat) {
        chat.innerHTML = data.notas.length
            ? data.notas.map((nota) => `
                <article class="chat-note ${nota.operador === DEFAULT_OPERATOR ? "mine" : ""}">
                    <div class="chat-note-head">
                        <div>
                            <strong>${escapeHtml(nota.operador)}</strong>
                            <span>${escapeHtml(nota.referencia_tipo)}${nota.referencia_id ? " #" + nota.referencia_id : ""}</span>
                        </div>
                        <button class="delete-note" data-delete-note="${nota.id}" title="Apagar mensagem">Apagar</button>
                    </div>
                    <p>${escapeHtml(nota.mensagem)}</p>
                    <small>${escapeHtml(nota.criado_em)}</small>
                </article>
            `).join("")
            : `<div class="empty-block">Nenhuma observação anexada.</div>`;
        chat.querySelectorAll("[data-delete-note]").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                deleteTurnoNote(button.dataset.deleteNote);
            });
        });
        chat.scrollTop = chat.scrollHeight;
    }
}

async function loadTrocaTurno() {
    if (!qs("#handover-pending")) return;

    const response = await fetch("/api/troca-turno", {cache: "no-store"});
    state.trocaTurno = await response.json();

    const operator = qs("#handover-operator");
    if (operator && !operator.value) operator.value = DEFAULT_OPERATOR;
    const message = qs("#handover-message");
    if (message && !message.value && state.handoverDraft) message.value = state.handoverDraft;

    renderTrocaTurno();
}

async function deleteTurnoNote(id) {
    if (!id) return;

    const response = await fetch(`/api/troca-turno/notas/${id}`, {
        method: "DELETE",
        headers: {"Content-Type": "application/json"},
    });

    if (response.ok) await loadTrocaTurno();
}

async function sendTurnoNote() {
    const operator = qs("#handover-operator");
    const ref = qs("#handover-reference");
    const message = qs("#handover-message");
    if (!message || !message.value.trim()) return;

    const [referenciaTipo, referenciaId] = String(ref.value || "GERAL").split(":");
    const response = await fetch("/api/troca-turno/notas", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            operador: operator.value || DEFAULT_OPERATOR,
            referencia_tipo: referenciaTipo,
            referencia_id: referenciaId ? Number(referenciaId) : null,
            mensagem: message.value,
        }),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok || !data.ok) {
        message.focus();
        return;
    }

    state.handoverDraft = "";
    message.value = "";
    await loadTrocaTurno();
}

async function createOccurrence(payload, noteText) {
    const response = await fetch("/api/ocorrencias", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok || !data.ok || !data.ocorrencia_id) {
        return false;
    }

    if (noteText && data.ocorrencia_id) {
        const noteResponse = await fetch(`/api/ocorrencias/${data.ocorrencia_id}/notas`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({operador: payload.operador || DEFAULT_OPERATOR, mensagem: noteText}),
        });
        const noteData = await noteResponse.json().catch(() => ({}));
        if (!noteResponse.ok || !noteData.ok) {
            return false;
        }
    }

    state.selectedOccurrenceId = data.ocorrencia_id;
    await refreshAll();
    return true;
}

async function createUserOccurrence(event) {
    event.preventDefault();
    const type = qs("#user-occurrence-type");
    const status = qs("#user-occurrence-status");
    const note = qs("#user-occurrence-note");
    const noteText = note.value.trim();

    const created = await createOccurrence({
        tipo: type.value,
        operador: DEFAULT_OPERATOR,
        maquina: "PAINEL",
        status: status.value,
        etapa: "ANEXADA_PELO_OPERADOR",
        placa: "-",
        motorista: "Nao informado",
        observacao: noteText,
    }, noteText);

    if (created) note.value = "";
}

async function createHandoverOccurrence(event) {
    event.preventDefault();
    const type = qs("#handover-new-type");
    const owner = qs("#handover-new-owner");
    const message = qs("#handover-new-message");
    const noteText = message.value.trim();

    const created = await createOccurrence({
        tipo: type.value,
        operador: (owner.value || DEFAULT_OPERATOR).trim().toLowerCase(),
        maquina: "TROCA_TURNO",
        status: "ABERTA",
        etapa: "ANEXADA_NO_REPASSE",
        placa: "-",
        motorista: "Nao informado",
        observacao: noteText,
    }, noteText);

    if (created) message.value = "";
}

async function loadData() {
    try {
        const response = await fetch("/api/dashboard", {cache: "no-store"});
        const data = await response.json();
        state.lastData = data;

        const status = qs("#sidebar-status");
        if (status) status.textContent = `Atualizado ${new Date().toLocaleTimeString("pt-BR")}`;

        renderDashboard(data);
        renderOperation(data);
    } catch (error) {
        const status = qs("#sidebar-status");
        if (status) status.textContent = "Sem conexão";
    }
}

function bindButtons() {
    const sendNote = qs("#handover-send");
    const userForm = qs("#user-occurrence-form");
    const handoverForm = qs("#handover-occurrence-form");
    const handoverMessage = qs("#handover-message");

    if (sendNote) sendNote.addEventListener("click", sendTurnoNote);
    if (userForm) userForm.addEventListener("submit", createUserOccurrence);
    if (handoverForm) handoverForm.addEventListener("submit", createHandoverOccurrence);
    if (handoverMessage) {
        handoverMessage.addEventListener("input", () => {
            state.handoverDraft = handoverMessage.value;
        });
    }

    document.querySelectorAll(".segment").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            state.filter = button.dataset.filter;
            if (state.lastData) renderOperation(state.lastData);
        });
    });
}

async function refreshAll() {
    await loadData();
    await loadTrocaTurno();
}

setClock();
bindButtons();
refreshAll();
setInterval(setClock, 1000);
setInterval(refreshAll, 2500);
