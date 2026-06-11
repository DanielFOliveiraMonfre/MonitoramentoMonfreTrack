const state = {
    selectedOccurrenceId: null,
    selectedOperator: null,
    filter: "todas",
    lastData: null,
    trocaTurno: null,
    occurrenceDrafts: {},
    handoverDraft: "",
    handoverReference: "GERAL",
    notifiedTimers: new Set(),
    detailClosed: false,
    occurrenceScale: "normal",
    historyHours: Number(localStorage.getItem("monfretrack-history-hours") || 9),
};

const currentUser = window.MONFRETRACK_USER || {nome: "daniel.oliveira", admin: false};
const DEFAULT_OPERATOR = currentUser.nome || "daniel.oliveira";
const qs = (selector) => document.querySelector(selector);

const ADDITIONAL_FIELD_LABELS = {
    contrato_programacao: "Contrato da Programação de Carga",
    programacao_carga: "Programação de Carga",
    tempo_direcao_continua: "Tempo de direção contínua",
    tempo_margem: "Tempo de margem",
    tempo_estimado_destino: "Tempo estimado para o destino",
    motorista_sinal_fadiga: "Motorista apresenta sinal de fadiga",
    cobertura_celular: "Celular está com área de cobertura",
    motorista_atendeu: "Motorista atendeu a ligação",
    mensagem_sirene: "Foi enviado mensagens e sirene",
    motorista_aceitou_parar: "Motorista aceitou parar",
    programacao_acionada: "Setor Programação foi acionado",
    programador: "Qual programador nos atendeu",
};

function isEditingOccurrenceNote() {
    return document.activeElement && document.activeElement.id === "occurrence-note";
}

