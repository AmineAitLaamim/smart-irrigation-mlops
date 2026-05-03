import random
import time
from datetime import datetime
from pydantic import BaseModel

class SensorReading(BaseModel):
    zone_id: str
    sensor_id: str
    moisture: float
    temperature: float
    timestamp: str

class SoilType:
    CLAY = "clay"
    CLAY_LOAM = "clay_loam"
    LOAM = "loam"
    SILTY_LOAM = "silty_loam"
    SILT = "silt"
    SANDY_LOAM = "sandy_loam"
    SAND = "sand"
    PEAT = "peat"

class SensorGenerator:
    def __init__(self, zone_id: str, sensor_id: str, soil_type: str = SoilType.LOAM):
        self.zone_id = zone_id
        self.sensor_id = sensor_id
        self.soil_type = soil_type.lower()
        
        # Initial conditions
        self.current_moisture = random.uniform(40.0, 80.0)
        self.current_temperature = random.uniform(15.0, 25.0)
        
        # Soil-specific parameters
        # Depletion rate: how much moisture is lost per tick (simulated)
        if self.soil_type == SoilType.SAND:
            self.depletion_base = 0.6
            self.retention_variance = 0.25
        elif self.soil_type == SoilType.SANDY_LOAM:
            self.depletion_base = 0.45
            self.retention_variance = 0.18
        elif self.soil_type == SoilType.LOAM:
            self.depletion_base = 0.25
            self.retention_variance = 0.1
        elif self.soil_type == SoilType.SILTY_LOAM:
            self.depletion_base = 0.2
            self.retention_variance = 0.08
        elif self.soil_type == SoilType.SILT:
            self.depletion_base = 0.18
            self.retention_variance = 0.07
        elif self.soil_type == SoilType.CLAY_LOAM:
            self.depletion_base = 0.15
            self.retention_variance = 0.06
        elif self.soil_type == SoilType.CLAY:
            self.depletion_base = 0.1
            self.retention_variance = 0.05
        elif self.soil_type == SoilType.PEAT:
            self.depletion_base = 0.05
            self.retention_variance = 0.03
        else: # Default/Fallback
            self.depletion_base = 0.25
            self.retention_variance = 0.1

    def generate_reading(self) -> SensorReading:
        # Simulate temperature (simple random walk constrained between 10C and 40C)
        temp_delta = random.uniform(-1.0, 1.0)
        self.current_temperature = max(10.0, min(40.0, self.current_temperature + temp_delta))
        
        # Simulate moisture depletion
        # Higher temperature = faster depletion
        temp_factor = max(0.5, self.current_temperature / 20.0)
        
        # Calculate depletion for this tick
        depletion = (self.depletion_base + random.uniform(-self.retention_variance, self.retention_variance)) * temp_factor
        
        # Sometimes it rains or irrigates (simulated random jump)
        if random.random() < 0.05: # 5% chance of sudden moisture increase
            self.current_moisture += random.uniform(10.0, 30.0)
        else:
            self.current_moisture -= depletion
            
        # Bound moisture between 0% and 100%
        self.current_moisture = max(0.0, min(100.0, self.current_moisture))
        
        # Optionally add slight sensor noise
        noise = random.uniform(-0.5, 0.5)
        reported_moisture = max(0.0, min(100.0, self.current_moisture + noise))
        
        return SensorReading(
            zone_id=self.zone_id,
            sensor_id=self.sensor_id,
            moisture=round(reported_moisture, 2),
            temperature=round(self.current_temperature, 2),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
