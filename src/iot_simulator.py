"""
IoT Sensor Telemetry Simulator for NER Landslide Early Warning System.
Generates realistic edge sensor telemetry (Rain gauges, Inclinometers, Piezometers, TDR Soil Sensors).
Provides instant demo presets for Tech Expo presentations.
"""

import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from src.data_manager import NER_STATIONS

SCENARIOS = {
    "baseline": {
        "title": "🟢 Scenario A: Baseline Dry Season (Safe Operations)",
        "description": "Clear skies across the North Eastern Region. Low pore pressure and zero slope displacement.",
        "params": {
            "rainfall_mult": 0.05,
            "soil_moist_bias": 28.0,
            "pwp_bias": 6.0,
            "disp_bias": 0.1,
            "pga_bias": 0.015
        }
    },
    "monsoon_deluge": {
        "title": "🌧️ Scenario B: Extreme Monsoon Deluge (Meghalaya & Assam)",
        "description": "Torrential monsoon burst across Meghalaya (Cherrapunji/Mawsynram) and Dima Hasao. Severe pore pressure saturation.",
        "params": {
            "high_stations": ["STN-ML01", "STN-ML02", "STN-ML03", "STN-AS01"],
            "high_rainfall_24h": 265.0,
            "high_soil_moist": 96.0,
            "high_pwp": 64.0,
            "high_disp": 7.5,
            "other_rainfall_mult": 1.2
        }
    },
    "seismic_sikkim": {
        "title": "⚡ Scenario C: Post-Earthquake Instability (Sikkim NH-10)",
        "description": "Moderate M5.4 seismic tremor along the Teesta valley fault line. Rapid tiltmeter displacement on steep fractured slopes.",
        "params": {
            "high_stations": ["STN-SK01", "STN-SK02"],
            "high_pga": 0.29,
            "high_disp": 21.4,
            "high_pwp": 42.0,
            "high_rainfall_24h": 85.0
        }
    },
    "railway_tupul": {
        "title": "🚨 Scenario D: Saturated Railway Slope Failure (Manipur & Nagaland)",
        "description": "Prolonged rainfall inducing deep-seated circular slip along the Imphal-Jiribam (Tupul) and Kohima highway corridors.",
        "params": {
            "high_stations": ["STN-MN01", "STN-NL01", "STN-MZ01"],
            "high_rainfall_24h": 195.0,
            "high_soil_moist": 92.0,
            "high_pwp": 58.0,
            "high_disp": 14.8
        }
    },
    "live_weather": {
        "title": "🌐 Scenario E: Live Real-World Weather Telemetry (Open-Meteo API)",
        "description": "Fetches current live precipitation, humidity, and temperature directly from Open-Meteo API for real-time risk assessment across NER.",
        "params": {}
    }
}

