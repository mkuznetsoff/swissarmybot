FROM jrottenberg/ffmpeg:4.4-ubuntu as ffmpeg

FROM python:3.10-slim

COPY --from=ffmpeg /usr/local /usr/local

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY . .

CMD ["python", "main.py"]
