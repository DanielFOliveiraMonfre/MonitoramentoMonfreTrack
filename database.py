# -*- coding: utf-8 -*-

import os
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH = os.environ.get("PAINEL_DB_PATH") or os.path.join(BASE_DIR, "painel.db")
USING_POSTGRES = bool(DATABASE_URL)

if USING_POSTGRES:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:
        raise RuntimeError(
            "DATABASE_URL foi configurado, mas o pacote psycopg nao esta instalado. "
            "Instale psycopg[binary] no requirements.txt."
        ) from exc


def carregar_fuso_local():
    try:
        return ZoneInfo(os.environ.get("MONFRETRACK_TZ", "America/Sao_Paulo"))
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=-3))


FUSO_LOCAL = carregar_fuso_local()
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

USUARIOS_FIXOS = {
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


def agora_iso():
    return agora_dt().isoformat(sep=" ")


def hoje_iso():
    return agora_dt().date().isoformat()


def agora_dt():
    return datetime.now(FUSO_LOCAL).replace(tzinfo=None, microsecond=0)


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


def adaptar_sql_postgres(sql):
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("?", "%s")
    return sql


def dividir_script_sql(script):
    return [parte.strip() for parte in script.split(";") if parte.strip()]


class PostgresConn:
    def __init__(self):
        self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    def execute(self, sql, params=None):
        return self.conn.execute(adaptar_sql_postgres(sql), params or [])

    def executescript(self, script):
        for statement in dividir_script_sql(script):
            self.execute(statement)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_conn():
    if USING_POSTGRES:
        return PostgresConn()

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def inserir_retorna_id(conn, sql, params):
    if USING_POSTGRES:
        sql = sql.strip().rstrip(";")
        cur = conn.execute(f"{sql} RETURNING id", params)
        row = cur.fetchone()
        return row["id"]

    cur = conn.execute(sql, params)
    return cur.lastrowid


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
    usuario = USUARIOS_FIXOS.get(nome)

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
    for nome, dados in USUARIOS_FIXOS.items():
        if nome not in nomes:
            usuarios.append({"nome": nome, "admin": dados["admin"], "ativo": True})
            nomes.add(nome)

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
                operador_nome TEXT,
                operador_email TEXT,
                maquina TEXT,
                data_hora TEXT,
                horario_alerta TEXT,
                origem TEXT NOT NULL DEFAULT 'MONFRETRACK',
                status TEXT NOT NULL DEFAULT 'ABERTA',
                etapa TEXT NOT NULL DEFAULT 'AGUARDANDO_CONTATO',
                contato_status TEXT NOT NULL DEFAULT 'PENDENTE',
                parada_status TEXT NOT NULL DEFAULT 'PENDENTE',
                timer_minutos INTEGER,
                timer_inicio TEXT,
                timer_fim TEXT,
                observacao TEXT,
                observacao_inicial TEXT,
                campos_adicionais TEXT,
                ordem_manual INTEGER,
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

            CREATE TABLE IF NOT EXISTS timeline_ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ocorrencia_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                operador TEXT,
                origem TEXT,
                criado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sincronizacao_excel (
                fonte TEXT PRIMARY KEY,
                ultimo_id INTEGER NOT NULL DEFAULT 0,
                inicializado_em TEXT NOT NULL,
                ultima_sincronizacao_em TEXT,
                ultimo_erro TEXT,
                atualizado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS importacoes_excel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fonte TEXT NOT NULL,
                linha_id INTEGER NOT NULL,
                ocorrencia_id INTEGER,
                payload_hash TEXT,
                status TEXT NOT NULL,
                erro TEXT,
                importado_em TEXT NOT NULL,
                UNIQUE(fonte, linha_id)
            );
            """
        )
        garantir_coluna(conn, "ocorrencias", "alertas_qtd", "INTEGER NOT NULL DEFAULT 1")
        garantir_coluna(conn, "ocorrencias", "ultimo_alerta_em", "TEXT")
        garantir_coluna(conn, "ocorrencias", "operador_nome", "TEXT")
        garantir_coluna(conn, "ocorrencias", "operador_email", "TEXT")
        garantir_coluna(conn, "ocorrencias", "data_hora", "TEXT")
        garantir_coluna(conn, "ocorrencias", "origem", "TEXT NOT NULL DEFAULT 'MONFRETRACK'")
        garantir_coluna(conn, "ocorrencias", "observacao_inicial", "TEXT")
        garantir_coluna(conn, "ocorrencias", "campos_adicionais", "TEXT")
        garantir_coluna(conn, "ocorrencias", "ordem_manual", "INTEGER")
        garantir_coluna(conn, "notas_turno", "apagada", "INTEGER NOT NULL DEFAULT 0")
        garantir_coluna(conn, "notas_turno", "apagada_em", "TEXT")
        conn.execute(
            """
            UPDATE ocorrencias
               SET timer_minutos = NULL, timer_inicio = NULL, timer_fim = NULL
             WHERE timer_minutos = 45
               AND status NOT IN ('FINALIZADA', 'CANCELADA')
            """
        )


def garantir_coluna(conn, tabela, coluna, definicao):
    if USING_POSTGRES:
        existentes = {
            row["column_name"]
            for row in conn.execute(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = ?
                """,
                (tabela,),
            ).fetchall()
        }
    else:
        existentes = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({tabela})").fetchall()
        }

    if coluna not in existentes:
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def obter_estado_sincronizacao_excel(fonte):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sincronizacao_excel WHERE fonte = ?",
            (fonte,),
        ).fetchone()
    return dict(row) if row else None


