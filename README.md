# peer_review_bot

Telegram-бот для peer-review проверки заданий курса DL in NLP

## Usage

Положить в файл .env переменные `PRB_TOKEN` (токен бота) и `PRB_PROXY` (адрес proxy).
Можно не указывать proxy, но тогда нужно прописать с config `use_proxy = False`

#### docker compose-way:
```docker compose up .```

#### python-way:

1. Поднять mongodb
1. ```python main.py```
