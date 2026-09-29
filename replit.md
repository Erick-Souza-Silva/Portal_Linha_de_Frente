# Executar o projeto

Este é um projeto Django. O workflow do Replit executa as migrações do banco de
desenvolvimento e inicia o servidor em `0.0.0.0:5000`, que é a porta usada pelo
preview web.

Para executar manualmente:

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:5000
```

O endpoint de verificação está disponível em `/health/` e retorna
`{"status": "ok"}`.

## Banco de dados

Quando `DATABASE_URL` está disponível, o Django usa o PostgreSQL gerenciado do
Replit. Sem essa variável, ele mantém SQLite como fallback local. O schema vem
das migrações versionadas em `core/migrations/`.

Antes da publicação, o banco de desenvolvimento deve estar com as migrações
aplicadas. O Publish do Replit sincroniza o schema com o banco de produção.

## Autenticação e segurança

- O cadastro deixa a conta inativa até o link de confirmação de e-mail ser
  usado. O backend de console serve apenas para desenvolvimento.
- Em produção, configure um SMTP com `EMAIL_HOST`, `EMAIL_PORT`,
  `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e
  `DEFAULT_FROM_EMAIL` usando Secrets do Replit.
- O usuário pode ativar MFA TOTP em `/seguranca/mfa/`. O login exige o código
  de seis dígitos quando o MFA estiver ativo.
- A MFA da conta Replit é independente desta aplicação e deve ser ativada nas
  configurações da conta Replit; o código Django não controla a conta da
  plataforma.

## Publicação

O servidor publicado usa Gunicorn e o build coleta os arquivos estáticos:

```bash
python manage.py collectstatic --noinput
gunicorn --bind 0.0.0.0:5000 --workers 2 config.wsgi:application
```

Em produção, configure `DJANGO_ENV=production`, `DJANGO_DEBUG=false`,
`DJANGO_ALLOWED_HOSTS` com o domínio publicado e `DJANGO_SECRET_KEY` como
Secret. Não use a chave de desenvolvimento nem o backend de e-mail do console.

As configurações opcionais podem ser definidas por variáveis de ambiente:

- `DJANGO_SECRET_KEY` (usa `SESSION_SECRET` do Replit como alternativa)
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_ENV`
- `DJANGO_DEBUG`
- `DATABASE_URL` (fornecida pelo PostgreSQL gerenciado do Replit)