function setClock() {
    const el = qs("#clock");
    if (el) el.textContent = new Date().toLocaleTimeString("pt-BR");

    const today = qs("#metric-date-today");
    if (today) today.textContent = new Date().toLocaleDateString("pt-BR");
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

function occurrenceType(oc) {
    return String(oc.tipo || oc.evento || "OCORRENCIA").trim().toUpperCase();
}

function valueOrNA(value) {
    const text = String(value ?? "").trim();
    return text || "N/A";
}

function operatorName(oc) {
    return valueOrNA(oc.operador_nome || oc.operador);
}

function isFinalizedOccurrence(oc) {
    return ["FINALIZADA", "CANCELADA"].includes(String(oc.status || "").toUpperCase());
}

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function truncateText(value, max = 34) {
    const text = String(value || "").trim();
    if (text.length <= max) return text;
    return `${text.slice(0, max).trim()}...`;
}

function parseLocalDate(value) {
    if (!value) return null;
    const normalized = String(value).replace(" ", "T");
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
}

function formatDateTime(value) {
    const date = parseLocalDate(value);
    if (!date) return value || "-";
    return date.toLocaleString("pt-BR");
}

function formatTimeOnly(value) {
    const date = parseLocalDate(value);
    if (!date) return "--:--";
    return date.toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"});
}

function occurrenceVisual(oc) {
    if (isFinalizedOccurrence(oc)) return {label: "FINALIZADA", cls: "finalizada"};
    if (oc.alerta_atrasado) return {label: "ALERTA", cls: "alerta"};
    if (String(oc.contato_status || "").toUpperCase() === "SEM_CONTATO") return {label: "SEM CONTATO", cls: "sem-contato"};
    if (String(oc.status || "").toUpperCase() === "EM_ACOMPANHAMENTO") return {label: "ACOMPANHAMENTO", cls: "acompanhamento"};
    return {label: "AGUARDANDO CONTATO", cls: "aguardando"};
}

function rolePill(op) {
    return `<span class="role-pill ${op.admin ? "admin" : "user"}">${op.admin ? "Admin" : "Usuario"}</span>`;
}

function operatorCard(op) {
    const selected = state.selectedOperator === op.operador ? "selected" : "";
    const onlineText = op.online ? "Online" : "Offline";
    const tempo = op.online ? op.tempo_aberto : "-";
    const fadigas = Number(op.fadigas_abertas || 0);
    const ocorrencias = Number(op.ocorrencias_abertas || 0);
    const priorityClass = [
        op.online ? "op-online" : "",
        ocorrencias ? "op-occurrence" : "",
        fadigas ? "op-fatigue" : "",
    ].filter(Boolean).join(" ");
    const priorityBadges = [
        op.online ? `<span class="operator-badge active">ATIVO</span>` : "",
        ocorrencias ? `<span class="operator-badge occurrence">${ocorrencias} OCORR.</span>` : "",
        fadigas ? `<span class="operator-badge fatigue">${fadigas} FADIGA</span>` : "",
    ].join("");

    return `
        <article class="operator-card ${selected} ${priorityClass}" data-operator="${op.operador}">
            <div class="operator-card-head">
                <div>
                    <strong>${op.operador}</strong>
                    <span>${op.turno || "-"} / ${op.maquina || "-"}</span>
                </div>
                <span class="status-pill ${statusClass(op.status, op.online)}">${onlineText}</span>
            </div>
            ${priorityBadges ? `<div class="operator-priority-badges">${priorityBadges}</div>` : ""}
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
    const ordem = ["T1", "T2", "T3", "ADM"];
    const grupos = ordem
        .map((turno) => ({
            turno,
            operadores: operadores.filter((op) => (op.turno || "T3") === turno),
        }))
        .filter((grupo) => grupo.operadores.length);

    grid.innerHTML = grupos.length
        ? grupos.map((grupo) => `
            <section class="operator-turno-group">
                <div class="operator-turno-head">
                    <strong>${grupo.turno}</strong>
                    <span>${grupo.operadores.filter((op) => op.online).length}/${grupo.operadores.length} online</span>
                </div>
                <div class="operator-turno-grid">
                    ${grupo.operadores.map(operatorCard).join("")}
                </div>
            </section>
        `).join("")
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
            const ocorrencias = (data.ocorrencias_operacao || data.ocorrencias_abertas || []).filter((oc) => oc.operador === button.dataset.operatorFilter);
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

function predominanceCard(turno) {
    const tipos = Array.isArray(turno.alertas_por_tipo) ? turno.alertas_por_tipo : [];
    const predominante = turno.alerta_predominante && turno.alerta_predominante !== "-"
        ? statusLabel(turno.alerta_predominante)
        : "-";
    const total = Number(turno.alerta_predominante_qtd || 0);
    const chips = tipos.length
        ? tipos.slice(0, 4).map((item) => `
            <span>${statusLabel(item.tipo)} <strong>${item.total}</strong></span>
        `).join("")
        : `<span>Sem alertas tratados</span>`;

    return `
        <article class="predominance-card">
            <div class="predominance-head">
                <strong>${turno.turno}</strong>
                <span>Alerta predominante</span>
            </div>
            <b>${predominante}</b>
            <small>${total} registros hoje</small>
            <div class="predominance-types">${chips}</div>
        </article>
    `;
}

function renderPredominance(data) {
    const grid = qs("#predominance-grid");
    if (!grid) return;

    grid.innerHTML = (data.turnos || []).length
        ? data.turnos.map(predominanceCard).join("")
        : `<div class="empty-block">Nenhum turno carregado.</div>`;
}

function occurrenceBadge(oc) {
    const visual = occurrenceVisual(oc);
    return `<span class="occurrence-state ${visual.cls}">${visual.label}</span>`;
}

function legacyOccurrenceTitle(oc) {
    return "OCORRÊNCIA DE FADIGA";
}

function legacyOccurrenceSubtitle(oc) {
    if (isFadiga(oc)) {
        return `Tratando: ${oc.operador || "-"} / ${oc.maquina || "-"}`;
    }

    return `Tratando: ${oc.operador || "-"} / ${oc.maquina || "-"}`;
}

function occurrenceTitle(oc) {
    const tipo = occurrenceType(oc);
    if (tipo === "FADIGA") return "OCORRÊNCIA DE FADIGA";
    if (tipo === "PARADA PREVENTIVA") return "PARADA PREVENTIVA";
    return statusLabel(tipo);
}

function occurrenceSubtitle(oc) {
    return `Registrado por: ${operatorName(oc)}${oc.operador_email && oc.operador_email !== "N/A" ? " / " + oc.operador_email : ""}`;
}

function occurrenceCard(oc, compact = false) {
    const selected = state.selectedOccurrenceId === oc.id ? "selected" : "";
    const finalizada = isFinalizedOccurrence(oc);
    const visual = occurrenceVisual(oc);
    const timer = oc.timer_restante || "-";
    const percent = oc.timer_percentual || 0;
    const note = Number(oc.observacoes_qtd || 0) > 0
        ? `<span class="note-pill" title="Possui observações">Obs. ${oc.observacoes_qtd}</span>`
        : "";
    const fatigueCount = isFadiga(oc) && Number(oc.alertas_qtd || 1) > 1
        ? `<span class="fatigue-count" title="Alertas de fadiga agrupados">x${oc.alertas_qtd}</span>`
        : "";
    const noteText = truncateText(oc.ultima_observacao || oc.observacao || "Sem observações anexadas.", 38);
    const cardAction = finalizada ? "Ver detalhes" : "Abrir detalhes";
    const timerBlock = compact || finalizada ? "" : `
        <div class="timer-track">
            <div class="timer-fill" style="width:${percent}%"></div>
        </div>
    `;
    const secondaryAction = finalizada
        ? `<span class="done-inline">✓ Finalizada</span>`
        : visual.cls === "aguardando"
            ? `<button class="card-action secondary" data-card-action="details">Acompanhar</button>`
            : `<button class="card-action secondary" data-card-action="finalizar">Finalizar</button>`;

    const evento = occurrenceType(oc);
    const responsavel = operatorName(oc);

    return `
        <article class="occurrence-card ${selected} ${visual.cls} type-${evento.replaceAll(" ", "-").toLowerCase()}" data-occurrence-id="${oc.id}" draggable="${compact || finalizada ? "false" : "true"}">
            <div class="occurrence-top">
                <div>
                    ${occurrenceBadge(oc)}
                    <div class="plate">${occurrenceTitle(oc)}</div>
                </div>
                <div class="occurrence-flags">
                    ${fatigueCount}
                    ${note}
                </div>
            </div>
            <div class="card-identity">
                <strong>${escapeHtml(oc.placa || "-")}</strong>
                <span>${escapeHtml(oc.motorista || "Motorista não informado")}</span>
            </div>
            <div class="card-mid">
                <div>
                    <span>Responsável</span>
                    <strong>${escapeHtml(responsavel)}</strong>
                </div>
                <div class="active-time ${visual.cls}">
                    <strong>${oc.tempo_ocorrencia || oc.idade || "-"}</strong>
                    <span>tempo ativo</span>
                </div>
            </div>
            <div class="occurrence-event-line">
                <span>${escapeHtml(statusLabel(evento))}</span>
                <small>${escapeHtml(formatDateTime(oc.data_hora || oc.horario_alerta || oc.criado_em))}</small>
            </div>
            <p class="last-note" title="${escapeHtml(oc.ultima_observacao || oc.observacao || oc.observacao_inicial || "")}">${escapeHtml(noteText)}</p>
            ${timerBlock}
            <div class="card-actions">
                <button class="card-action" data-card-action="details">${cardAction}</button>
                ${secondaryAction}
            </div>
            <div class="occurrence-meta">
                <span>${formatTimeOnly(oc.horario_alerta || oc.criado_em)}</span>
                <span>${formatDateTime(oc.atualizado_em)}</span>
            </div>
        </article>
    `;
}

function renderDashboard(data) {
    if (qs("#metric-online")) qs("#metric-online").textContent = data.operadores_online;
    if (qs("#metric-offline")) qs("#metric-offline").textContent = data.operadores_offline;
    if (qs("#metric-tratados")) qs("#metric-tratados").textContent = data.alertas_tratados_hoje;
    if (qs("#metric-fadigas")) qs("#metric-fadigas").textContent = data.ocorrencias_abertas.filter(isFadiga).length;

    const resumo = qs("#ocorrencias-resumo");
    if (resumo) {
        resumo.innerHTML = data.ocorrencias_abertas.length
            ? data.ocorrencias_abertas.map((oc) => occurrenceCard(oc, true)).join("")
            : `<div class="empty-block">Nenhuma ocorrência aberta.</div>`;
    }

    renderOperators(data);
    renderTurnos(data);
    renderPredominance(data);
}

function filteredOccurrences(ocorrencias) {
    if (state.filter === "todas") return ocorrencias;
    if (state.filter === "ALERTA") return ocorrencias.filter((oc) => oc.alerta_atrasado && !isFinalizedOccurrence(oc));
    return ocorrencias.filter((oc) => oc.status === state.filter);
}

function renderOccurrenceKpis(data) {
    const abertas = data.ocorrencias_abertas || [];
    const all = data.ocorrencias_operacao || abertas;
    const emAcompanhamento = abertas.filter((oc) => oc.status === "EM_ACOMPANHAMENTO").length;
    const semContato = abertas.filter((oc) => String(oc.contato_status || "").toUpperCase() === "SEM_CONTATO").length;
    const alerta = abertas.filter((oc) => oc.alerta_atrasado).length;

    if (qs("#kpi-oc-abertas")) qs("#kpi-oc-abertas").textContent = abertas.length;
    if (qs("#kpi-oc-alerta")) qs("#kpi-oc-alerta").textContent = alerta;
    if (qs("#kpi-oc-acompanhamento")) qs("#kpi-oc-acompanhamento").textContent = emAcompanhamento;
    if (qs("#kpi-oc-sem-contato")) qs("#kpi-oc-sem-contato").textContent = semContato;

    document.querySelectorAll(".segment").forEach((button) => {
        const filter = button.dataset.filter;
        const count = filter === "todas" ? all.length :
            filter === "ALERTA" ? alerta :
            all.filter((oc) => oc.status === filter).length;
        const label = button.textContent.replace(/\s+\d+$/, "").trim();
        button.innerHTML = `${label} <span>${count}</span>`;
    });
}

function legacyRenderOperation(data) {
    const lista = qs("#ocorrencias-operacao");
    if (!lista) return;

    renderOccurrenceKpis(data);

    const base = data.ocorrencias_operacao || data.ocorrencias_abertas || [];
    const ocorrencias = filteredOccurrences(base.concat([]));
    lista.innerHTML = ocorrencias.length
        ? ocorrencias.map((oc) => occurrenceCard(oc, false)).join("")
        : `<div class="empty-block">Nenhuma ocorrência nesta visão.</div>`;

    lista.querySelectorAll(".occurrence-card").forEach((card) => {
        card.addEventListener("click", (event) => {
            if (event.target.dataset.cardAction === "finalizar") {
                event.stopPropagation();
                handleOccurrenceAction(Number(card.dataset.occurrenceId), "finalizar");
                return;
            }

            state.selectedOccurrenceId = Number(card.dataset.occurrenceId);
            state.detailClosed = false;
            renderOperation(data);
            renderDetail(data);
        });
    });

    if (state.selectedOccurrenceId && !ocorrencias.some((oc) => oc.id === state.selectedOccurrenceId)) {
        state.selectedOccurrenceId = null;
    }

    if (!state.selectedOccurrenceId && ocorrencias.length && !state.detailClosed) {
        state.selectedOccurrenceId = ocorrencias[0].id;
    }

    if (!isEditingOccurrenceNote()) {
        renderDetail(data);
    }
}

function legacyRenderDetail(data) {
    const box = qs("#detail-box");
    if (!box) return;

    const base = data.ocorrencias_operacao || data.ocorrencias_abertas || [];
    const oc = base.find((item) => item.id === state.selectedOccurrenceId);
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

    const dadosFadiga = `
        <div class="detail-row featured"><span>Placa</span><strong>${oc.placa || "-"}</strong></div>
        <div class="detail-row featured"><span>Motorista</span><strong>${oc.motorista || "-"}</strong></div>
        <div class="detail-row"><span>Alertas de fadiga</span><strong>${oc.alertas_qtd || 1}</strong></div>
    `;
    const visual = occurrenceVisual(oc);
    const notas = Array.isArray(oc.notas) ? oc.notas : [];
    const notasHtml = notas.length
        ? `
            <div class="saved-notes">
                <strong>Observações salvas</strong>
                ${notas.map((nota) => `
                    <article>
                        <span>${escapeHtml(nota.operador)} / ${escapeHtml(formatDateTime(nota.criado_em))}</span>
                        <p>${escapeHtml(nota.mensagem)}</p>
                    </article>
                `).join("")}
            </div>
        `
        : "";
    const finalizada = isFinalizedOccurrence(oc);
    const timeline = [
        {time: oc.criado_em, text: "Primeiro alerta de fadiga", cls: "info"},
        Number(oc.alertas_qtd || 1) > 1 ? {time: oc.ultimo_alerta_em || oc.atualizado_em, text: `${oc.alertas_qtd} alertas de fadiga agrupados`, cls: "info"} : null,
        oc.contato_status && oc.contato_status !== "PENDENTE" ? {time: oc.atualizado_em, text: statusLabel(oc.contato_status), cls: "warn"} : null,
        oc.parada_status && oc.parada_status !== "PENDENTE" ? {time: oc.atualizado_em, text: statusLabel(oc.parada_status), cls: "ok"} : null,
        finalizada ? {time: oc.finalizado_em || oc.atualizado_em, text: "Ocorrência finalizada", cls: "ok"} : null,
    ].filter(Boolean);
    const timelineHtml = timeline.length ? `
        <div class="timeline">
            <strong>Linha do tempo</strong>
            ${timeline.map((item) => `
                <div class="timeline-item ${item.cls}">
                    <span>${formatTimeOnly(item.time)}</span>
                    <p>${escapeHtml(item.text)}</p>
                </div>
            `).join("")}
        </div>
    ` : "";
    const timerValue = Math.max(5, Math.min(30, Number(oc.timer_minutos || 10)));
    const timerDetail = finalizada ? "" : `
        <div class="detail-row"><span>Timer</span><strong>${oc.timer_restante || "-"}</strong></div>
    `;
    const actionsHtml = finalizada ? `
        <div class="finalized-banner">
            <strong>Ocorrência finalizada</strong>
            <span>Histórico preservado até ${oc.finalizado_em || oc.atualizado_em || "-"}</span>
        </div>
    ` : `
        <div class="detail-actions">
            <button class="primary" data-action="contato">Contato feito</button>
            <button class="warning" data-action="sem-contato">Sem contato</button>
            <button class="success" data-action="aceitou">Aceitou parar</button>
            <button class="danger" data-action="recusou">Recusou</button>
            <button data-action="finalizar">Finalizar</button>
        </div>

        <div class="timer-picker">
            <div>
                <span>Timer de parada</span>
                <strong id="timer-minutes-label">${timerValue} min</strong>
            </div>
            <input id="timer-minutes" type="range" min="5" max="30" step="1" value="${timerValue}">
            <button class="primary-button" data-action="timer">Iniciar timer</button>
        </div>
    `;
    const adminDeleteHtml = currentUser.admin ? `
        <div class="admin-danger-zone">
            <div>
                <strong>Admin</strong>
                <span>Apaga esta ocorrência e as observações anexadas.</span>
            </div>
            <button class="danger-button" data-action="delete-occurrence">Apagar ocorrência</button>
        </div>
    ` : "";

    box.className = "detail-box";
    box.innerHTML = `
        <div class="detail-title">
            <div>
                <div class="plate">${occurrenceTitle(oc)}</div>
                <div class="motorista">${occurrenceSubtitle(oc)}</div>
            </div>
            <button class="drawer-close" type="button" data-action="close-detail">×</button>
        </div>
        <div class="detail-state-line">
            ${occurrenceBadge(oc)}
            <span>${oc.tempo_ocorrencia || oc.idade || "-"} de ocorrência</span>
        </div>

        <div class="detail-grid">
            ${dadosFadiga}
            <div class="detail-row"><span>Tratando</span><strong>${oc.operador || "-"}</strong></div>
            <div class="detail-row"><span>Etapa</span><strong>${statusLabel(oc.etapa)}</strong></div>
            <div class="detail-row"><span>Contato</span><strong>${statusLabel(oc.contato_status)}</strong></div>
            <div class="detail-row"><span>Parada</span><strong>${statusLabel(oc.parada_status)}</strong></div>
            ${timerDetail}
            <div class="detail-row"><span>Observações</span><strong>${oc.observacoes_qtd || 0}</strong></div>
            <div class="detail-row"><span>Aberta em</span><strong>${formatDateTime(oc.criado_em)}</strong></div>
            <div class="detail-row"><span>Finalizado em</span><strong>${formatDateTime(oc.finalizado_em) || "-"}</strong></div>
        </div>

        ${timelineHtml}

        ${actionsHtml}
        ${adminDeleteHtml}

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

    const timerRange = qs("#timer-minutes");
    const timerLabel = qs("#timer-minutes-label");
    if (timerRange && timerLabel) {
        timerRange.addEventListener("input", () => {
            timerLabel.textContent = `${timerRange.value} min`;
        });
    }

    const noteField = qs("#occurrence-note");
    if (noteField) {
        noteField.value = state.occurrenceDrafts[oc.id] || "";
        noteField.addEventListener("input", () => {
            state.occurrenceDrafts[oc.id] = noteField.value;
        });
    }
}

function openOccurrenceModal(id, data) {
    state.selectedOccurrenceId = Number(id);
    state.detailClosed = false;
    renderDetail(data || state.lastData || {});
    const modal = qs("#occurrence-modal");
    if (modal) {
        modal.hidden = false;
        modal.setAttribute("aria-hidden", "false");
    }
}

function closeOccurrenceModal() {
    state.selectedOccurrenceId = null;
    state.detailClosed = true;
    const modal = qs("#occurrence-modal");
    if (modal) {
        modal.hidden = true;
        modal.setAttribute("aria-hidden", "true");
    }
    if (state.lastData) renderOperation(state.lastData);
}

function additionalFieldsHtml(oc) {
    const campos = oc.campos_adicionais && typeof oc.campos_adicionais === "object" ? oc.campos_adicionais : {};
    return Object.entries(ADDITIONAL_FIELD_LABELS).map(([key, label]) => `
        <div class="detail-row">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(valueOrNA(campos[key]))}</strong>
        </div>
    `).join("");
}

function timelineHtml(oc) {
    const timeline = Array.isArray(oc.timeline) && oc.timeline.length
        ? oc.timeline
        : [
            {criado_em: oc.data_hora || oc.criado_em, mensagem: `${occurrenceTitle(oc)} registrada`, tipo: "CRIACAO"},
            isFinalizedOccurrence(oc) ? {criado_em: oc.finalizado_em || oc.atualizado_em, mensagem: "Ocorrência finalizada", tipo: "FINALIZADA"} : null,
        ].filter(Boolean);

    return `
        <div class="timeline">
            <strong>Linha do tempo</strong>
            ${timeline.map((item) => `
                <div class="timeline-item ${String(item.tipo || "").toLowerCase().includes("final") ? "ok" : "info"}">
                    <span>${formatTimeOnly(item.criado_em)}</span>
                    <p>${escapeHtml(item.mensagem || "-")}</p>
                </div>
            `).join("")}
        </div>
    `;
}

function bindOccurrenceDrag(lista) {
    let dragging = null;
    lista.querySelectorAll(".occurrence-card[draggable='true']").forEach((card) => {
        card.addEventListener("dragstart", (event) => {
            dragging = card;
            card.classList.add("dragging");
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", card.dataset.occurrenceId);
        });
        card.addEventListener("dragend", () => {
            card.classList.remove("dragging");
            dragging = null;
            saveOccurrenceOrder(lista);
        });
        card.addEventListener("dragover", (event) => {
            event.preventDefault();
            const target = event.currentTarget;
            if (!dragging || dragging === target) return;
            const rect = target.getBoundingClientRect();
            const before = event.clientY < rect.top + rect.height / 2;
            lista.insertBefore(dragging, before ? target : target.nextSibling);
        });
    });
}

async function saveOccurrenceOrder(lista) {
    const ids = [...lista.querySelectorAll(".occurrence-card")]
        .map((card) => Number(card.dataset.occurrenceId))
        .filter(Boolean);
    if (!ids.length) return;
    await fetch("/api/ocorrencias/ordem", {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ids}),
    }).catch(() => {});
}

