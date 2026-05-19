# -*- coding: utf-8 -*-

import os
import sqlite3
import hashlib
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "painel.db")
MONFRETRACK_DIR = (
    r"C:\Users\DANIEL.OLIVEIRA\OneDrive - MONFREDINI TRANSPORTES LTDA"
    r"\Área de Trabalho\Teste"
)
MONFRETRACK_DB_PATH = os.path.join(MONFRETRACK_DIR, "monfretrack.db")
DESKTOP_DIR = (
    r"C:\Users\DANIEL.OLIVEIRA\OneDrive - MONFREDINI TRANSPORTES LTDA"
    r"\Área de Trabalho"
)

TURNOS = {
    "daniel.oliveira": "T1",
    "nathan.peres": "T1",
    "holly.canedo": "T1",
    "reginaldo.reis": "T1",
    "matheus.ribeiro": "T2",
    "amanda.malta": "T2",
    "andreia.oliveira": "T2",
    "delton.braga": "T3",
    "filipe.brito": "T3",
    "tiago.fernandes": "T3",
    "edjairo.pereira": "T3",
    "julia.cassani": "T3",
}

TURNOS_ORDEM = ["T1", "T2", "T3", "ADM"]


def agora_iso():
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def hoje_iso():
    return datetime.now().date().isoformat()


def parse_dt(valor):
    if not valor:
        return None

    try:
        return datetime.fromisoformat(str(valor))
    except Exception:
        return None


def turno_operador(nome, admin=False):
    nome = (nome or "").strip().lower()
    if nome in TURNOS:
        return TURNOS[nome]
    return "ADM" if admin else "T3"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_senha(senha):
    return hashlib.sha256(str(senha or "").encode("utf-8")).hexdigest()