def inicializar_sincronizacao_excel(fonte, ultimo_id):
    agora = agora_iso()
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT fonte FROM sincronizacao_excel WHERE fonte = ?",
            (fonte,),
        ).fetchone()
        if existente:
            return False
        conn.execute(
            """
            INSERT INTO sincronizacao_excel
                (fonte, ultimo_id, inicializado_em, ultima_sincronizacao_em, ultimo_erro, atualizado_em)
            VALUES (?, ?, ?, ?, NULL, ?)
            """,
            (fonte, int(ultimo_id or 0), agora, agora, agora),
        )
    return True


def atualizar_estado_sincronizacao_excel(fonte, ultimo_id):
    agora = agora_iso()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT ultimo_id FROM sincronizacao_excel WHERE fonte = ?",
            (fonte,),
        ).fetchone()
        if not row:
            return inicializar_sincronizacao_excel(fonte, ultimo_id)
        novo_ultimo_id = max(int(row["ultimo_id"] or 0), int(ultimo_id or 0))
        conn.execute(
            """
            UPDATE sincronizacao_excel
               SET ultimo_id = ?,
                   ultima_sincronizacao_em = ?,
                   ultimo_erro = NULL,
                   atualizado_em = ?
             WHERE fonte = ?
            """,
            (novo_ultimo_id, agora, agora, fonte),
        )
    return True


def concluir_sincronizacao_excel(fonte, ultimo_id):
    return atualizar_estado_sincronizacao_excel(fonte, ultimo_id)


def registrar_erro_sincronizacao_excel(fonte, erro):
    agora = agora_iso()
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT fonte FROM sincronizacao_excel WHERE fonte = ?",
            (fonte,),
        ).fetchone()
        if not existente:
            return False
        conn.execute(
            """
            UPDATE sincronizacao_excel
               SET ultimo_erro = ?,
                   atualizado_em = ?
             WHERE fonte = ?
            """,
            (str(erro or "")[:1000], agora, fonte),
        )
    return True


def linha_excel_importada(fonte, linha_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM importacoes_excel WHERE fonte = ? AND linha_id = ?",
            (fonte, int(linha_id)),
        ).fetchone()
    return bool(row)


def ocorrencia_external_id_existe(external_id):
    if not external_id:
        return False

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM ocorrencias WHERE external_id = ?",
            (external_id,),
        ).fetchone()
    return bool(row)


