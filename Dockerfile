FROM python:3.12-slim

WORKDIR /app
COPY connector/ /app/

ENV PORT=8000
EXPOSE 8000
VOLUME /app/data

CMD ["python3", "server.py"]