def get_monfre_conn():
    db_path = resolver_monfretrack_db()
    if not db_path:
        return None

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def contar_usuarios_db(db_path):
    try:
        with sqlite3.connect(db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    except Exception:
        return -1


def resolver_monfretrack_db():
    env_path = os.environ.get("MONFRETRACK_DB_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    candidatos = [
        MONFRETRACK_DB_PATH,
        os.path.join(DESKTOP_DIR, "MonfreTrack-v1", "monfretrack.db"),
        os.path.join(DESKTOP_DIR, "Teste", "MonfreTrack-v1", "monfretrack.db"),
        os.path.join(DESKTOP_DIR, "MonfreTrack_2.0", "monfretrack.db"),
        os.path.join(DESKTOP_DIR, "MonfreTrack", "monfretrack.db"),
        os.path.join(DESKTOP_DIR, "monfretrack.db"),
    ]

    existentes = [path for path in candidatos if os.path.exists(path)]
    if not existentes:
        return None

    return max(existentes, key=contar_usuarios_db)


def validar_login(nome, senha):
    nome = (nome or "").strip().lower()
    senha = str(senha or "").strip()

    usuarios = {
        "daniel.oliveira": {"senha": "789456", "admin": True},
        "william.santos": {"senha": "564208", "admin": True},
        "aurelio.elizei": {"senha": "830471", "admin": True},

        "nathan.peres": {"senha": "604913", "admin": False},
        "holly.canedo": {"senha": "275840", "admin": False},
        "reginaldo.reis": {"senha": "918362", "admin": False},

        "matheus.ribeiro": {"senha": "482913", "admin": False},
        "amanda.malta": {"senha": "739204", "admin": False},
        "andreia.oliveira": {"senha": "158672", "admin": False},
        "delton.braga": {"senha": "904381", "admin": False},
        "filipe.brito": {"senha": "627490", "admin": False},
        "julia.cassani": {"senha": "315846", "admin": False},
        "edjairo.pereira": {"senha": "806157", "admin": False},
        "tiago.fernandes": {"senha": "291638", "admin": False},
    }

    usuario = usuarios.get(nome)

    if not usuario or usuario["senha"] != senha:
        return None

    return {
        "nome": nome,
        "admin": usuario["admin"],
    }

def listar_usuarios_cadastrados():
    conn = get_monfre_conn()
    usuarios = []

    if conn:
        try:
            rows = conn.execute(
                """
                SELECT nome, admin, ativo
                  FROM usuarios
                 WHERE ativo = 1
                 ORDER BY nome
                """
            ).fetchall()
        finally:
            conn.close()

        usuarios = [
            {
                "nome": row["nome"],
                "admin": bool(row["admin"]),
                "ativo": bool(row["ativo"]),
            }
            for row in rows
        ]

    nomes = {usuario["nome"] for usuario in usuarios}
    for nome in TURNOS:
        if nome not in nomes:
            usuarios.append({"nome": nome, "admin": False, "ativo": True})

    return sorted(usuarios, key=lambda item: item["nome"])


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS operadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operador TEXT NOT NULL,
                maquina TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ABERTO',
                app_aberto_em TEXT NOT NULL,
                ultimo_heartbeat TEXT NOT NULL,
                versao TEXT,
                UNIQUE(operador, maquina)
            );

            CREATE TABLE IF NOT EXISTS alertas_tratados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operador TEXT NOT NULL,
                maquina TEXT NOT NULL,
                tipo TEXT NOT NULL,
                placa TEXT,
                motorista TEXT,
                criado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                tipo TEXT NOT NULL DEFAULT 'FADIGA',
                placa TEXT,
                motorista TEXT,
                operador TEXT,
                maquina TEXT,
                horario_alerta TEXT,
                status TEXT NOT NULL DEFAULT 'ABERTA',
                etapa TEXT NOT NULL DEFAULT 'AGUARDANDO_CONTATO',
                contato_status TEXT NOT NULL DEFAULT 'PENDENTE',
                parada_status TEXT NOT NULL DEFAULT 'PENDENTE',
                timer_minutos INTEGER,
                timer_inicio TEXT,
                timer_fim TEXT,
                observacao TEXT,
                alertas_qtd INTEGER NOT NULL DEFAULT 1,
                ultimo_alerta_em TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                finalizado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS preventivas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placa TEXT NOT NULL,
                motorista TEXT NOT NULL,
                tempo_conducao_min INTEGER NOT NULL,
                contrato TEXT NOT NULL,
                programacao TEXT NOT NULL,
                rastreador TEXT NOT NULL,
                eta_distancia_km INTEGER NOT NULL,
                tempo_estimado_min INTEGER NOT NULL,
                tempo_margem_min INTEGER NOT NULL,
                velocidade_kmh INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'OBSERVAR',
                operador_tratando TEXT,
                contato_confirmado_em TEXT,
                parada_aceita_em TEXT,
                parada_confirmada_em TEXT,
                timer_minutos INTEGER,
                timer_inicio TEXT,
                timer_fim TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notas_turno (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operador TEXT NOT NULL,
                referencia_tipo TEXT NOT NULL,
                referencia_id INTEGER,
                mensagem TEXT NOT NULL,
                apagada INTEGER NOT NULL DEFAULT 0,
                apagada_em TEXT,
                criado_em TEXT NOT NULL
            );
            """
        )
        garantir_coluna(conn, "ocorrencias", "alertas_qtd", "INTEGER NOT NULL DEFAULT 1")
        garantir_coluna(conn, "ocorrencias", "ultimo_alerta_em", "TEXT")
        garantir_coluna(conn, "notas_turno", "apagada", "INTEGER NOT NULL DEFAULT 0")
        garantir_coluna(conn, "notas_turno", "apagada_em", "TEXT")


def garantir_coluna(conn, tabela, coluna, definicao):
    existentes = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    }

    if coluna not in existentes:
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def upsert_operador(operador, maquina, status="ABERTO", versao=None):
    operador = (operador or "sem.operador").strip().lower()
    maquina = (maquina or "sem.maquina").strip().upper()
    status = (status or "ABERTO").strip().upper()
    agora = agora_iso()

    with get_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM operadores WHERE operador = ? AND maquina = ?",
            (operador, maquina),
        ).fetchone()

        if existente:
            conn.execute(
                """
                UPDATE operadores
                   SET status = ?,
                       ultimo_heartbeat = ?,
                       versao = COALESCE(?, versao)
                 WHERE id = ?
                """,
                (status, agora, versao, existente["id"]),
            )
            return existente["id"]

        cur = conn.execute(
            """
            INSERT INTO operadores
                (operador, maquina, status, app_aberto_em, ultimo_heartbeat, versao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (operador, maquina, status, agora, agora, versao),
        )
        return cur.lastrowid


