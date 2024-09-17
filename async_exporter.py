import os
import asyncio
import httpx
from datetime import datetime, timedelta
from prometheus_client import Gauge, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
import uvicorn
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
import logging

# Configuration
ENDPOINT = "https://hydro-back.imgw.pl/station/hydro/status"
STATION_ID = os.getenv('STATION_ID')

if not STATION_ID:
    raise ValueError("Environment variable 'STATION_ID' is not set")

# Split STATION_ID into a list
STATION_IDS = [id.strip() for id in STATION_ID.split(',')]

# Create a custom CollectorRegistry
registry = CollectorRegistry()

# Store the last update time
last_update_time = None
fetch_lock = asyncio.Lock()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the metrics dict to hold our metrics
metrics = {}

async def fetch_data():
    global last_update_time
    async with fetch_lock:
        try:
            async with httpx.AsyncClient() as client:
                tasks = []
                for station_id in STATION_IDS:
                    params = {'id': station_id}
                    tasks.append(client.get(ENDPOINT, params=params))
                responses = await asyncio.gather(*tasks, return_exceptions=True)

            for response, station_id in zip(responses, STATION_IDS):
                if isinstance(response, Exception):
                    logger.error(f"Error fetching data for station {station_id}: {response}")
                    continue
                try:
                    if response.status_code != 200:
                        logger.error(f"Received status code {response.status_code} for station {station_id}")
                        continue

                    try:
                        data = response.json()
                    except ValueError as e:
                        logger.error(f"Error parsing JSON for station {station_id}: {e}")
                        logger.debug(f"Response content: {response.text}")
                        continue

                    if not data:
                        logger.error(f"No data received for station {station_id}")
                        continue

                    status = data.get('status', {})
                    if not status:
                        logger.error(f"No 'status' in data for station {station_id}")
                        logger.debug(f"Data received: {data}")
                        continue

                    properties = data.get('properties', {})

                    station_id = data.get('id', 'unknown')
                    station_name = status.get('description', 'unknown')

                    state_code = data.get('stateCode', 'unknown')

                    current_state = status.get('currentState', {})
                    current_value = current_state.get('value', 0)

                    trend_value = status.get('trend', 0)
                    status_value = status.get('status', 0)
                    alarm_val = status.get('alarmValue', 0)
                    warning_val = status.get('warningValue', 0)

                    # Update metrics
                    metrics['current_state_value'].labels(station_id=station_id, station_name=station_name, state_code=state_code).set(current_value)
                    metrics['trend'].labels(station_id=station_id, station_name=station_name, state_code=state_code).set(trend_value)
                    metrics['status_metric'].labels(station_id=station_id, station_name=station_name, state_code=state_code).set(status_value)
                    metrics['alarm_value'].labels(station_id=station_id, station_name=station_name, state_code=state_code).set(alarm_val)
                    metrics['warning_value'].labels(station_id=station_id, station_name=station_name, state_code=state_code).set(warning_val)

                    logger.info(f"Metrics updated for station {station_id} - {station_name}")

                except Exception as e:
                    logger.error(f"Error processing data for station {station_id}: {e}")
                    logger.debug(f"Data causing error: {data}")

            last_update_time = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error fetching data: {e}")

async def schedule_fetch():
    while True:
        now = datetime.utcnow()
        # Calculate time until the next 5-minute interval
        next_run = (now.replace(second=0, microsecond=0) + timedelta(minutes=5 - now.minute % 5))
        wait_time = (next_run - now).total_seconds()
        logger.info(f"Next data update at {next_run} (in {wait_time} seconds)")
        await asyncio.sleep(wait_time)
        await fetch_data()

# Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    global metrics
    # Define metrics within the lifespan to ensure they're registered only once
    metrics = {
        'current_state_value': Gauge('current_state_value', 'Current state value', ['station_id', 'station_name', 'state_code'], registry=registry),
        'trend': Gauge('trend', 'Trend', ['station_id', 'station_name', 'state_code'], registry=registry),
        'status_metric': Gauge('status', 'Status', ['station_id', 'station_name', 'state_code'], registry=registry),
        'alarm_value': Gauge('alarm_value', 'Alarm value', ['station_id', 'station_name', 'state_code'], registry=registry),
        'warning_value': Gauge('warning_value', 'Warning value', ['station_id', 'station_name', 'state_code'], registry=registry),
    }

    # Startup code
    await fetch_data()
    # Start scheduled data fetching
    task = asyncio.create_task(schedule_fetch())
    try:
        yield
    finally:
        # Shutdown code
        task.cancel()
        await task

# Create FastAPI application with lifespan
app = FastAPI(lifespan=lifespan)

# Create an endpoint to expose metrics
@app.get("/metrics")
async def metrics_endpoint():
    output = generate_latest(registry)
    return Response(content=output, media_type=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    uvicorn.run("async_exporter:app", host="0.0.0.0", port=8000)
