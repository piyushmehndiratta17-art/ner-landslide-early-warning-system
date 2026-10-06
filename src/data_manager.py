"""
Data Manager for Landslide Risk Monitoring System in NER (North Eastern Region).
Contains NER station telemetry registries, historical inventory, and synthetic dataset generation.
"""

import json
import os
import numpy as np
import pandas as pd

# Key landslide monitoring stations across the 8 Northeastern states
NER_STATIONS = [
    {
        "id": "STN-SK01",
        "name": "NH-10 Gangtok Corridor",
        "state": "Sikkim",
        "district": "East Sikkim",
        "lat": 27.3389,
        "lon": 88.6065,
        "elevation_m": 1650,
        "slope_deg": 48.5,
        "lithology": "Weathered Schist & Phyllite",
        "lithology_factor": 4,
        "historical_events": 14,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-SK01-LORA"
    },
    {
        "id": "STN-SK02",
        "name": "Mangan - Chungthang Sector",
        "state": "Sikkim",
        "district": "North Sikkim",
        "lat": 27.5085,
        "lon": 88.5298,
        "elevation_m": 1820,
        "slope_deg": 52.0,
        "lithology": "Gneissic Debris & Weathered Granites",
        "lithology_factor": 3,
        "historical_events": 19,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-SK02-LORA"
    },
    {
        "id": "STN-ML01",
        "name": "Cherrapunji (Sohra) Escarpment",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.2702,
        "lon": 91.7323,
        "elevation_m": 1430,
        "slope_deg": 44.0,
        "lithology": "Sandstone-Shale Alternations",
        "lithology_factor": 3,
        "historical_events": 11,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-ML01-4G"
    },
    {
        "id": "STN-ML02",
        "name": "Mawsynram Precipitation Belt",
        "state": "Meghalaya",
        "district": "South West Khasi Hills",
        "lat": 25.2975,
        "lon": 91.5826,
        "elevation_m": 1400,
        "slope_deg": 41.5,
        "lithology": "Fissured Sandstone & Clay Layer",
        "lithology_factor": 3,
        "historical_events": 9,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-ML02-LORA"
    },
    {
        "id": "STN-ML03",
        "name": "NH-6 Sonapur Tunnel / Jaintia Hills",
        "state": "Meghalaya",
        "district": "East Jaintia Hills",
        "lat": 25.1121,
        "lon": 92.3654,
        "elevation_m": 620,
        "slope_deg": 46.0,
        "lithology": "Coal-Bearing Soft Mudstones",
        "lithology_factor": 4,
        "historical_events": 23,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-ML03-LORA"
    },
    {
        "id": "STN-AS01",
        "name": "Dima Hasao (Jatinga Valley / Hill Railway)",
        "state": "Assam",
        "district": "Dima Hasao",
        "lat": 25.1667,
        "lon": 93.0333,
        "elevation_m": 512,
        "slope_deg": 39.0,
        "lithology": "Unconsolidated Tertiary Shale & Clay",
        "lithology_factor": 4,
        "historical_events": 27,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-AS01-LORA"
    },
    {
        "id": "STN-AS02",
        "name": "Guwahati Nilachal / Kamakhya Slopes",
        "state": "Assam",
        "district": "Kamrup Metropolitan",
        "lat": 26.1663,
        "lon": 91.7052,
        "elevation_m": 240,
        "slope_deg": 35.0,
        "lithology": "In-situ Weathered Red Soil & Granite",
        "lithology_factor": 2,
        "historical_events": 7,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-AS02-4G"
    },
    {
        "id": "STN-AR01",
        "name": "Tawang - Sela Pass Highway Axis",
        "state": "Arunachal Pradesh",
        "district": "Tawang",
        "lat": 27.5861,
        "lon": 91.8653,
        "elevation_m": 3050,
        "slope_deg": 55.0,
        "lithology": "Glacial Moraines & Sheared Gneiss",
        "lithology_factor": 3,
        "historical_events": 15,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-AR01-SAT"
    },
    {
        "id": "STN-AR02",
        "name": "West Kameng / Bomdila Ridge",
        "state": "Arunachal Pradesh",
        "district": "West Kameng",
        "lat": 27.2644,
        "lon": 92.4159,
        "elevation_m": 2210,
        "slope_deg": 47.0,
        "lithology": "Quartzite & Weathered Biotite Schist",
        "lithology_factor": 3,
        "historical_events": 12,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-AR02-LORA"
    },
    {
        "id": "STN-MZ01",
        "name": "Aizawl Fault Scarp (Laipuitlang Zone)",
        "state": "Mizoram",
        "district": "Aizawl",
        "lat": 23.7271,
        "lon": 92.7176,
        "elevation_m": 1130,
        "slope_deg": 50.0,
        "lithology": "Surma Group Interbedded Siltstone & Shale",
        "lithology_factor": 4,
        "historical_events": 18,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-MZ01-4G"
    },
    {
        "id": "STN-NL01",
        "name": "Kohima - Dzüdza River Axis (NH-29)",
        "state": "Nagaland",
        "district": "Kohima",
        "lat": 25.6751,
        "lon": 94.1086,
        "elevation_m": 1440,
        "slope_deg": 43.0,
        "lithology": "Disang Formation Highly Cleaved Shale",
        "lithology_factor": 4,
        "historical_events": 21,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-NL01-LORA"
    },
    {
        "id": "STN-MN01",
        "name": "Imphal - Jiribam NH-37 (Tupul Station Axis)",
        "state": "Manipur",
        "district": "Noney",
        "lat": 24.7891,
        "lon": 93.6812,
        "elevation_m": 780,
        "slope_deg": 49.0,
        "lithology": "Crushed Shale & Talus Overburden",
        "lithology_factor": 4,
        "historical_events": 25,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-MN01-LORA"
    },
    {
        "id": "STN-TR01",
        "name": "Jampui Hills Ridge Corridor",
        "state": "Tripura",
        "district": "North Tripura",
        "lat": 23.8211,
        "lon": 92.2743,
        "elevation_m": 930,
        "slope_deg": 34.0,
        "lithology": "Tipam Sandstone & Friable Silt",
        "lithology_factor": 2,
        "historical_events": 6,
        "sensor_health": "Active",
        "gateway_sn": "GW-NER-TR01-4G"
    }
]

