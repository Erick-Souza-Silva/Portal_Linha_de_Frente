---
name: Produção no Replit
description: Regras duráveis para banco, proxy HTTPS e publicação deste projeto no Replit.
---

O projeto deve usar o PostgreSQL gerenciado quando `DATABASE_URL` estiver disponível. A publicação deve usar Gunicorn, servir estáticos coletados e confiar no cabeçalho HTTPS encaminhado pelo proxy.

**Why:** O workflow local pode iniciar antes de uma troca de banco terminar, e `SECURE_SSL_REDIRECT` faz verificações diretas em HTTP parecerem falhas quando não simulam o proxy. O schema de produção é sincronizado pelo fluxo Publish do Replit, não por DDL no comando de inicialização.

**How to apply:** Aplique migrações no banco de desenvolvimento antes de publicar, valide o endpoint usando o proxy HTTPS ou `X-Forwarded-Proto: https`, e não adicione `migrate` ao comando de produção. Configure `DJANGO_ALLOWED_HOSTS` e SMTP por Secrets antes do primeiro Publish.