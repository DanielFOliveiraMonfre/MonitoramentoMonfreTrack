# -*- coding: utf-8 -*-

import re
import unicodedata
from datetime import datetime


CAMPOS_ADICIONAIS_PADRAO = {
    "contrato_programacao": "Contrato da Programacao de Carga",
    "programacao_carga": "Programacao de Carga",
    "tempo_direcao_continua": "Tempo de direcao continua",
    "tempo_margem": "Tempo de margem",
    "tempo_estimado_destino": "Tempo estimado para o destino",
    "motorista_sinal_fadiga": "Motorista apresenta sinal de fadiga",
    "cobertura_celular": "Celular esta com area de cobertura",
    "motorista_atendeu": "Motorista atendeu a ligacao",
    "mensagem_sirene": "Foi enviado mensagens e sirene",
    "motorista_aceitou_parar": "Motorista aceitou parar",
    "programacao_acionada": "Setor Programacao foi acionado",
    "programador": "Qual programador nos atendeu",
}


MAPA_CAMPOS = {
    "contrato da programacao de carga": "contrato_programacao",
    "programacao de carga": "programacao_carga",
    "tempo de direcao continua": "tempo_direcao_continua",
    "tempo de margem": "tempo_margem",
    "tempo estimado para o destino": "tempo_estimado_destino",
    "motorista apresenta sinal de fadiga": "motorista_sinal_fadiga",
    "celular esta com area de cobertura": "cobertura_celular",
    "motorista atendeu a ligacao": "motorista_atendeu",
    "foi enviado mensagens e sirene": "mensagem_sirene",
    "motorista aceitou parar": "motorista_aceitou_parar",
    "setor programacao foi acionado": "programacao_acionada",
    "qual programador nos atendeu": "programador",
}


def valor_ou_na(valor):
    texto = str(valor or "").strip()
    return texto if texto else "N/A"


def normalizar_chave(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.lower().strip()
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.replace("?", "").replace(":", "")
    return texto


def slug_operador(nome, email=None):
    if email and "@" in email:
        return email.split("@", 1)[0].strip().lower()

    texto = unicodedata.normalize("NFKD", str(nome or "sem.operador"))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-zA-Z0-9]+", ".", texto).strip(".").lower()
    return texto or "sem.operador"


def limpar_valor(valor):
    texto = str(valor or "").strip()
    texto = re.sub(r"\[([^\]]+)\]\(mailto:[^)]+\)", r"\1", texto, flags=re.I)
    texto = texto.replace("(mailto:", "").replace(")", "")
    return texto.strip()


def parse_operador(valor):
    texto = limpar_valor(valor)
    email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", texto)
    email = email_match.group(0).lower() if email_match else "N/A"

    nome = texto
    if " - " in nome:
        nome = nome.split(" - ", 1)[0]
    elif email_match:
        nome = nome[:email_match.start()]

    nome = re.sub(r"\s+", " ", nome).strip(" -[]")
    return valor_ou_na(nome), valor_ou_na(email)


def parse_data_hora(valor):
    texto = str(valor or "").strip()
    if not texto:
        return "N/A"

    formatos = [
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ]
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).isoformat(sep=" ")
        except ValueError:
            continue

    return texto


def pares_linhas(texto):
    campos = {}
    for linha in str(texto or "").splitlines():
        linha = linha.strip()
        if not linha or ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        campos[normalizar_chave(chave)] = limpar_valor(valor)
    return campos


def normalizar_payload_direto(payload):
    campos = {
        chave: valor_ou_na(payload.get(chave))
        for chave in CAMPOS_ADICIONAIS_PADRAO
    }
    extras = payload.get("campos_adicionais") or {}
    if isinstance(extras, dict):
        for chave in CAMPOS_ADICIONAIS_PADRAO:
            if chave in extras:
                campos[chave] = valor_ou_na(extras.get(chave))

    operador_nome = payload.get("operador_nome")
    operador_email = payload.get("operador_email")
    if not operador_nome and payload.get("registro_feito_por"):
        operador_nome, operador_email = parse_operador(payload.get("registro_feito_por"))

    return {
        "evento": valor_ou_na(payload.get("evento") or payload.get("tipo")).upper(),
        "placa": valor_ou_na(payload.get("placa")),
        "motorista": valor_ou_na(payload.get("motorista")),
        "data_hora": parse_data_hora(payload.get("data_hora") or payload.get("data/hora")),
        "operador_nome": valor_ou_na(operador_nome),
        "operador_email": valor_ou_na(operador_email),
        "operador": slug_operador(operador_nome, operador_email),
        "campos_adicionais": campos,
        "observacao_inicial": valor_ou_na(payload.get("observacao") or payload.get("observacao_inicial")),
    }


def parse_forms_text(texto):
    campos_linha = pares_linhas(texto)
    registro = campos_linha.get("registro feito por", "")
    operador_nome, operador_email = parse_operador(registro)

    adicionais = {}
    for chave_final, _label in CAMPOS_ADICIONAIS_PADRAO.items():
        adicionais[chave_final] = "N/A"

    for chave_linha, valor in campos_linha.items():
        chave_final = MAPA_CAMPOS.get(chave_linha)
        if chave_final:
            adicionais[chave_final] = valor_ou_na(valor)

    return {
        "evento": valor_ou_na(campos_linha.get("evento")).upper(),
        "placa": valor_ou_na(campos_linha.get("placa")).upper(),
        "motorista": valor_ou_na(campos_linha.get("motorista")),
        "data_hora": parse_data_hora(campos_linha.get("data/hora") or campos_linha.get("data hora")),
        "operador_nome": operador_nome,
        "operador_email": operador_email,
        "operador": slug_operador(operador_nome, operador_email),
        "campos_adicionais": adicionais,
        "observacao_inicial": valor_ou_na(campos_linha.get("observacao")),
    }


def parse_forms_payload(payload):
    payload = payload or {}
    texto = (
        payload.get("texto")
        or payload.get("mensagem")
        or payload.get("message")
        or payload.get("body")
        or payload.get("text")
    )

    if texto:
        return parse_forms_text(texto)

    return normalizar_payload_direto(payload)
