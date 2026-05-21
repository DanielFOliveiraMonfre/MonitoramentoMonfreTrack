# MonfreTrack Central - Flask

Painel local para apresentar operadores online, alertas tratados e ocorrencias de fadiga.

## Como rodar

```powershell
cd C:\Users\DANIEL.OLIVEIRA\Documents\Codex\2026-05-12\oi\painel_flask
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra:

```text
http://127.0.0.1:5000
```

## Persistência no Render

Por padrão o painel usa `painel.db` dentro da pasta do projeto. Em serviços como Render, essa pasta pode ser recriada em deploy/restart e apagar os dados. Para manter histórico, configure um caminho persistente:

```text
PAINEL_DB_PATH=/var/data/painel.db
MONFRETRACK_TZ=America/Sao_Paulo
```

Depois monte um Persistent Disk em `/var/data` ou use outro armazenamento persistente equivalente.

Se quiser abrir em outro computador da mesma rede, use o IP do seu PC:

```text
http://SEU_IP:5000
```

## Telas

- `/` mostra dashboard geral.
- `/operacao` mostra a fila de ocorrencias de fadiga.

## API principal

### Heartbeat

```http
POST /api/heartbeat
```

```json
{
  "operador": "daniel.oliveira",
  "maquina": "MONITOR-01",
  "status": "RODANDO",
  "versao": "1.0"
}
```

### Contador de alerta tratado

```http
POST /api/alerta-tratado
```

```json
{
  "operador": "daniel.oliveira",
  "maquina": "MONITOR-01",
  "tipo": "FADIGA",
  "placa": "QSS7G98",
  "motorista": "EDVANIO DIAS DA SILVA"
}
```

### Criar ocorrencia de fadiga

```http
POST /api/ocorrencias
```

```json
{
  "external_id": "QSS7G98-1710000000",
  "tipo": "FADIGA",
  "placa": "QSS7G98",
  "motorista": "EDVANIO DIAS DA SILVA",
  "operador": "daniel.oliveira",
  "maquina": "MONITOR-01",
  "status": "ABERTA",
  "etapa": "AGUARDANDO_CONTATO",
  "contato_status": "PENDENTE",
  "parada_status": "PENDENTE"
}
```

### Atualizar ocorrencia

```http
PATCH /api/ocorrencias/1
```

```json
{
  "status": "EM_ACOMPANHAMENTO",
  "etapa": "ACOMPANHAMENTO",
  "contato_status": "CONTATO_FEITO",
  "parada_status": "ACEITOU_PARAR"
}
```

### Iniciar timer

```http
POST /api/ocorrencias/1/timer
```

```json
{
  "minutos": 10
}
```
