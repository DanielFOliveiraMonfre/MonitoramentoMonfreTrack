# MonfreTrack Central - Flask

Painel operacional para operadores online, alertas tratados, ocorrências e troca de turno.

## Como Rodar Local

```powershell
cd "C:\Users\DANIEL.OLIVEIRA\OneDrive - MONFREDINI TRANSPORTES LTDA\Área de Trabalho\painel_flask"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra:

```text
http://127.0.0.1:5000
```

## Persistência No Render

Para produção no Render, use PostgreSQL. Não use SQLite local como fonte principal de histórico, porque deploy/restart pode recriar a pasta do projeto.

Configure:

```text
DATABASE_URL=postgresql://usuario:senha@host:porta/banco
MONFRETRACK_TZ=America/Sao_Paulo
```

O endpoint do Power Automate só responde sucesso depois que a ocorrência é salva no banco.

## Telas

- `/` mostra o dashboard geral.
- `/operacao` mostra a fila de ocorrências recebidas do Forms/Power Automate.
- `/troca-turno` mostra o chat de repasse.

## APIs Principais

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

### Contador De Alerta Tratado

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

### Receber Ocorrência Do Forms / Power Automate

```http
POST /api/forms/ocorrencia
POST /api/power-automate/ocorrencia
```

```json
{
  "texto": "Registro feito por: Filipe Brito - filipe.brito@monfredinitransportes.com.br\nEvento: PARADA PREVENTIVA\nPlaca: UEQ7B48\nMotorista: IDEILDO SILVA TELES\nData/Hora: 28/05/2026 06:54\nObservação: Aguardando retorno."
}
```

### Atualizar Ocorrência

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

### Iniciar Timer

```http
POST /api/ocorrencias/1/timer
```

```json
{
  "minutos": 10
}
```