def registrar_alerta_tratado(operador, maquina, tipo, placa=None, motorista=None):
    operador = (operador or "sem.operador").strip().lower()
    maquina = (maquina or "sem.maquina").strip().upper()
    tipo = (tipo or "NAO INFORMADO").strip().upper()

    if tipo != "FADIGA":
        placa = None
        motorista = None

    upsert_operador(operador, maquina, status="RODANDO")

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO alertas_tratados
                (operador, maquina, tipo, placa, motorista, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (operador, maquina, tipo, placa, motorista, agora_iso()),
        )
        return cur.lastrowid


def criar_ocorrencia(payload):
    agora = agora_iso()
    operador = (payload.get("operador") or "sem.operador").strip().lower()
    maquina = (payload.get("maquina") or "sem.maquina").strip().upper()
    external_id = payload.get("external_id")
    tipo = (payload.get("tipo") or "FADIGA").strip().upper()
    placa = normalizar_chave(payload.get("placa"))
    motorista = normalizar_chave(payload.get("motorista"))

    upsert_operador(operador, maquina, status=payload.get("status_operador") or "RODANDO")

    with get_conn() as conn:
        if tipo == "FADIGA":
            existente = buscar_fadiga_aberta(conn, placa, motorista)
            if existente:
                conn.execute(
                    """
                    UPDATE ocorrencias
                       SET alertas_qtd = COALESCE(alertas_qtd, 1) + 1,
                           ultimo_alerta_em = ?,
                           operador = COALESCE(NULLIF(?, ''), operador),
                           maquina = COALESCE(NULLIF(?, ''), maquina),
                           atualizado_em = ?
                     WHERE id = ?
                    """,
                    (agora, operador, maquina, agora, existente["id"]),
                )
                return existente["id"]

        if external_id:
            existente = conn.execute(
                "SELECT id FROM ocorrencias WHERE external_id = ?",
                (external_id,),
            ).fetchone()
            if existente:
                atualizar_ocorrencia(existente["id"], payload)
                return existente["id"]

        cur = conn.execute(
            """
            INSERT INTO ocorrencias (
                external_id, tipo, placa, motorista, operador, maquina,
                horario_alerta, status, etapa, contato_status, parada_status,
                timer_minutos, timer_inicio, timer_fim, observacao,
                alertas_qtd, ultimo_alerta_em, criado_em, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                external_id,
                tipo,
                payload.get("placa") or "-",
                payload.get("motorista") or "Motorista nao identificado",
                operador,
                maquina,
                payload.get("horario_alerta") or agora,
                (payload.get("status") or "ABERTA").strip().upper(),
                (payload.get("etapa") or "AGUARDANDO_CONTATO").strip().upper(),
                (payload.get("contato_status") or "PENDENTE").strip().upper(),
                (payload.get("parada_status") or "PENDENTE").strip().upper(),
                payload.get("timer_minutos"),
                payload.get("timer_inicio"),
                payload.get("timer_fim"),
                payload.get("observacao"),
                int(payload.get("alertas_qtd") or 1),
                agora,
                agora,
                agora,
            ),
        )
        return cur.lastrowid


def normalizar_chave(valor):
    valor = str(valor or "").strip().upper()

    if not valor or valor in {"-", "NAO INFORMADO", "NÃO INFORMADO", "MOTORISTA NAO IDENTIFICADO", "MOTORISTA NÃO IDENTIFICADO"}:
        return ""

    return valor


def buscar_fadiga_aberta(conn, placa, motorista):
    if not placa and not motorista:
        return None

    condicoes = ["tipo = 'FADIGA'", "status NOT IN ('FINALIZADA', 'CANCELADA')"]
    params = []

    if placa:
        condicoes.append("UPPER(COALESCE(placa, '')) = ?")
        params.append(placa)

    if motorista:
        condicoes.append("UPPER(COALESCE(motorista, '')) = ?")
        params.append(motorista)

    return conn.execute(
        f"""
        SELECT id
          FROM ocorrencias
         WHERE {' AND '.join(condicoes)}
         ORDER BY atualizado_em DESC
         LIMIT 1
        """,
        params,
    ).fetchone()


def atualizar_ocorrencia(ocorrencia_id, payload):
    campos = []
    valores = []
    permitidos = {
        "placa",
        "motorista",
        "operador",
        "maquina",
        "horario_alerta",
        "status",
        "etapa",
        "contato_status",
        "parada_status",
        "timer_minutos",
        "timer_inicio",
        "timer_fim",
        "observacao",
        "finalizado_em",
    }

    for campo in permitidos:
        if campo in payload:
            valor = payload[campo]
            if campo in {"operador"} and valor:
                valor = str(valor).strip().lower()
            if campo in {"maquina"} and valor:
                valor = str(valor).strip().upper()
            if campo in {"status", "etapa", "contato_status", "parada_status"} and valor:
                valor = str(valor).strip().upper()
            campos.append(f"{campo} = ?")
            valores.append(valor)

    if payload.get("status", "").upper() in {"FINALIZADA", "CANCELADA"} and "finalizado_em" not in payload:
        campos.append("finalizado_em = ?")
        valores.append(agora_iso())

    campos.append("atualizado_em = ?")
    valores.append(agora_iso())
    valores.append(ocorrencia_id)

    with get_conn() as conn:
        conn.execute(
            f"UPDATE ocorrencias SET {', '.join(campos)} WHERE id = ?",
            valores,
        )


def iniciar_timer_ocorrencia(ocorrencia_id, minutos):
    inicio = datetime.now().replace(microsecond=0)
    fim = inicio + timedelta(minutes=int(minutos))
    atualizar_ocorrencia(
        ocorrencia_id,
        {
            "timer_minutos": int(minutos),
            "timer_inicio": inicio.isoformat(sep=" "),
            "timer_fim": fim.isoformat(sep=" "),
            "etapa": "ACOMPANHAMENTO",
            "status": "EM_ACOMPANHAMENTO",
        },
    )


def contrato_classe(contrato):
    contrato = (contrato or "").strip().lower()
    if "mercado" in contrato:
        return "mercado"
    if "amazon" in contrato:
        return "amazon"
    if "shopee" in contrato:
        return "shopee"
    return "outro"


def status_preventiva_por_tempo(minutos):
    return "PREVENTIVA" if int(minutos or 0) >= 420 else "OBSERVAR"


def seed_preventivas_demo():
    dados = [
        ("TLH1G74", "JOAO VITOR SILVA SANTOS", 556, "Mercado Livre", "93139594", "Autotrac", 43, 25, 168, 34),
        ("EMT5A22", "EVAIR JOSE DA SILVA", 545, "Shopee", "LT005C025HGU1", "Autotrac", 252, 204, 138, 0),
        ("EML5J72", "GABRIEL RICARTE LUZ", 505, "Mercado Livre", "93157797", "Trucks Control", 306, 252, 300, 86),
        ("UFK3E10", "PAULO GUSTAVO DOS SANTOS", 474, "Shopee", "LT005D025JNM1", "Autotrac", 938, 791, 661, 76),
        ("EML3G02", "DADIENE DA SILVA RODRIGUES", 459, "Mercado Livre", "93146709", "Trucks Control", 371, 309, 303, 9),
        ("EML5E52", "CARLOS ALBERTO BIACCHI", 400, "Mercado Livre", "93139480", "Trucks Control", 467, 510, 372, 56),
        ("EMT3G81", "LUIS EDUARDO BITENCOURT", 399, "Mercado Livre", "93154556", "Autotrac", 402, 335, 34, 51),
        ("UDY9A07", "JOAO BATISTA DE SALES", 385, "Shopee", "LT005C025IV21", "Autotrac", 0, 0, 0, 0),
        ("UEE9D96", "RICHARD DE BARROS", 363, "Shopee", "LT105D025T71", "Autotrac", 910, 767, 415, 88),
        ("TKG7F96", "ADILSON AMARO RIBEIRO", 359, "Shopee", "LT003C025J232", "Autotrac", 662, 556, 627, 85),
        ("EML5B12", "WANDERSON MARTINS", 345, "Mercado Livre", "93115012", "Trucks Control", 567, 480, 403, 68),
        ("EMT5E81", "EDVALDO JOSE DA COSTA", 336, "Amazon", "116L2WGR6", "Autotrac", 469, 384, -27, 77),
    ]
    agora = agora_iso()

    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS total FROM preventivas").fetchone()["total"]
        if total:
            return

        for item in dados:
            tempo = item[2]
            conn.execute(
                """
                INSERT INTO preventivas (
                    placa, motorista, tempo_conducao_min, contrato, programacao,
                    rastreador, eta_distancia_km, tempo_estimado_min,
                    tempo_margem_min, velocidade_kmh, status, criado_em, atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                item + (status_preventiva_por_tempo(tempo), agora, agora),
            )


def formatar_margem(minutos):
    minutos = int(minutos or 0)
    sinal = "+" if minutos >= 0 else "-"
    minutos = abs(minutos)
    horas = minutos // 60
    resto = minutos % 60
    return f"{sinal}{horas:02d}h{resto:02d}m"


def enriquecer_preventiva(row):
    item = dict(row)
    item["tempo_conducao"] = formatar_duracao(item["tempo_conducao_min"] * 60)
    item["tempo_estimado"] = formatar_duracao(item["tempo_estimado_min"] * 60)
    item["tempo_margem"] = formatar_margem(item["tempo_margem_min"])
    item["contrato_classe"] = contrato_classe(item["contrato"])

    timer_fim = parse_dt(item["timer_fim"])
    timer_inicio = parse_dt(item["timer_inicio"])
    restante = None
    if timer_fim:
        restante = int((timer_fim - datetime.now()).total_seconds())

    item["timer_restante_segundos"] = restante
    item["timer_restante"] = formatar_timer(restante) if restante is not None else "-"
    item["timer_percentual"] = calcular_percentual_timer(timer_inicio, timer_fim)
    item["timer_estado"] = "RODANDO" if restante and restante > 0 else ("VENCIDO" if restante is not None else "SEM_TIMER")
    return item


def listar_preventivas():
    seed_preventivas_demo()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
              FROM preventivas
             ORDER BY
                CASE
                    WHEN status IN ('PREVENTIVA', 'EM_CONTATO', 'PARADA_ACEITA', 'TIMER_ATIVO') THEN 0
                    WHEN status = 'OBSERVAR' THEN 1
                    ELSE 2
                END,
                tempo_conducao_min DESC
            """
        ).fetchall()

    return [enriquecer_preventiva(row) for row in rows]


def atualizar_preventiva(preventiva_id, payload):
    operador = (payload.get("operador") or "daniel.oliveira").strip().lower()
    acao = (payload.get("acao") or "").strip()
    agora = agora_iso()
    campos = ["operador_tratando = ?", "atualizado_em = ?"]
    valores = [operador, agora]

    if acao == "contato":
        campos += ["status = ?", "contato_confirmado_em = ?"]
        valores += ["EM_CONTATO", agora]
    elif acao == "parada_aceita":
        campos += ["status = ?", "parada_aceita_em = ?"]
        valores += ["PARADA_ACEITA", agora]
    elif acao == "parada_confirmada":
        campos += ["status = ?", "parada_confirmada_em = ?"]
        valores += ["PARADA_CONFIRMADA", agora]
    elif acao == "finalizar":
        campos += ["status = ?"]
        valores += ["FINALIZADA"]

    valores.append(preventiva_id)

    with get_conn() as conn:
        conn.execute(
            f"UPDATE preventivas SET {', '.join(campos)} WHERE id = ?",
            valores,
        )


def iniciar_timer_preventiva(preventiva_id, minutos):
    minutos = max(1, min(20, int(minutos or 20)))
    inicio = datetime.now().replace(microsecond=0)
    fim = inicio + timedelta(minutes=minutos)

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE preventivas
               SET operador_tratando = COALESCE(operador_tratando, 'daniel.oliveira'),
                   status = 'TIMER_ATIVO',
                   timer_minutos = ?,
                   timer_inicio = ?,
                   timer_fim = ?,
                   atualizado_em = ?
             WHERE id = ?
            """,
            (
                minutos,
                inicio.isoformat(sep=" "),
                fim.isoformat(sep=" "),
                agora_iso(),
                preventiva_id,
            ),
        )


