FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV STATION_ID=

EXPOSE 8000

CMD ["python", "async_exporter.py"]
