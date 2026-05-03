export interface Zone {
  id: string;
  zone_id: string;
  name: string;
  zone_name: string;
  description?: string;
  soil_type: string;
  crop_type: string;
  moisture_min: number;
  moisture_max: number;
  is_active: boolean;
  active: boolean;
  owner_id?: string;
  source?: string;
  created_at: string;
  updated_at: string;
}

export interface SensorReading {
  timestamp: string;
  sensor_id: string;
  moisture: number | null;
  temperature: number | null;
}

export interface Prediction {
  predicted_at: string;
  sensor_id: string;
  prediction: number | null;
  confidence: number | null;
}

export interface IrrigationEvent {
  triggered_at: string;
  zone_id: string;
  trigger_reason: string;
  recommended_volume: number | null;
  status: string;
}