function renderOperation(data) {
    const lista = qs("#ocorrencias-operacao");
    if (!lista) return;

    renderOccurrenceKpis(data);

    const base = data.ocorrencias_operacao || data.ocorrencias_abertas || [];
    const ocorrencias = filteredOccurrences(base.concat([]));
    lista.innerHTML = ocorrencias.length
        ? ocorrencias.map((oc) => occurrenceCard(oc, false)).join("")
        : `<div class="empty-block">Nenhuma ocorrência nesta visão.</div>`;

    lista.querySelectorAll(".occurrence-card").forEach((card) => {
        card.addEventListener("click", (event) => {
            if (event.target.dataset.cardAction === "finalizar") {
                event.stopPropagation();
                handleOccurrenceAction(Number(card.dataset.occurrenceId), "finalizar");
                return;
            }
            openOccurrenceModal(Number(card.dataset.occurrenceId), data);
        });
    });
    bindOccurrenceDrag(lista);

    if (state.selectedOccurrenceId && !base.some((oc) => oc.id === state.selectedOccurrenceId)) {
        closeOccurrenceModal();
        return;
    }

    const modal = qs("#occurrence-modal");
    const modalOpen = modal && !modal.hidden;
    if (modalOpen && !isEditingOccurrenceNote()) {
        renderDetail(data);
    }
}

