FROM python:3

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8012

CMD [ "python", "peer_review_bot/telegram_ui.py"]