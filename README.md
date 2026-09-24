# Portal Linha de Frente

Portal de notícias esportivas da Linha de Frente, desenvolvido em Django.

## Executar localmente

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

O endpoint inicial fica disponível em `http://127.0.0.1:8000/` e retorna `{"status": "ok"}`.

## Testes

```bash
python manage.py test
```