function renderDetail(data) {
    const box = qs("#detail-box");
    if (!box) return;

    const base = data.ocorrencias_operacao || data.ocorrencias_abertas || [];
    const oc = base.find((item) => item.id === state.selectedOccurrenceId);
    if (!oc) {
        box.className = "detail-box empty-detail";
        box.innerHTML = `<strong>Nenhuma ocorrência selecionada</strong>`;
        return;
    }

    const visual = occurrenceVisual(oc);
    const finalizada = isFinalizedOccurrence(oc);
    const notas = Array.isArray(oc.notas) ? oc.notas : [];
    const timerValue = Math.max(5, Math.min(30, Number(oc.timer_minutos || 10)));
    const obsInicial = valueOrNA(oc.observacao_inicial || oc.observacao);
    const timerDetail = finalizada ? "" : `
        <div class="detail-row"><span>Timer</span><strong>${escapeHtml(oc.timer_restante || "-")}</strong></div>
    `;
    const actionsHtml = finalizada ? `
        <div class="finalized-banner">
            <strong>Ocorrência finalizada</strong>
            <span>Histórico preservado até ${escapeHtml(formatDateTime(oc.finalizado_em || oc.atualizado_em || "-"))}</span>
        </div>
    ` : `
        <div class="detail-actions">
            <button class="primary" data-action="contato">Contato feito</button>
            <button class="warning" data-action="sem-contato">Sem contato</button>
            <button class="success" data-action="aceitou">Aceitou parar</button>
            <button class="danger" data-action="recusou">Recusou</button>
            <button data-action="finalizar">Finalizar</button>
        </div>
        <div class="timer-picker">
            <div>
                <span>Timer de parada</span>
                <strong id="timer-minutes-label">${timerValue} min</strong>
            </div>
            <input id="timer-minutes" type="range" min="5" max="30" step="1" value="${timerValue}">
            <button class="primary-button" data-action="timer">Iniciar timer</button>
        </div>
    `;
    const notasHtml = notas.length ? `
        <div class="saved-notes">
            <strong>Observações adicionais</strong>
            ${notas.map((nota) => `
                <article>
                    <span>${escapeHtml(nota.operador)} / ${escapeHtml(formatDateTime(nota.criado_em))}</span>
                    <p>${escapeHtml(nota.mensagem)}</p>
                </article>
            `).join("")}
        </div>
    ` : `<div class="saved-notes"><strong>Observações adicionais</strong><article><p>Sem observações adicionais.</p></article></div>`;
    const adminDeleteHtml = currentUser.admin ? `
        <div class="admin-danger-zone">
            <div>
                <strong>Admin</strong>
                <span>Apaga esta ocorrência e as observações anexadas.</span>
            </div>
            <button class="danger-button" data-action="delete-occurrence">Apagar ocorrência</button>
        </div>
    ` : "";

    box.className = "detail-box";
    box.innerHTML = `
        <div class="detail-title">
            <div>
                <div class="plate">${escapeHtml(occurrenceTitle(oc))}</div>
                <div class="motorista">${escapeHtml(occurrenceSubtitle(oc))}</div>
            </div>
        </div>
        <div class="detail-state-line">
            ${occurrenceBadge(oc)}
            <span>${escapeHtml(oc.tempo_ocorrencia || oc.idade || "-")} de ocorrência</span>
        </div>

        <div class="detail-grid modal-main-grid">
            <div class="detail-row featured"><span>Evento</span><strong>${escapeHtml(statusLabel(occurrenceType(oc)))}</strong></div>
            <div class="detail-row featured"><span>Placa</span><strong>${escapeHtml(oc.placa || "-")}</strong></div>
            <div class="detail-row featured wide"><span>Motorista</span><strong>${escapeHtml(oc.motorista || "N/A")}</strong></div>
            <div class="detail-row"><span>Data/Hora</span><strong>${escapeHtml(formatDateTime(oc.data_hora || oc.horario_alerta || oc.criado_em))}</strong></div>
            <div class="detail-row"><span>Quem registrou</span><strong>${escapeHtml(operatorName(oc))}</strong></div>
            <div class="detail-row"><span>E-mail</span><strong>${escapeHtml(valueOrNA(oc.operador_email))}</strong></div>
            <div class="detail-row"><span>Status</span><strong>${escapeHtml(statusLabel(oc.status))}</strong></div>
            <div class="detail-row"><span>Etapa</span><strong>${escapeHtml(statusLabel(oc.etapa))}</strong></div>
            <div class="detail-row"><span>Contato</span><strong>${escapeHtml(statusLabel(oc.contato_status))}</strong></div>
            <div class="detail-row"><span>Parada</span><strong>${escapeHtml(statusLabel(oc.parada_status))}</strong></div>
            ${timerDetail}
            <div class="detail-row"><span>Observações</span><strong>${oc.observacoes_qtd || 0}</strong></div>
        </div>

        <section class="modal-section">
            <h3>Informações adicionais</h3>
            <div class="detail-grid">${additionalFieldsHtml(oc)}</div>
        </section>

        <section class="modal-section">
            <h3>Observação inicial</h3>
            <p class="initial-note">${escapeHtml(obsInicial === "N/A" ? "Sem observações" : obsInicial)}</p>
        </section>

        ${timelineHtml(oc)}
        ${actionsHtml}
        ${adminDeleteHtml}

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

    const timerRange = qs("#timer-minutes");
    const timerLabel = qs("#timer-minutes-label");
    if (timerRange && timerLabel) {
        timerRange.addEventListener("input", () => {
            timerLabel.textContent = `${timerRange.value} min`;
        });
    }

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
    if (action === "close-detail") {
        closeOccurrenceModal();
        return;
    }

    if (action === "delete-occurrence") {
        if (!currentUser.admin) {
            showToast("Apenas usuarios admin podem apagar ocorrencias.");
            return;
        }

        if (!window.confirm("Apagar esta ocorrencia definitivamente?")) return;

        const response = await fetch(`/api/ocorrencias/${id}`, {
            method: "DELETE",
            headers: {"Content-Type": "application/json"},
        });

        if (!response.ok) {
            showToast("Nao foi possivel apagar a ocorrencia.");
            return;
        }

        state.selectedOccurrenceId = null;
        closeOccurrenceModal();
        delete state.occurrenceDrafts[id];
        return refreshAll();
    }

    if (action === "timer") {
        const timerRange = qs("#timer-minutes");
        const minutos = Math.max(5, Math.min(30, Number(timerRange ? timerRange.value : 10)));
        await fetch(`/api/ocorrencias/${id}/timer`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({minutos}),
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

function requestNotificationPermission() {
    if (!("Notification" in window)) return;

    if (Notification.permission === "default") {
        Notification.requestPermission()
            .then(updateNotificationControl)
            .catch(updateNotificationControl);
        return;
    }

    if (Notification.permission === "denied") {
        showToast("Notificações do navegador estão bloqueadas. Libere nas permissões do site para receber aviso do Windows.");
    }

    updateNotificationControl();
}

function notificationLabel() {
    if (!("Notification" in window)) return "Notif. indisponível";
    if (Notification.permission === "granted") return "Notificações ON";
    if (Notification.permission === "denied") return "Notif. bloqueada";
    return "Ativar notificações";
}

function updateNotificationControl() {
    const button = qs("#notification-toggle");
    if (!button) return;

    button.textContent = notificationLabel();
    button.classList.toggle("enabled", "Notification" in window && Notification.permission === "granted");
    button.classList.toggle("blocked", "Notification" in window && Notification.permission === "denied");
}

function setupNotificationControl() {
    const topActions = qs(".top-actions");
    if (!topActions || qs("#notification-toggle")) return;

    const button = document.createElement("button");
    button.type = "button";
    button.id = "notification-toggle";
    button.className = "notification-toggle";
    button.addEventListener("click", requestNotificationPermission);

    topActions.insertBefore(button, topActions.firstChild);
    updateNotificationControl();
}

function setupSidebarToggle() {
    const button = qs("#sidebar-toggle");
    if (!button) return;

    if (localStorage.getItem("monfretrack-sidebar") === "collapsed") {
        document.body.classList.add("sidebar-collapsed");
    }

    button.addEventListener("click", () => {
        document.body.classList.toggle("sidebar-collapsed");
        localStorage.setItem(
            "monfretrack-sidebar",
            document.body.classList.contains("sidebar-collapsed") ? "collapsed" : "open"
        );
    });
}

function applyOccurrenceScale(scale) {
    const allowed = ["normal", "compacta", "tv", "maxima"];
    const selected = allowed.includes(scale) ? scale : "normal";
    state.occurrenceScale = selected;

    document.body.classList.remove(
        "occ-scale-normal",
        "occ-scale-compacta",
        "occ-scale-tv",
        "occ-scale-maxima"
    );
    document.body.classList.add(`occ-scale-${selected}`);
    localStorage.setItem("monfretrack-occurrence-scale", selected);

    document.querySelectorAll("[data-scale]").forEach((button) => {
        button.classList.toggle("active", button.dataset.scale === selected);
    });
}

function setupOccurrenceScale() {
    const control = qs("#occurrence-scale-control");
    if (!control) return;

    applyOccurrenceScale(localStorage.getItem("monfretrack-occurrence-scale") || "normal");
    control.querySelectorAll("[data-scale]").forEach((button) => {
        button.addEventListener("click", () => applyOccurrenceScale(button.dataset.scale));
    });
}

function applyHistoryWindow(hours) {
    const allowed = [5, 9, 12, 24];
    const selected = allowed.includes(Number(hours)) ? Number(hours) : 9;
    state.historyHours = selected;
    localStorage.setItem("monfretrack-history-hours", String(selected));

    document.querySelectorAll("[data-history-hours]").forEach((button) => {
        button.classList.toggle("active", Number(button.dataset.historyHours) === selected);
    });
}

function setupHistoryWindow() {
    const control = qs("#history-window-control");
    if (!control) return;

    applyHistoryWindow(state.historyHours);
    control.querySelectorAll("[data-history-hours]").forEach((button) => {
        button.addEventListener("click", async () => {
            applyHistoryWindow(button.dataset.historyHours);
            await refreshAll();
        });
    });
}

function showToast(message) {
    let container = qs("#toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("article");
    toast.className = "timer-toast";
    toast.innerHTML = `
        <strong>Timer finalizado</strong>
        <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 14000);
}