def generate_synthetic_dataset(num_samples: int = 1500, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic multi-factor dataset of geological, hydrological, and geotechnical
    parameters modeled after Eastern Himalayan and Indo-Burmese terrain.
    """
    np.random.seed(random_seed)

    slope_deg = np.random.uniform(15.0, 65.0, num_samples)
    rainfall_24h = np.random.exponential(scale=55.0, size=num_samples)
    rainfall_24h = np.clip(rainfall_24h, 0.0, 380.0)

    # Antecedent rainfall index (72-hour accumulation)
    rainfall_72h_ari = rainfall_24h * np.random.uniform(1.4, 2.8, num_samples) + np.random.uniform(5.0, 60.0, num_samples)

    # Maximum hourly peak intensity (mm/hr)
    rainfall_intensity_max = rainfall_24h * np.random.uniform(0.12, 0.28, num_samples) + np.random.uniform(1.0, 10.0, num_samples)

    # Soil moisture content (%) correlated with rainfall
    base_smc = 25.0 + (rainfall_72h_ari / 350.0) * 60.0
    soil_moisture_pct = np.clip(base_smc + np.random.normal(0, 5, num_samples), 15.0, 98.0)

    # Pore water pressure (kPa) increases as soil moisture exceeds field capacity (>65%)
    pore_water_pressure_kpa = np.where(
        soil_moisture_pct > 60.0,
        (soil_moisture_pct - 60.0) * 1.6 + (rainfall_24h * 0.1) + np.random.uniform(0, 12, num_samples),
        np.random.uniform(2.0, 15.0, num_samples)
    )

    # Lithology factor: 1 (Granite/Massive), 2 (Sandstone), 3 (Schist/Gneiss), 4 (Weak Shale/Phyllite)
    lithology_factor = np.random.choice([1, 2, 3, 4], size=num_samples, p=[0.15, 0.25, 0.30, 0.30])

    # Elevation (m)
    elevation_m = np.random.uniform(200.0, 3200.0, num_samples)

    # Normalized Difference Vegetation Index (NDVI) - higher vegetation stabilizes slopes
    ndvi = np.clip(np.random.beta(5, 2, num_samples) * 0.9, 0.05, 0.85)

    # Seismic Peak Ground Acceleration (g) - NER lies in Seismic Zones V and IV
    seismic_pga_g = np.random.exponential(scale=0.04, size=num_samples)
    seismic_pga_g = np.clip(seismic_pga_g, 0.005, 0.48)

    # Geotechnical displacement rate (mm/day) measured by in-place inclinometer
    # Creeps heavily when pore pressure and slope are high
    displacement_rate_mm_day = np.where(
        (pore_water_pressure_kpa > 35.0) & (slope_deg > 35.0),
        np.random.exponential(scale=8.0, size=num_samples) + 2.0,
        np.random.exponential(scale=0.5, size=num_samples)
    )

    # Physics-informed ground truth probability calculation
    # Factor of Safety (FS) proxy: Driving force vs Resisting force
    # Driving: gravity on slope, pore pressure reducing effective stress, seismic load, antecedent water weight
    # Resisting: internal friction, cohesion, root reinforcement (NDVI)
    driving_score = (
        0.30 * (slope_deg / 65.0) +
        0.25 * (pore_water_pressure_kpa / 75.0) +
        0.20 * (rainfall_72h_ari / 400.0) +
        0.10 * (displacement_rate_mm_day / 20.0) +
        0.10 * (lithology_factor / 4.0) +
        0.05 * (seismic_pga_g / 0.35)
    )
    
    resisting_benefit = 0.15 * ndvi
    net_risk_probability = np.clip(driving_score - resisting_benefit + np.random.normal(0, 0.04, num_samples), 0.0, 1.0)
    
    # Binary target with realistic threshold
    landslide_occurred = (net_risk_probability > 0.52).astype(int)

    df = pd.DataFrame({
        "slope_deg": np.round(slope_deg, 1),
        "rainfall_24h": np.round(rainfall_24h, 1),
        "rainfall_72h_ari": np.round(rainfall_72h_ari, 1),
        "rainfall_intensity_max": np.round(rainfall_intensity_max, 1),
        "soil_moisture_pct": np.round(soil_moisture_pct, 1),
        "pore_water_pressure_kpa": np.round(pore_water_pressure_kpa, 1),
        "displacement_rate_mm_day": np.round(displacement_rate_mm_day, 2),
        "lithology_factor": lithology_factor,
        "elevation_m": np.round(elevation_m, 0),
        "ndvi": np.round(ndvi, 2),
        "seismic_pga_g": np.round(seismic_pga_g, 3),
        "landslide_occurred": landslide_occurred
    })

    return df

def get_stations_dataframe() -> pd.DataFrame:
    """Returns the NER stations as a pandas DataFrame."""
    return pd.DataFrame(NER_STATIONS)
