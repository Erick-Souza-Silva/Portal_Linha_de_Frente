# Executar o projeto

Este é um projeto Django. O workflow do Replit executa as migrações e inicia o
servidor em `0.0.0.0:5000`, que é a porta usada pelo preview web.

Para executar manualmente:

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:5000
```

O endpoint de verificação está disponível em `/health/` e retorna
`{"status": "ok"}`.

As configurações opcionais podem ser definidas por variáveis de ambiente:

- `DJANGO_SECRET_KEY` (usa `SESSION_SECRET` do Replit como alternativa)
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_ENV`
- `DJANGO_DEBUG`