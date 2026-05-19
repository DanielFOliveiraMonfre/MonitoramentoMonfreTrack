# -*- coding: utf-8 -*-

import socket
import threading
import time
from datetime import datetime

import requests


class FlaskClient:
    def __init__(self, servidor="http://127.0.0.1:5000", operador="sem.operador", versao="1.0"):
        self.servidor = servidor.rstrip("/")
        self.operador = (operador or "sem.operador").strip().lower()
        self.maquina = socket.gethostname().upper()
        self.versao = versao
        self.status = "ABERTO"
        self._rodando = False
        self._thread = None

    def iniciar(self):
        if self._rodando:
            return

        self._rodando = True
        self._thread = threading.Thread(target=self._loop_heartbeat, daemon=True)
        self._thread.start()

    def parar(self):
        self._rodando = False

    def atualizar_status(self, status):
        self.status = (status or "ABERTO").upper()
        self.heartbeat()

    def heartbeat(self):
        return self._post(
            "/api/heartbeat",
            {
                "operador": self.operador,
                "maquina": self.maquina,
                "status": self.status,
                "versao": self.versao,
            },
        )

    def alerta_tratado(self, tipo, placa="-", motorista="Motorista nao identificado"):
        return self._post(
            "/api/alerta-tratado",
            {
                "operador": self.operador,
                "maquina": self.maquina,
                "tipo": tipo,
                "placa": placa,
                "motorista": motorista,
            },
        )

    def criar_ocorrencia_fadiga(self, placa, motorista, external_id=None, horario_alerta=None):
        return self._post(
            "/api/ocorrencias",
            {
                "external_id": external_id,
                "tipo": "FADIGA",
                "placa": placa,
                "motorista": motorista,
                "operador": self.operador,
                "maquina": self.maquina,
                "horario_alerta": horario_alerta or datetime.now().replace(microsecond=0).isoformat(sep=" "),
                "status": "ABERTA",
                "etapa": "AGUARDANDO_CONTATO",
                "contato_status": "PENDENTE",
                "parada_status": "PENDENTE",
            },
        )

    def atualizar_ocorrencia(self, ocorrencia_id, **campos):
        return self._patch(f"/api/ocorrencias/{ocorrencia_id}", campos)

    def iniciar_timer(self, ocorrencia_id, minutos):
        return self._post(f"/api/ocorrencias/{ocorrencia_id}/timer", {"minutos": minutos})

    def _loop_heartbeat(self):
        while self._rodando:
            self.heartbeat()
            time.sleep(10)

    def _post(self, endpoint, payload):
        try:
            r = requests.post(f"{self.servidor}{endpoint}", json=payload, timeout=2)
            return r.json()
        except Exception:
            return {"ok": False}

    def _patch(self, endpoint, payload):
        try:
            r = requests.patch(f"{self.servidor}{endpoint}", json=payload, timeout=2)
            return r.json()
        except Exception:
            return {"ok": False}