def adicionar_nota_turno(payload):
    operador = (payload.get("operador") or "daniel.oliveira").strip().lower()
    referencia_tipo = (payload.get("referencia_tipo") or "GERAL").strip().upper()
    referencia_id = payload.get("referencia_id")
    mensagem = (payload.get("mensagem") or "").strip()

    if not mensagem:
        mensagem = "Sem observacao informada."

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO notas_turno
                (operador, referencia_tipo, referencia_id, mensagem, apagada, criado_em)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (operador, referencia_tipo, referencia_id, mensagem, agora_iso()),
        )
        return cur.lastrowid


def listar_notas_turno(limite=80):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
              FROM (
                    SELECT *
                      FROM notas_turno
                     WHERE apagada = 0
                     ORDER BY criado_em DESC
                     LIMIT ?
                   )
             ORDER BY criado_em ASC
            """,
            (limite,),
        ).fetchall()

    return [dict(row) for row in rows]


def listar_notas_referencia(referencia_tipo, referencia_id, limite=20):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
              FROM notas_turno
             WHERE apagada = 0
               AND referencia_tipo = ?
               AND referencia_id = ?
             ORDER BY criado_em ASC
             LIMIT ?
            """,
            ((referencia_tipo or "").strip().upper(), referencia_id, limite),
        ).fetchall()

    return [dict(row) for row in rows]


