# Cron Manager API

Aplicação minimalista para gerenciar cron jobs via API REST em container Alpine Linux.

## Características

- 🐳 Container Alpine Linux (imagem mínima)
- 🚀 API REST com Flask
- ⏰ Gerenciamento completo de cron jobs (CRUD)
- ✅ Validação de expressões cron
- 💾 Persistência de dados
- 📝 Logs de execução

## Endpoints da API

### 1. Criar agendamento
```bash
POST /api/cron
Content-Type: application/json

{
  "name": "backup-diario",
  "schedule": "0 2 * * *",
  "command": "/usr/local/bin/backup.sh"
}
```

### 2. Listar agendamentos
```bash
GET /api/cron
```

### 3. Obter agendamento específico
```bash
GET /api/cron/{id}
```

### 4. Alterar agendamento
```bash
PUT /api/cron/{id}
Content-Type: application/json

{
  "name": "backup-diario-atualizado",
  "schedule": "0 3 * * *",
  "command": "/usr/local/bin/backup-v2.sh"
}
```

### 5. Excluir agendamento
```bash
DELETE /api/cron/{id}
```

### 6. Health check
```bash
GET /health
```

## Como usar

### Usando Docker Compose (recomendado)

```bash
docker-compose up -d
```

### Usando Docker diretamente

```bash
# Build
docker build -t cron-manager .

# Run
docker run -d -p 5000:5000 --name cron-manager cron-manager
```

## Exemplos de uso

### Criar um backup diário às 2h da manhã
```bash
curl -X POST http://localhost:5000/api/cron \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backup-diario",
    "schedule": "0 2 * * *",
    "command": "echo \"Executando backup $(date)\" >> /var/log/backup.log"
  }'
```

### Listar todos os agendamentos
```bash
curl http://localhost:5000/api/cron
```

### Atualizar agendamento
```bash
curl -X PUT http://localhost:5000/api/cron/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backup-atualizado",
    "schedule": "0 3 * * *",
    "command": "echo \"Novo backup $(date)\" >> /var/log/backup.log"
  }'
```

### Excluir agendamento
```bash
curl -X DELETE http://localhost:5000/api/cron/1
```

## Formato de expressão cron

```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Dia da semana (0-7, 0 e 7 = Domingo)
│ │ │ └───── Mês (1-12)
│ │ └─────── Dia do mês (1-31)
│ └───────── Hora (0-23)
└─────────── Minuto (0-59)
```

### Exemplos:
- `0 2 * * *` - Todo dia às 2h da manhã
- `*/15 * * * *` - A cada 15 minutos
- `0 0 * * 0` - Todo domingo à meia-noite
- `0 9-17 * * 1-5` - Às horas inteiras das 9h às 17h, de segunda a sexta

## Logs

Os logs do cron ficam disponíveis em:
```bash
docker logs cron-manager
```

## Volumes

Os dados são persistidos em:
- `/data/cron.json` - Configurações dos cron jobs
- `/var/log/cron.log` - Logs de execução

## Tecnologias

- Alpine Linux 3.19
- Python 3.11
- Flask 3.0
- Cronie (cron daemon)