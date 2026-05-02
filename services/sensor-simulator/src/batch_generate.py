import os
import json
import logging
import requests
import redis
import sys
import argparse
import random
from datetime import datetime, timedelta
from sensor_generator import SensorGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("batch-generator")

# Configuration from environment
REDIS_URL_ENV = os.environ.get("REDIS_URL", "redis://redis:6379/0")
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://user-service:5005")
CHANNEL = os.environ.get("REDIS_CHANNEL_SENSOR_DATA", "sensor:data")

def get_zones_from_api():
    """Fetch active zones from the user service."""
    try:
        response = requests.get(f"{USER_SERVICE_URL}/v1/zones", timeout=5)
        response.raise_for_status()
        zones = response.json()
        return [z for z in zones if z.get("active", True)]
    except Exception as e:
        logger.error(f"Failed to fetch zones from {USER_SERVICE_URL}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Generate a batch of sensor readings.")
    parser.add_argument("--count", type=int, default=100, help="Number of readings per sensor")
    parser.add_argument("--interval", type=int, default=60, help="Simulated seconds between readings")
    args = parser.parse_args()

    logger.info(f"Connecting to Redis at {REDIS_URL_ENV}")
    try:
        r = redis.from_url(REDIS_URL_ENV, decode_responses=True)
        r.ping()
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    active_zones = get_zones_from_api()
    if not active_zones:
        logger.warning("No active zones found. Exiting.")
        return

    logger.info(f"Found {len(active_zones)} active zones. Generating {args.count} readings for each (2 sensors per zone).")

    total_published = 0
    # Use a fixed start time in the past to simulate historical data
    start_time = datetime.utcnow() - timedelta(seconds=args.count * args.interval)

    # Sort zones to ensure consistent generation if needed
    for z in active_zones:
        zid = z.get("zone_id")
        soil_type = z.get("soil_type", "loam").lower()
        
        sensors = [
            SensorGenerator(zone_id=zid, sensor_id=f"{zid}-s1", soil_type=soil_type),
            SensorGenerator(zone_id=zid, sensor_id=f"{zid}-s2", soil_type=soil_type)
        ]

        current_sim_time = start_time
        for i in range(args.count):
            # Add some jitter to the interval (up to 10% variance) to make it look "normal"
            jitter = random.uniform(-args.interval * 0.1, args.interval * 0.1)
            current_sim_time += timedelta(seconds=args.interval + jitter)
            timestamp_str = current_sim_time.isoformat() + "Z"
            
            for gen in sensors:
                reading = gen.generate_reading()
                # Override timestamp with simulated time
                reading.timestamp = timestamp_str
                
                payload = reading.model_dump_json()
                r.publish(CHANNEL, payload)
                total_published += 1

    logger.info(f"Successfully published {total_published} readings to {CHANNEL}.")

if __name__ == "__main__":
    main()
