import os
import time
import json
import logging
import requests
import redis
from sensor_generator import SensorGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sensor-simulator")

# Configuration from environment
REDIS_URL_ENV = os.environ.get("REDIS_URL", "redis://redis:6379/0")
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://user-service:5005")
TICK_INTERVAL = float(os.environ.get("SENSOR_PUBLISH_INTERVAL", 10.0))

# Redis channel
CHANNEL = os.environ.get("REDIS_CHANNEL_SENSOR_DATA", "sensor:data")

def get_zones_from_api():
    """Fetch active zones from the user service."""
    try:
        response = requests.get(f"{USER_SERVICE_URL}/v1/zones", timeout=5)
        response.raise_for_status()
        zones = response.json()
        # Filter only active zones
        return [z for z in zones if z.get("active", True)]
    except Exception as e:
        logger.error(f"Failed to fetch zones from {USER_SERVICE_URL}: {e}")
        return []

def main():
    logger.info(f"Starting sensor simulator... Connecting to Redis at {REDIS_URL_ENV}")
    
    # Connect to Redis
    try:
        r = redis.from_url(REDIS_URL_ENV, decode_responses=True)
        r.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        # We will keep trying in the main loop anyway
        r = redis.from_url(REDIS_URL_ENV, decode_responses=True)

    generators = {}
    last_zone_sync = 0

    while True:
        current_time = time.time()
        
        # Sync zones every 60 seconds
        if current_time - last_zone_sync > 60:
            logger.info("Syncing zones from API...")
            active_zones = get_zones_from_api()
            
            if not active_zones and not generators:
                logger.warning("No active zones found and no generators initialized. Waiting...")
            
            if active_zones:
                active_zone_ids = {z.get("zone_id") for z in active_zones}
                
                # Add new generators
                for z in active_zones:
                    zid = z.get("zone_id")
                    if zid not in generators:
                        soil_type = z.get("soil_type", "loam").lower()
                        # Create 2 sensors per zone for redundancy simulation
                        generators[zid] = [
                            SensorGenerator(zone_id=zid, sensor_id=f"{zid}-s1", soil_type=soil_type),
                            SensorGenerator(zone_id=zid, sensor_id=f"{zid}-s2", soil_type=soil_type)
                        ]
                        logger.info(f"Initialized sensors for new zone: {zid} (Soil: {soil_type})")
                
                # Remove removed/inactive zones
                for zid in list(generators.keys()):
                    if zid not in active_zone_ids:
                        logger.info(f"Removing sensors for inactive zone: {zid}")
                        del generators[zid]
            
            last_zone_sync = current_time

        # Generate and publish readings
        published_count = 0
        for zid, zone_generators in generators.items():
            for gen in zone_generators:
                try:
                    reading = gen.generate_reading()
                    payload = reading.model_dump_json()
                    r.publish(CHANNEL, payload)
                    published_count += 1
                except Exception as e:
                    logger.error(f"Error publishing reading for {gen.sensor_id}: {e}")

        if published_count > 0:
            logger.debug(f"Published {published_count} readings.")
            
        time.sleep(TICK_INTERVAL)

if __name__ == "__main__":
    main()
