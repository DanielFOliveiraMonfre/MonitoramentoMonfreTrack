# MonfreTrack Central - Flask

Painel operacional para operadores online, alertas tratados, ocorrencias e troca de turno.

## Como rodar local

```powershell
cd "C:\caminho\painel_flask"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`.

## Render e persistencia

Em producao, use PostgreSQL. O SQLite local do Render nao deve ser usado como fonte principal, pois pode ser perdido em reinicios e deploys.

Variaveis obrigatorias:

```text
DATABASE_URL=postgresql://usuario:senha@host:porta/banco
MONFRETRACK_TZ=America/Sao_Paulo
FORMS_PLANILHA_URL=https://link-compartilhado-do-sharepoint?e=TOKEN&download=1
FORMS_PLANILHA_INTERVALO=15
FORMS_PLANILHA_FONTE=forms_ocorrencias
WEB_CONCURRENCY=1
```

O link da planilha deve ficar somente nas variaveis de ambiente do Render. Nao publique o link no codigo ou no GitHub.

## Origem das ocorrencias

As ocorrencias sao criadas exclusivamente pela planilha Excel ligada ao Microsoft Forms.

Na primeira sincronizacao, o maior `Id` existente vira a linha de corte e nenhuma resposta antiga e importada. Depois disso, somente linhas com `Id` maior sao processadas. O ultimo ID e cada linha importada ficam persistidos no PostgreSQL.

O executavel MonfreTrack continua enviando:

- heartbeat e status do operador;
- contador de alertas tratados.

O executavel nao cria mais ocorrencias. As rotas antigas `POST /api/ocorrencias`, `POST /api/forms/ocorrencia` e `POST /api/power-automate/ocorrencia` retornam HTTP 410.

## Telas

- `/` mostra o dashboard geral.
- `/operacao` mostra a fila de ocorrencias recebidas do Excel do Forms.
- `/troca-turno` mostra o chat de repasse.

## APIs principais

### Heartbeat

```http
POST /api/heartbeat
```

### Contador de alerta tratado

```http
POST /api/alerta-tratado
```

Esse endpoint atualiza apenas o contador e nao cria ocorrencia.

### Status da sincronizacao Excel

```http
GET /api/sincronizacao-excel
```

Mostra o ultimo ID lido, horario da ultima sincronizacao e eventual erro.

### Executar sincronizacao agora

```http
POST /api/sincronizacao-excel/executar
```

Exige usuario administrador.

### Atualizar ocorrencia

```http
PATCH /api/ocorrencias/1
```

### Iniciar timer

```http
POST /api/ocorrencias/1/timer
```