function notifyTimerEnd(oc) {
    const placa = oc.placa && oc.placa !== "-" ? oc.placa : "placa não informada";
    const motorista = oc.motorista && oc.motorista !== "Nao informado" ? oc.motorista : "motorista não informado";
    const minutos = oc.timer_minutos || "-";
    const message = `Timer de ${minutos} min finalizado | ${placa} | ${motorista} | confirmar parada`;

    showToast(message);

    if ("Notification" in window && Notification.permission === "granted") {
        const notification = new Notification("MonfreTrack", {
            body: message,
            tag: `timer-${oc.id}-${oc.timer_fim || ""}`,
            requireInteraction: true,
        });
        notification.onclick = () => {
            window.focus();
            openOccurrenceModal(oc.id, state.lastData);
        };
    }
}

function checkTimerNotifications(data) {
    const ocorrencias = data.ocorrencias_abertas || [];
    ocorrencias.forEach((oc) => {
        const vencido = oc.timer_estado === "VENCIDO" || Number(oc.timer_restante_segundos) <= 0;
        if (!vencido || !oc.timer_fim) return;

        const key = `${oc.id}:${oc.timer_fim}`;
        if (state.notifiedTimers.has(key)) return;

        state.notifiedTimers.add(key);
        notifyTimerEnd(oc);
    });
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
        const nearBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80;
        const firstLoad = chat.dataset.loaded !== "1";
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
                    <small>${escapeHtml(formatDateTime(nota.criado_em))}</small>
                </article>
            `).join("")
            : `<div class="empty-block">Nenhuma observação anexada.</div>`;
        chat.querySelectorAll("[data-delete-note]").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                deleteTurnoNote(button.dataset.deleteNote);
            });
        });
        if (firstLoad || nearBottom) {
            chat.scrollTop = chat.scrollHeight;
        }
        chat.dataset.loaded = "1";
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
    state.detailClosed = false;
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
        const response = await fetch(`/api/dashboard?history_hours=${state.historyHours}`, {cache: "no-store"});
        const data = await response.json();
        state.lastData = data;

        const status = qs("#sidebar-status");
        if (status) status.textContent = `Atualizado ${new Date().toLocaleTimeString("pt-BR")}`;

        renderDashboard(data);
        renderOperation(data);
        checkTimerNotifications(data);
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
    const modal = qs("#occurrence-modal");
    if (modal) {
        modal.addEventListener("click", (event) => {
            if (event.target === modal) closeOccurrenceModal();
        });
    }
    document.querySelectorAll("[data-action='close-detail']").forEach((button) => {
        button.addEventListener("click", closeOccurrenceModal);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeOccurrenceModal();
    });
    setupNotificationControl();
    setupSidebarToggle();
    setupOccurrenceScale();
    setupHistoryWindow();
    document.addEventListener("click", requestNotificationPermission, {once: true});

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