def apagar_nota_turno(nota_id, operador=None):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE notas_turno
               SET apagada = 1,
                   apagada_em = ?
             WHERE id = ?
            """,
            (agora_iso(), nota_id),
        )


def dados_troca_turno():
    ocorrencias = listar_ocorrencias(apenas_abertas=True, limite=80)

    return {
        "operador_padrao": "daniel.oliveira",
        "ocorrencias": ocorrencias,
        "operadores": listar_operadores(),
        "notas": listar_notas_turno(),
    }


def listar_operadores(timeout_online=35):
    limite = datetime.now() - timedelta(seconds=timeout_online)
    usuarios = listar_usuarios_cadastrados()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
              FROM operadores
             ORDER BY ultimo_heartbeat DESC
            """
        ).fetchall()

        tratados = {
            row["operador"]: row["total"]
            for row in conn.execute(
                """
                SELECT operador, COUNT(*) AS total
                  FROM alertas_tratados
                 WHERE date(criado_em) = date('now', 'localtime')
                 GROUP BY operador
                """
            ).fetchall()
        }

    ultimo_por_operador = {}
    for row in rows:
        operador = row["operador"]
        if operador not in ultimo_por_operador:
            ultimo_por_operador[operador] = row

    nomes_conhecidos = {usuario["nome"] for usuario in usuarios}
    for operador in ultimo_por_operador:
        if operador not in nomes_conhecidos:
            usuarios.append({"nome": operador, "admin": False, "ativo": True})

    operadores = []
    for usuario in sorted(usuarios, key=lambda item: item["nome"]):
        row = ultimo_por_operador.get(usuario["nome"])

        ultimo = parse_dt(row["ultimo_heartbeat"]) if row else None
        aberto = parse_dt(row["app_aberto_em"]) if row else None
        online = bool(ultimo and ultimo >= limite)
        segundos_aberto = int((datetime.now() - aberto).total_seconds()) if aberto else 0
        status = row["status"] if row else "OFFLINE"

        operadores.append(
            {
                "id": row["id"] if row else None,
                "operador": usuario["nome"],
                "admin": usuario["admin"],
                "turno": turno_operador(usuario["nome"], usuario["admin"]),
                "maquina": row["maquina"] if row else "-",
                "status": status,
                "online": online,
                "app_aberto_em": row["app_aberto_em"] if row else None,
                "ultimo_heartbeat": row["ultimo_heartbeat"] if row else None,
                "segundos_aberto": max(0, segundos_aberto),
                "tempo_aberto": formatar_duracao(segundos_aberto),
                "tratados_hoje": tratados.get(usuario["nome"], 0),
                "versao": row["versao"] if row else None,
            }
        )

    return operadores