class IoTSimulator:
    def __init__(self, predictor):
        self.predictor = predictor
        self._live_cache = {}

    def _fetch_open_meteo(self, lat: float, lon: float) -> dict:
        """Fetches live weather from Open-Meteo API with caching."""
        cache_key = f"{lat:.2f}_{lon:.2f}"
        now = datetime.utcnow()
        if cache_key in self._live_cache:
            data, timestamp = self._live_cache[cache_key]
            if (now - timestamp).total_seconds() < 600:  # 10 min cache
                return data

        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code&hourly=precipitation"
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                cur = resp.json().get("current", {})
                hourly_precip = resp.json().get("hourly", {}).get("precipitation", [])
                sum_24h = float(sum(hourly_precip[:24])) if hourly_precip else float(cur.get("rain", 0.0) * 12.0)
                result = {
                    "temp_c": cur.get("temperature_2m", 22.0),
                    "humidity_pct": cur.get("relative_humidity_2m", 65.0),
                    "current_rain_mm_h": float(cur.get("precipitation", 0.0)),
                    "estimated_24h_rain": max(float(cur.get("rain", 0.0) * 10.0), sum_24h),
                    "source": "Open-Meteo Live API"
                }
                self._live_cache[cache_key] = (result, now)
                return result
        except Exception:
            pass

        return {
            "temp_c": 21.0,
            "humidity_pct": 70.0,
            "current_rain_mm_h": 0.0,
            "estimated_24h_rain": 4.5,
            "source": "Fallback Offline Ambient"
        }

    def get_station_telemetry(self, station: dict, scenario_key: str = "baseline", custom_overrides: dict = None) -> dict:
        """
        Generates instantaneous multi-parameter sensor readings for a specific station
        based on active scenario and optional user overrides.
        """
        stn_id = station["id"]
        base_slope = station["slope_deg"]
        lithology_factor = station["lithology_factor"]
        elev = station["elevation_m"]

        # Default normal conditions
        rainfall_24h = 8.0 + np.random.uniform(0, 10)
        rainfall_72h = rainfall_24h * 1.8 + 12.0
        rainfall_intensity = 1.2 + np.random.uniform(0, 2)
        soil_moisture = 32.0 + np.random.uniform(0, 6)
        pwp = 5.0 + np.random.uniform(0, 4)
        displacement_rate = 0.15 + np.random.uniform(0, 0.2)
        seismic_pga = 0.015 + np.random.uniform(0, 0.01)
        ndvi = 0.65 - (base_slope / 150.0)

        # Apply Scenario modifications
        if scenario_key == "baseline":
            pass
        elif scenario_key == "monsoon_deluge":
            params = SCENARIOS["monsoon_deluge"]["params"]
            if stn_id in params["high_stations"]:
                rainfall_24h = params["high_rainfall_24h"] + np.random.uniform(-15, 20)
                rainfall_72h = rainfall_24h * 2.3 + np.random.uniform(20, 60)
                rainfall_intensity = 28.5 + np.random.uniform(-4, 8)
                soil_moisture = params["high_soil_moist"] + np.random.uniform(-2, 2)
                pwp = params["high_pwp"] + np.random.uniform(-5, 6)
                displacement_rate = params["high_disp"] + np.random.uniform(-1, 2)
            else:
                rainfall_24h = 45.0 + np.random.uniform(0, 25)
                rainfall_72h = rainfall_24h * 1.9
                rainfall_intensity = 6.0
                soil_moisture = 55.0
                pwp = 18.0
        elif scenario_key == "seismic_sikkim":
            params = SCENARIOS["seismic_sikkim"]["params"]
            if stn_id in params["high_stations"]:
                seismic_pga = params["high_pga"] + np.random.uniform(-0.02, 0.04)
                displacement_rate = params["high_disp"] + np.random.uniform(-2, 3)
                pwp = params["high_pwp"] + np.random.uniform(-4, 5)
                rainfall_24h = params["high_rainfall_24h"] + np.random.uniform(-10, 15)
                rainfall_72h = rainfall_24h * 2.0
                rainfall_intensity = 12.0
                soil_moisture = 78.0
            else:
                seismic_pga = 0.06 + np.random.uniform(0, 0.03)
        elif scenario_key == "railway_tupul":
            params = SCENARIOS["railway_tupul"]["params"]
            if stn_id in params["high_stations"]:
                rainfall_24h = params["high_rainfall_24h"] + np.random.uniform(-10, 15)
                rainfall_72h = rainfall_24h * 2.4
                rainfall_intensity = 22.0
                soil_moisture = params["high_soil_moist"] + np.random.uniform(-3, 2)
                pwp = params["high_pwp"] + np.random.uniform(-4, 6)
                displacement_rate = params["high_disp"] + np.random.uniform(-1.5, 2.5)
        elif scenario_key == "live_weather":
            live_data = self._fetch_open_meteo(station["lat"], station["lon"])
            rainfall_24h = max(0.5, live_data["estimated_24h_rain"])
            rainfall_72h = rainfall_24h * 1.9 + np.random.uniform(2.0, 10.0)
            rainfall_intensity = max(0.5, live_data["current_rain_mm_h"])
            soil_moisture = min(98.0, max(20.0, live_data["humidity_pct"] * 0.75 + (rainfall_24h * 0.15)))
            pwp = max(2.0, (soil_moisture - 55.0) * 1.2) if soil_moisture > 55.0 else 5.0
            displacement_rate = 0.2 + (pwp / 40.0) * 0.8
            ndvi = 0.68 - (base_slope / 160.0)

        # Apply manual user overrides if provided
        if custom_overrides and custom_overrides.get("stn_id") == stn_id:
            if "rainfall_24h" in custom_overrides:
                rainfall_24h = custom_overrides["rainfall_24h"]
                rainfall_72h = rainfall_24h * 2.1
            if "soil_moisture_pct" in custom_overrides:
                soil_moisture = custom_overrides["soil_moisture_pct"]
            if "pore_water_pressure_kpa" in custom_overrides:
                pwp = custom_overrides["pore_water_pressure_kpa"]
            if "displacement_rate_mm_day" in custom_overrides:
                displacement_rate = custom_overrides["displacement_rate_mm_day"]
            if "seismic_pga_g" in custom_overrides:
                seismic_pga = custom_overrides["seismic_pga_g"]
            if "slope_deg" in custom_overrides:
                base_slope = custom_overrides["slope_deg"]

        telemetry = {
            "station_id": stn_id,
            "station_name": station["name"],
            "state": station["state"],
            "district": station["district"],
            "lat": station["lat"],
            "lon": station["lon"],
            "elevation_m": elev,
            "slope_deg": round(base_slope, 1),
            "rainfall_24h": round(rainfall_24h, 1),
            "rainfall_72h_ari": round(rainfall_72h, 1),
            "rainfall_intensity_max": round(rainfall_intensity, 1),
            "soil_moisture_pct": round(min(99.0, max(10.0, soil_moisture)), 1),
            "pore_water_pressure_kpa": round(max(0.0, pwp), 1),
            "displacement_rate_mm_day": round(max(0.0, displacement_rate), 2),
            "lithology_factor": lithology_factor,
            "lithology": station["lithology"],
            "ndvi": round(ndvi, 2),
            "seismic_pga_g": round(seismic_pga, 3),
            "gateway_sn": station["gateway_sn"],
            "battery_v": round(3.85 + np.random.uniform(-0.15, 0.25), 2),
            "signal_rssi_dbm": int(-72 + np.random.uniform(-8, 5)),
            "last_ping_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        # Run AI Risk Prediction
        risk_result = self.predictor.predict_risk(telemetry)
        telemetry.update(risk_result)
        return telemetry

    def get_all_stations_telemetry(self, scenario_key: str = "baseline", custom_overrides: dict = None) -> list:
        """Returns live telemetry and AI assessment for all NER monitoring stations."""
        results = []
        for stn in NER_STATIONS:
            tel = self.get_station_telemetry(stn, scenario_key=scenario_key, custom_overrides=custom_overrides)
            results.append(tel)
        return results

    def generate_24h_history(self, current_telemetry: dict) -> pd.DataFrame:
        """
        Synthesizes a 24-hour hourly trend history leading up to the current reading
        for time-series charting.
        """
        now = datetime.now()
        hours = [now - timedelta(hours=23 - i) for i in range(24)]
        timestamps = [h.strftime("%H:%M") for h in hours]

        target_rain = current_telemetry["rainfall_24h"]
        target_pwp = current_telemetry["pore_water_pressure_kpa"]
        target_disp = current_telemetry["displacement_rate_mm_day"]
        target_moist = current_telemetry["soil_moisture_pct"]

        # Cumulative curve pattern
        t = np.linspace(0, 1, 24)
        sig = 1 / (1 + np.exp(-6 * (t - 0.5)))

        hourly_rain = (target_rain * (sig / sig.sum()) * 1.5) + np.random.uniform(0, 1.0, 24)
        cum_rain = np.cumsum(hourly_rain)
        cum_rain = (cum_rain / cum_rain[-1]) * target_rain

        hourly_pwp = (target_pwp * 0.2) + (target_pwp * 0.8 * sig) + np.random.normal(0, 0.5, 24)
        hourly_disp = (target_disp * 0.1) + (target_disp * 0.9 * (t ** 2)) + np.random.normal(0, 0.05, 24)
        hourly_moist = (target_moist * 0.4) + (target_moist * 0.6 * sig)

        df_history = pd.DataFrame({
            "Time": timestamps,
            "Rainfall_mm": np.clip(np.round(hourly_rain, 1), 0, None),
            "Cum_Rain_mm": np.clip(np.round(cum_rain, 1), 0, None),
            "Pore_Pressure_kPa": np.clip(np.round(hourly_pwp, 1), 0, None),
            "Displacement_mm_day": np.clip(np.round(hourly_disp, 2), 0, None),
            "Soil_Moisture_pct": np.clip(np.round(hourly_moist, 1), 10, 99)
        })

        return df_history