def registrar_linha_excel_importada(
    fonte,
    linha_id,
    ocorrencia_id,
    payload_hash,
    status,
    erro=None,
):
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM importacoes_excel WHERE fonte = ? AND linha_id = ?",
            (fonte, int(linha_id)),
        ).fetchone()
        if existente:
            conn.execute(
                """
                UPDATE importacoes_excel
                   SET ocorrencia_id = COALESCE(?, ocorrencia_id),
                       payload_hash = COALESCE(?, payload_hash),
                       status = ?,
                       erro = ?,
                       importado_em = ?
                 WHERE id = ?
                """,
                (
                    ocorrencia_id,
                    payload_hash,
                    (status or "IMPORTADA").strip().upper(),
                    erro,
                    agora_iso(),
                    existente["id"],
                ),
            )
            return existente["id"]

        return inserir_retorna_id(
            conn,
            """
            INSERT INTO importacoes_excel
                (fonte, linha_id, ocorrencia_id, payload_hash, status, erro, importado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fonte,
                int(linha_id),
                ocorrencia_id,
                payload_hash,
                (status or "IMPORTADA").strip().upper(),
                erro,
                agora_iso(),
            ),
        )


def upsert_operador(operador, maquina, status="ABERTO", versao=None):
    operador = (operador or "sem.operador").strip().lower()
    maquina = (maquina or "sem.maquina").strip().upper()
    status = (status or "ABERTO").strip().upper()
    agora = agora_iso()

    with get_conn() as conn:
        existente = conn.execute(
            "SELECT * FROM operadores WHERE operador = ? AND maquina = ?",
            (operador, maquina),
        ).fetchone()

        if existente:
            ultimo = parse_dt(existente["ultimo_heartbeat"])
            resetar_abertura = bool(
                not ultimo or (agora_dt() - ultimo).total_seconds() > 45
            )
            conn.execute(
                """
                UPDATE operadores
                   SET status = ?,
                       app_aberto_em = CASE WHEN ? = 1 THEN ? ELSE app_aberto_em END,
                       ultimo_heartbeat = ?,
                       versao = COALESCE(?, versao)
                 WHERE id = ?
                """,
                (status, 1 if resetar_abertura else 0, agora, agora, versao, existente["id"]),
            )
            return existente["id"]

        return inserir_retorna_id(
            conn,
            """
            INSERT INTO operadores
                (operador, maquina, status, app_aberto_em, ultimo_heartbeat, versao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (operador, maquina, status, agora, agora, versao),
        )


def registrar_alerta_tratado(operador, maquina, tipo, placa=None, motorista=None):
    operador = (operador or "sem.operador").strip().lower()
    maquina = (maquina or "sem.maquina").strip().upper()
    tipo = (tipo or "NAO INFORMADO").strip().upper()

    if tipo != "FADIGA":
        placa = None
        motorista = None

    upsert_operador(operador, maquina, status="RODANDO")

    with get_conn() as conn:
        registro_id = inserir_retorna_id(
            conn,
            """
            INSERT INTO alertas_tratados
                (operador, maquina, tipo, placa, motorista, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (operador, maquina, tipo, placa, motorista, agora_iso()),
        )

    return registro_id


def criar_ocorrencia(payload):
    agora = agora_iso()
    operador = (payload.get("operador") or "sem.operador").strip().lower()
    operador_nome = (payload.get("operador_nome") or operador or "sem.operador").strip()
    operador_email = (payload.get("operador_email") or "N/A").strip()
    maquina = (payload.get("maquina") or "sem.maquina").strip().upper()
    external_id = payload.get("external_id")
    tipo = (payload.get("tipo") or payload.get("evento") or "FADIGA").strip().upper()
    placa = normalizar_chave(payload.get("placa"))
    motorista = normalizar_chave(payload.get("motorista"))
    data_hora = payload.get("data_hora") or payload.get("horario_alerta") or agora
    origem = (payload.get("origem") or "MONFRETRACK").strip().upper()
    campos_adicionais = payload.get("campos_adicionais") or {}
    if isinstance(campos_adicionais, str):
        campos_json = campos_adicionais
    else:
        campos_json = json.dumps(campos_adicionais, ensure_ascii=False)
    observacao_inicial = payload.get("observacao_inicial")
    if observacao_inicial is None:
        observacao_inicial = payload.get("observacao")
    timer_minutos = payload.get("timer_minutos")
    timer_inicio = payload.get("timer_inicio")
    timer_fim = payload.get("timer_fim")

    if origem not in {"FORMS", "POWER_AUTOMATE", "EXCEL_FORMS"}:
        upsert_operador(operador, maquina, status=payload.get("status_operador") or "RODANDO")

    with get_conn() as conn:
        if external_id:
            existente = conn.execute(
                "SELECT id FROM ocorrencias WHERE external_id = ?",
                (external_id,),
            ).fetchone()
            if existente:
                return existente["id"]

        if tipo == "FADIGA" and origem not in {"FORMS", "POWER_AUTOMATE", "EXCEL_FORMS"}:
            existente = buscar_fadiga_aberta(conn, placa, motorista)
            if existente:
                ultimo = parse_dt(existente["ultimo_alerta_em"])
                duplicado_recente = bool(
                    ultimo
                    and (agora_dt() - ultimo).total_seconds() <= 5
                    and (existente["operador"] or "").lower() == operador
                )
                if duplicado_recente:
                    return existente["id"]

                conn.execute(
                    """
                    UPDATE ocorrencias
                       SET alertas_qtd = COALESCE(alertas_qtd, 1) + 1,
                           ultimo_alerta_em = ?,
                           atualizado_em = ?
                     WHERE id = ?
                    """,
                    (agora, agora, existente["id"]),
                )
                adicionar_timeline_conn(
                    conn,
                    existente["id"],
                    "NOVO_ALERTA",
                    f"Novo alerta de fadiga agrupado por {operador}",
                    operador,
                    origem,
                    agora,
                )
                return existente["id"]

        ocorrencia_id = inserir_retorna_id(
            conn,
            """
            INSERT INTO ocorrencias (
                external_id, tipo, placa, motorista, operador, operador_nome,
                operador_email, maquina, data_hora, horario_alerta, origem,
                status, etapa, contato_status, parada_status,
                timer_minutos, timer_inicio, timer_fim, observacao,
                observacao_inicial, campos_adicionais, ordem_manual, alertas_qtd,
                ultimo_alerta_em, criado_em, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                external_id,
                tipo,
                payload.get("placa") or "-",
                payload.get("motorista") or "Motorista nao identificado",
                operador,
                operador_nome,
                operador_email,
                maquina,
                data_hora,
                payload.get("horario_alerta") or data_hora,
                origem,
                (payload.get("status") or "ABERTA").strip().upper(),
                (payload.get("etapa") or "AGUARDANDO_CONTATO").strip().upper(),
                (payload.get("contato_status") or "PENDENTE").strip().upper(),
                (payload.get("parada_status") or "PENDENTE").strip().upper(),
                timer_minutos,
                timer_inicio,
                timer_fim,
                payload.get("observacao"),
                observacao_inicial,
                campos_json,
                payload.get("ordem_manual"),
                int(payload.get("alertas_qtd") or 1),
                agora,
                agora,
                agora,
            ),
        )
        adicionar_timeline_conn(
            conn,
            ocorrencia_id,
            "CRIACAO",
            f"Ocorrencia registrada por {operador_nome}",
            operador,
            origem,
            data_hora,
        )
        if observacao_inicial and str(observacao_inicial).strip() and str(observacao_inicial).strip().upper() != "N/A":
            adicionar_timeline_conn(
                conn,
                ocorrencia_id,
                "OBSERVACAO_INICIAL",
                f"Observacao inicial: {observacao_inicial}",
                operador,
                origem,
                data_hora,
            )
        return ocorrencia_id


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
    elif motorista:
        condicoes.append("UPPER(COALESCE(motorista, '')) = ?")
        params.append(motorista)

    return conn.execute(
        f"""
        SELECT *
          FROM ocorrencias
         WHERE {' AND '.join(condicoes)}
         ORDER BY atualizado_em DESC
         LIMIT 1
        """,
        params,
    ).fetchone()


def adicionar_timeline_conn(conn, ocorrencia_id, tipo, mensagem, operador=None, origem=None, criado_em=None):
    if not mensagem:
        return None

    return inserir_retorna_id(
        conn,
        """
        INSERT INTO timeline_ocorrencias
            (ocorrencia_id, tipo, mensagem, operador, origem, criado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ocorrencia_id,
            (tipo or "INFO").strip().upper(),
            str(mensagem).strip(),
            operador,
            origem or "SISTEMA",
            criado_em or agora_iso(),
        ),
    )


def adicionar_timeline(ocorrencia_id, tipo, mensagem, operador=None, origem=None):
    with get_conn() as conn:
        return adicionar_timeline_conn(conn, ocorrencia_id, tipo, mensagem, operador, origem)


def listar_timeline_ocorrencia(ocorrencia_id, limite=80):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
              FROM timeline_ocorrencias
             WHERE ocorrencia_id = ?
             ORDER BY criado_em ASC, id ASC
             LIMIT ?
            """,
            (ocorrencia_id, limite),
        ).fetchall()

    return [dict(row) for row in rows]


def criar_ocorrencia_forms(payload):
    data_hora = payload.get("data_hora") or agora_iso()
    timer_minutos = payload.get("timer_minutos")
    timer_inicio = payload.get("timer_inicio")
    timer_fim = payload.get("timer_fim")
    operador = (payload.get("operador") or "sem.operador").strip().lower()
    tipo = (payload.get("evento") or payload.get("tipo") or "OCORRENCIA").strip().upper()
    if tipo in {"", "N/A"}:
        tipo = "OCORRENCIA"

    dados = dict(payload)
    dados.update(
        {
            "tipo": tipo,
            "evento": tipo,
            "operador": operador,
            "maquina": payload.get("maquina") or "FORMS",
            "origem": payload.get("origem") or "FORMS",
            "horario_alerta": data_hora,
            "data_hora": data_hora,
            "status": payload.get("status") or "ABERTA",
            "etapa": payload.get("etapa") or "AGUARDANDO_CONTATO",
            "contato_status": payload.get("contato_status") or "PENDENTE",
            "parada_status": payload.get("parada_status") or "PENDENTE",
            "timer_minutos": timer_minutos,
            "timer_inicio": timer_inicio,
            "timer_fim": timer_fim,
            "observacao": payload.get("observacao_inicial"),
        }
    )
    return criar_ocorrencia(dados)


def atualizar_ocorrencia(ocorrencia_id, payload):
    campos = []
    valores = []
    permitidos = {
        "placa",
        "motorista",
        "operador",
        "operador_nome",
        "operador_email",
        "maquina",
        "data_hora",
        "horario_alerta",
        "origem",
        "status",
        "etapa",
        "contato_status",
        "parada_status",
        "timer_minutos",
        "timer_inicio",
        "timer_fim",
        "observacao",
        "observacao_inicial",
        "campos_adicionais",
        "ordem_manual",
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
            if campo == "campos_adicionais" and not isinstance(valor, str):
                valor = json.dumps(valor or {}, ensure_ascii=False)
            campos.append(f"{campo} = ?")
            valores.append(valor)

    finalizando = str(payload.get("status", "")).upper() in {"FINALIZADA", "CANCELADA"}

    if finalizando:
        for campo in ("timer_minutos", "timer_inicio", "timer_fim"):
            if campo not in payload:
                campos.append(f"{campo} = ?")
                valores.append(None)

    if finalizando and "finalizado_em" not in payload:
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
        if payload.get("status") or payload.get("etapa") or payload.get("contato_status") or payload.get("parada_status"):
            mensagens = {
                "CONTATO_FEITO": "Motorista atendeu a ligacao",
                "SEM_CONTATO": "Tentativa de contato sem sucesso",
                "ACEITOU_PARAR": "Motorista aceitou parar",
                "RECUSOU_PARAR": "Motorista recusou parar",
                "FINALIZADA": "Ocorrencia finalizada",
                "CANCELADA": "Ocorrencia cancelada",
            }
            mensagem = payload.get("_historico_mensagem")
            if not mensagem:
                for campo in ("parada_status", "contato_status", "status"):
                    valor = str(payload.get(campo) or "").upper()
                    if valor in mensagens:
                        mensagem = mensagens[valor]
                        break
            if not mensagem:
                partes = []
                for campo in ("status", "etapa", "contato_status", "parada_status"):
                    if payload.get(campo):
                        partes.append(f"{campo}: {payload[campo]}")
                mensagem = " | ".join(partes)
            adicionar_timeline_conn(
                conn,
                ocorrencia_id,
                payload.get("_historico_tipo") or "ATUALIZACAO",
                mensagem,
                payload.get("_audit_operador") or payload.get("operador"),
                "PAINEL",
            )


def iniciar_timer_ocorrencia(ocorrencia_id, minutos, operador=None):
    minutos = max(5, min(30, int(minutos or 10)))
    inicio = agora_dt()
    fim = inicio + timedelta(minutes=minutos)
    inicio_iso = inicio.isoformat(sep=" ")
    fim_iso = fim.isoformat(sep=" ")
    atualizar_ocorrencia(
        ocorrencia_id,
        {
            "timer_minutos": minutos,
            "timer_inicio": inicio_iso,
            "timer_fim": fim_iso,
            "etapa": "ACOMPANHAMENTO",
            "status": "EM_ACOMPANHAMENTO",
            "_historico_tipo": "TIMER_INICIADO",
            "_historico_mensagem": f"Timer de parada iniciado por {minutos} minutos",
            "_audit_operador": operador,
        },
    )
    return {
        "minutos": minutos,
        "inicio": inicio_iso,
        "fim": fim_iso,
    }


def reordenar_ocorrencias(ids):
    ids = [int(item) for item in ids if str(item).isdigit()]
    if not ids:
        return 0

    with get_conn() as conn:
        for ordem, ocorrencia_id in enumerate(ids, start=1):
            conn.execute(
                """
                UPDATE ocorrencias
                   SET ordem_manual = ?,
                       atualizado_em = ?
                 WHERE id = ?
                """,
                (ordem, agora_iso(), ocorrencia_id),
            )

    return len(ids)


def apagar_ocorrencia(ocorrencia_id):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM notas_turno WHERE referencia_tipo = 'OCORRENCIA' AND referencia_id = ?",
            (ocorrencia_id,),
        )
        conn.execute(
            "DELETE FROM timeline_ocorrencias WHERE ocorrencia_id = ?",
            (ocorrencia_id,),
        )
        cur = conn.execute("DELETE FROM ocorrencias WHERE id = ?", (ocorrencia_id,))
        return cur.rowcount


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
        restante = int((timer_fim - agora_dt()).total_seconds())

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
    inicio = agora_dt()
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
        nota_id = inserir_retorna_id(
            conn,
            """
            INSERT INTO notas_turno
                (operador, referencia_tipo, referencia_id, mensagem, apagada, criado_em)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (operador, referencia_tipo, referencia_id, mensagem, agora_iso()),
        )
        if referencia_tipo == "OCORRENCIA" and referencia_id:
            adicionar_timeline_conn(
                conn,
                referencia_id,
                "OBSERVACAO",
                mensagem,
                operador,
                "PAINEL",
            )
        return nota_id


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


def registrar_fim_timer_ocorrencia(ocorrencia_id, timer_inicio, timer_fim):
    if not timer_inicio or not timer_fim:
        return False

    with get_conn() as conn:
        existente = conn.execute(
            """
            SELECT id
              FROM timeline_ocorrencias
             WHERE ocorrencia_id = ?
               AND tipo = 'TIMER_FINALIZADO'
               AND criado_em >= ?
             LIMIT 1
            """,
            (ocorrencia_id, timer_inicio),
        ).fetchone()
        if existente:
            return False
        adicionar_timeline_conn(
            conn,
            ocorrencia_id,
            "TIMER_FINALIZADO",
            "Timer de parada finalizado",
            origem="SISTEMA",
            criado_em=timer_fim,
        )
    return True


def listar_operadores(timeout_online=35):
    limite = agora_dt() - timedelta(seconds=timeout_online)
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
                 WHERE substr(criado_em, 1, 10) = ?
                 GROUP BY operador
                """,
                (hoje_iso(),),
            ).fetchall()
        }

        ocorrencias_por_operador = {
            row["operador"]: {
                "ocorrencias_abertas": int(row["ocorrencias_abertas"] or 0),
                "fadigas_abertas": int(row["fadigas_abertas"] or 0),
            }
            for row in conn.execute(
                """
                SELECT operador,
                       COUNT(*) AS ocorrencias_abertas,
                       SUM(CASE WHEN UPPER(COALESCE(tipo, '')) = 'FADIGA' THEN 1 ELSE 0 END) AS fadigas_abertas
                  FROM ocorrencias
                 WHERE status NOT IN ('FINALIZADA', 'CANCELADA')
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
        segundos_aberto = int((agora_dt() - aberto).total_seconds()) if aberto else 0
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
                "ocorrencias_abertas": ocorrencias_por_operador.get(usuario["nome"], {}).get("ocorrencias_abertas", 0),
                "fadigas_abertas": ocorrencias_por_operador.get(usuario["nome"], {}).get("fadigas_abertas", 0),
                "versao": row["versao"] if row else None,
            }
        )

    return operadores


def enriquecer_ocorrencia(row):
    item = dict(row)
    finalizada = str(item.get("status") or "").upper() in {"FINALIZADA", "CANCELADA"}
    timer_fim = None if finalizada else parse_dt(item["timer_fim"])
    timer_inicio = None if finalizada else parse_dt(item["timer_inicio"])
    restante = None
    timer_estado = "SEM_TIMER"

    if timer_fim:
        restante = int((timer_fim - agora_dt()).total_seconds())
        timer_estado = "RODANDO" if restante > 0 else "VENCIDO"

    duracao_aberta = 0
    # Para a operacao, o SLA conta desde que a ocorrencia entrou no painel.
    # A data/hora do Forms pode ser o horario do evento e ficar fora da janela visual.
    criado = parse_dt(row["criado_em"] or item.get("data_hora"))
    if criado:
        duracao_aberta = int((agora_dt() - criado).total_seconds())

    try:
        campos = json.loads(item.get("campos_adicionais") or "{}")
    except Exception:
        campos = {}

    item["campos_adicionais"] = campos if isinstance(campos, dict) else {}
    item["operador_nome"] = item.get("operador_nome") or item.get("operador") or "-"
    item["operador_email"] = item.get("operador_email") or "N/A"
    item["data_hora"] = item.get("data_hora") or item.get("horario_alerta") or item.get("criado_em")
    item["observacao_inicial"] = item.get("observacao_inicial") or item.get("observacao") or ""
    item["alertas_qtd"] = int(item.get("alertas_qtd") or 1)
    if timer_estado == "VENCIDO":
        registrar_fim_timer_ocorrencia(
            item["id"],
            item.get("timer_inicio"),
            item.get("timer_fim"),
        )
    item["notas"] = listar_notas_referencia("OCORRENCIA", item["id"], limite=12)
    item["timeline"] = listar_timeline_ocorrencia(item["id"], limite=80)
    item["alerta_atrasado"] = bool(not finalizada and duracao_aberta >= 45 * 60)
    item["timer_estado"] = timer_estado
    item["timer_restante_segundos"] = restante
    item["timer_restante"] = formatar_timer(restante) if restante is not None else "-"
    item["timer_percentual"] = calcular_percentual_timer(timer_inicio, timer_fim)
    if finalizada:
        item["timer_minutos"] = None
        item["timer_inicio"] = None
        item["timer_fim"] = None
    item["ocorrencia_segundos"] = max(0, duracao_aberta)
    item["tempo_ocorrencia"] = formatar_duracao(duracao_aberta)
    item["idade"] = formatar_duracao(duracao_aberta)
    return item


def normalizar_horas_historico(valor, padrao=9):
    try:
        horas = int(valor or padrao)
    except Exception:
        horas = padrao

    return horas if horas in {5, 9, 12, 24} else padrao


def listar_ocorrencias(apenas_abertas=False, apenas_finalizadas=False, limite=80, history_hours=9):
    filtros = ["1 = 1"]
    params = []
    history_hours = normalizar_horas_historico(history_hours)
    limite_painel = (agora_dt() - timedelta(hours=history_hours)).isoformat(sep=" ")
    if apenas_abertas:
        filtros.append("o.status NOT IN ('FINALIZADA', 'CANCELADA')")
    elif apenas_finalizadas:
        filtros.append("o.status IN ('FINALIZADA', 'CANCELADA')")

    if apenas_finalizadas:
        campo_historico = "COALESCE(o.finalizado_em, o.atualizado_em, o.criado_em)"
    elif apenas_abertas:
        campo_historico = "COALESCE(o.criado_em, o.atualizado_em, o.data_hora, o.horario_alerta)"
    else:
        campo_historico = """
            CASE
                WHEN o.status IN ('FINALIZADA', 'CANCELADA')
                    THEN COALESCE(o.finalizado_em, o.atualizado_em, o.criado_em)
                ELSE COALESCE(o.criado_em, o.atualizado_em, o.data_hora, o.horario_alerta)
            END
        """
    filtros.append(f"{campo_historico} >= ?")
    params.append(limite_painel)

    where = f"WHERE {' AND '.join(filtros)}"

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
                  CASE WHEN o.status IN ('FINALIZADA', 'CANCELADA') THEN 1 ELSE 0 END,
                  CASE WHEN o.ordem_manual IS NULL THEN 999999 ELSE o.ordem_manual END ASC,
                  COALESCE(o.data_hora, o.horario_alerta, o.criado_em) ASC,
                  o.id ASC
              LIMIT ?
            """,
            params + [limite],
        ).fetchall()

    return [enriquecer_ocorrencia(row) for row in rows]


def listar_ocorrencias_finalizadas(limite=120, history_hours=9):
    return listar_ocorrencias(apenas_finalizadas=True, limite=limite, history_hours=history_hours)


def montar_resumo_turnos(operadores, ocorrencias_abertas, alertas_por_turno=None):
    alertas_por_turno = alertas_por_turno or {}
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
            "alerta_predominante": "-",
            "alerta_predominante_qtd": 0,
            "alertas_por_tipo": [],
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
                "alerta_predominante": "-",
                "alerta_predominante_qtd": 0,
                "alertas_por_tipo": [],
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

    for nome_turno, turno in turnos.items():
        tipos = alertas_por_turno.get(nome_turno, {})
        ordenados = sorted(tipos.items(), key=lambda item: item[1], reverse=True)
        turno["alertas_por_tipo"] = [
            {"tipo": tipo, "total": total}
            for tipo, total in ordenados
        ]
        if ordenados:
            turno["alerta_predominante"] = ordenados[0][0]
            turno["alerta_predominante_qtd"] = ordenados[0][1]

    return [turnos[turno] for turno in TURNOS_ORDEM if turno in turnos]


def contar_alertas_por_turno_hoje():
    operadores = listar_usuarios_cadastrados()
    admin_por_nome = {op["nome"]: op.get("admin", False) for op in operadores}
    resumo = {turno: {} for turno in TURNOS_ORDEM}

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT operador, tipo, COUNT(*) AS total
              FROM alertas_tratados
              WHERE substr(criado_em, 1, 10) = ?
             GROUP BY operador, tipo
            """,
            (hoje_iso(),),
        ).fetchall()

    for row in rows:
        operador = row["operador"]
        turno = turno_operador(operador, admin_por_nome.get(operador, False))
        if turno not in resumo:
            resumo[turno] = {}

        tipo = (row["tipo"] or "NAO INFORMADO").upper()
        resumo[turno][tipo] = resumo[turno].get(tipo, 0) + int(row["total"] or 0)

    return resumo


def resumo_dashboard(history_hours=9):
    history_hours = normalizar_horas_historico(history_hours)
    operadores = listar_operadores()
    ocorrencias_abertas = listar_ocorrencias(apenas_abertas=True, limite=80, history_hours=history_hours)
    ocorrencias_finalizadas = listar_ocorrencias_finalizadas(limite=160, history_hours=history_hours)
    admins = [op for op in operadores if op.get("admin")]
    usuarios = [op for op in operadores if not op.get("admin")]

    with get_conn() as conn:
        total_tratados_hoje = conn.execute(
            """
            SELECT COUNT(*) AS total
              FROM alertas_tratados
             WHERE substr(criado_em, 1, 10) = ?
            """,
            (hoje_iso(),),
        ).fetchone()["total"]

        fadigas_hoje = conn.execute(
            """
            SELECT COUNT(*) AS total
              FROM ocorrencias
             WHERE tipo = 'FADIGA'
               AND substr(criado_em, 1, 10) = ?
            """,
            (hoje_iso(),),
        ).fetchone()["total"]

    online = [op for op in operadores if op["online"]]
    offline = [op for op in operadores if not op["online"]]
    ocorrencias_alerta = [oc for oc in ocorrencias_abertas if oc.get("alerta_atrasado")]
    alertas_por_turno = contar_alertas_por_turno_hoje()
    turnos = montar_resumo_turnos(operadores, ocorrencias_abertas, alertas_por_turno)

    return {
        "agora": agora_iso(),
        "history_hours": history_hours,
        "operadores": operadores,
        "admins": admins,
        "usuarios": usuarios,
        "turnos": turnos,
        "operadores_online": len(online),
        "operadores_offline": len(offline),
        "operadores_cadastrados": len(operadores),
        "alertas_tratados_hoje": total_tratados_hoje,
        "fadigas_hoje": fadigas_hoje,
        "ocorrencias_alerta": ocorrencias_alerta,
        "ocorrencias_abertas": ocorrencias_abertas,
        "ocorrencias_finalizadas": ocorrencias_finalizadas,
        "ocorrencias_operacao": ocorrencias_abertas + ocorrencias_finalizadas,
        "alertas_por_turno": alertas_por_turno,
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

    passado = (agora_dt() - inicio_dt).total_seconds()
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