def enriquecer_ocorrencia(row):
    timer_fim = parse_dt(row["timer_fim"])
    timer_inicio = parse_dt(row["timer_inicio"])
    restante = None
    timer_estado = "SEM_TIMER"

    if timer_fim:
        restante = int((timer_fim - datetime.now()).total_seconds())
        timer_estado = "RODANDO" if restante > 0 else "VENCIDO"

    duracao_aberta = 0
    criado = parse_dt(row["criado_em"])
    if criado:
        duracao_aberta = int((datetime.now() - criado).total_seconds())

    item = dict(row)
    item["alertas_qtd"] = int(item.get("alertas_qtd") or 1)
    item["notas"] = listar_notas_referencia("OCORRENCIA", item["id"], limite=12)
    item["timer_estado"] = timer_estado
    item["timer_restante_segundos"] = restante
    item["timer_restante"] = formatar_timer(restante) if restante is not None else "-"
    item["timer_percentual"] = calcular_percentual_timer(timer_inicio, timer_fim)
    item["idade"] = formatar_duracao(duracao_aberta)
    return item


def listar_ocorrencias(apenas_abertas=False, limite=80):
    where = ""
    params = []
    if apenas_abertas:
        where = "WHERE o.status NOT IN ('FINALIZADA', 'CANCELADA')"

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT o.*,
                   (
                       SELECT COUNT(*)
                         FROM notas_turno n
                        WHERE n.referencia_tipo = 'OCORRENCIA'
                          AND n.referencia_id = o.id
                          AND n.apagada = 0
                   ) AS observacoes_qtd,
                   (
                       SELECT n.mensagem
                         FROM notas_turno n
                        WHERE n.referencia_tipo = 'OCORRENCIA'
                          AND n.referencia_id = o.id
                          AND n.apagada = 0
                        ORDER BY n.criado_em DESC
                        LIMIT 1
                   ) AS ultima_observacao
              FROM ocorrencias o
              {where}
             ORDER BY
                  CASE WHEN o.status IN ('ABERTA', 'EM_CONTATO', 'EM_ACOMPANHAMENTO') THEN 0 ELSE 1 END,
                  o.atualizado_em DESC
             LIMIT ?
            """,
            params + [limite],
        ).fetchall()

    return [enriquecer_ocorrencia(row) for row in rows]


def montar_resumo_turnos(operadores, ocorrencias_abertas):
    turnos = {
        turno: {
            "turno": turno,
            "operadores": [],
            "total": 0,
            "online": 0,
            "offline": 0,
            "tratados_hoje": 0,
            "ocorrencias_abertas": 0,
            "fadigas_abertas": 0,
            "produtividade": 0,
        }
        for turno in TURNOS_ORDEM
    }

    for operador in operadores:
        turno = operador.get("turno") or "T3"
        if turno not in turnos:
            turnos[turno] = {
                "turno": turno,
                "operadores": [],
                "total": 0,
                "online": 0,
                "offline": 0,
                "tratados_hoje": 0,
                "ocorrencias_abertas": 0,
                "fadigas_abertas": 0,
                "produtividade": 0,
            }

        turnos[turno]["operadores"].append(operador)
        turnos[turno]["total"] += 1
        turnos[turno]["online"] += 1 if operador.get("online") else 0
        turnos[turno]["offline"] += 0 if operador.get("online") else 1
        turnos[turno]["tratados_hoje"] += int(operador.get("tratados_hoje") or 0)

    for ocorrencia in ocorrencias_abertas:
        turno = turno_operador(ocorrencia.get("operador"))
        if turno not in turnos:
            continue

        turnos[turno]["ocorrencias_abertas"] += 1
        if str(ocorrencia.get("tipo") or "").upper() == "FADIGA":
            turnos[turno]["fadigas_abertas"] += 1

    for turno in turnos.values():
        turno["produtividade"] = round(turno["tratados_hoje"] / max(1, turno["total"]), 1)

    return [turnos[turno] for turno in TURNOS_ORDEM if turno in turnos]


def resumo_dashboard():
    operadores = listar_operadores()
    ocorrencias_abertas = listar_ocorrencias(apenas_abertas=True, limite=30)
    admins = [op for op in operadores if op.get("admin")]
    usuarios = [op for op in operadores if not op.get("admin")]

    with get_conn() as conn:
        total_tratados_hoje = conn.execute(
            """
            SELECT COUNT(*) AS total
              FROM alertas_tratados
             WHERE date(criado_em) = date('now', 'localtime')
            """
        ).fetchone()["total"]

        fadigas_hoje = conn.execute(
            """
            SELECT COUNT(*) AS total
              FROM ocorrencias
             WHERE tipo = 'FADIGA'
               AND date(criado_em) = date('now', 'localtime')
            """
        ).fetchone()["total"]

    online = [op for op in operadores if op["online"]]
    offline = [op for op in operadores if not op["online"]]
    turnos = montar_resumo_turnos(operadores, ocorrencias_abertas)

    return {
        "agora": agora_iso(),
        "operadores": operadores,
        "admins": admins,
        "usuarios": usuarios,
        "turnos": turnos,
        "operadores_online": len(online),
        "operadores_offline": len(offline),
        "operadores_cadastrados": len(operadores),
        "alertas_tratados_hoje": total_tratados_hoje,
        "fadigas_hoje": fadigas_hoje,
        "ocorrencias_abertas": ocorrencias_abertas,
    }


def formatar_duracao(segundos):
    segundos = max(0, int(segundos or 0))
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60

    if horas:
        return f"{horas}h {minutos:02d}m"

    return f"{minutos}m"


def formatar_timer(segundos):
    if segundos is None:
        return "-"

    negativo = segundos < 0
    segundos = abs(int(segundos))
    minutos = segundos // 60
    resto = segundos % 60
    prefixo = "-" if negativo else ""
    return f"{prefixo}{minutos:02d}:{resto:02d}"


def calcular_percentual_timer(inicio, fim):
    inicio_dt = parse_dt(inicio)
    fim_dt = parse_dt(fim)
    if not inicio_dt or not fim_dt:
        return 0

    total = (fim_dt - inicio_dt).total_seconds()
    if total <= 0:
        return 100

    passado = (datetime.now() - inicio_dt).total_seconds()
    return max(0, min(100, int((passado / total) * 100)))


def limpar_demo():
    with get_conn() as conn:
        conn.execute("DELETE FROM alertas_tratados")
        conn.execute("DELETE FROM ocorrencias")
        conn.execute("DELETE FROM operadores")
        conn.execute("DELETE FROM preventivas")
        conn.execute("DELETE FROM notas_turno")


def popular_demo():
    limpar_demo()

    demo_ops = [
        ("daniel.oliveira", "MONITOR-01", "RODANDO"),
        ("reginaldo.reis", "MONITOR-02", "PAUSADO"),
        ("holly.canedo", "MONITOR-03", "RODANDO"),
        ("nathan.peres", "MONITOR-04", "ABERTO"),
    ]

    for operador, maquina, status in demo_ops:
        upsert_operador(operador, maquina, status=status, versao="demo")

    for _ in range(7):
        registrar_alerta_tratado("daniel.oliveira", "MONITOR-01", "FADIGA", "QSS7G98", "EDVANIO DIAS DA SILVA")

    for _ in range(4):
        registrar_alerta_tratado("holly.canedo", "MONITOR-03", "BOCEJO", "ABC1D23", "MOTORISTA DEMO")

    oc1 = criar_ocorrencia(
        {
            "external_id": "demo-001",
            "placa": "QSS7G98",
            "motorista": "EDVANIO DIAS DA SILVA",
            "operador": "daniel.oliveira",
            "maquina": "MONITOR-01",
            "status": "EM_ACOMPANHAMENTO",
            "etapa": "ACOMPANHAMENTO",
            "contato_status": "CONTATO_FEITO",
            "parada_status": "ACEITOU_PARAR",
            "observacao": "Motorista orientado a parar no ponto seguro.",
        }
    )
    iniciar_timer_ocorrencia(oc1, 15)

    criar_ocorrencia(
        {
            "external_id": "demo-002",
            "placa": "SVP5I73",
            "motorista": "MARCOS ANTONIO",
            "operador": "reginaldo.reis",
            "maquina": "MONITOR-02",
            "status": "EM_CONTATO",
            "etapa": "LIGANDO",
            "contato_status": "TENTANDO_CONTATO",
            "parada_status": "PENDENTE",
        }
    )

    seed_preventivas_demo()
    adicionar_nota_turno(
        {
            "operador": "daniel.oliveira",
            "referencia_tipo": "PREVENTIVA",
            "referencia_id": 1,
            "mensagem": "Priorizar contato com veiculo acima de 9h de conducao.",
        }
    )
