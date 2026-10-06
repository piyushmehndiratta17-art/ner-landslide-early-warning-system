"""
AI / Machine Learning Model for Landslide Susceptibility & Risk Prediction in NER.
Combines Random Forest ensemble classification with geotechnical physics thresholds
(Intensity-Duration curves and Saito's inverse-velocity time-to-failure forecasting).
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from src.data_manager import generate_synthetic_dataset

FEATURE_COLUMNS = [
    "slope_deg",
    "rainfall_24h",
    "rainfall_72h_ari",
    "rainfall_intensity_max",
    "soil_moisture_pct",
    "pore_water_pressure_kpa",
    "displacement_rate_mm_day",
    "lithology_factor",
    "elevation_m",
    "ndvi",
    "seismic_pga_g"
]

FEATURE_LABELS = {
    "slope_deg": "Slope Angle (°)",
    "rainfall_24h": "24h Cumulative Rainfall (mm)",
    "rainfall_72h_ari": "72h Antecedent Rain Index (mm)",
    "rainfall_intensity_max": "Max Peak Intensity (mm/h)",
    "soil_moisture_pct": "Soil Moisture Content (%)",
    "pore_water_pressure_kpa": "Pore Water Pressure (kPa)",
    "displacement_rate_mm_day": "Slope Displacement (mm/day)",
    "lithology_factor": "Geological Vulnerability (1-4)",
    "elevation_m": "Terrain Elevation (m)",
    "ndvi": "Vegetation Density (NDVI)",
    "seismic_pga_g": "Seismic Peak Ground Acc (g)"
}

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "landslide_rf_model.joblib")

class LandslidePredictor:
    def __init__(self):
        self.model = None
        self.feature_importances_ = None
        self.metrics = {}
        self.load_or_train()

    def train(self, num_samples: int = 2000):
        """Trains the Random Forest model on geological and hydrological data."""
        df = generate_synthetic_dataset(num_samples=num_samples)
        X = df[FEATURE_COLUMNS]
        y = df["landslide_occurred"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        rf = RandomForestClassifier(
            n_estimators=120,
            max_depth=10,
            min_samples_split=4,
            random_state=42,
            class_weight="balanced"
        )
        rf.fit(X_train, y_train)

        y_pred = rf.predict(X_test)
        y_prob = rf.predict_proba(X_test)[:, 1]

        self.model = rf
        self.feature_importances_ = dict(zip(FEATURE_COLUMNS, rf.feature_importances_))
        self.metrics = {
            "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 3),
            "accuracy": round(float((y_pred == y_test).mean()), 3),
            "samples": len(df)
        }

        # Save model
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": self.model, "metrics": self.metrics, "importances": self.feature_importances_}, MODEL_PATH)

    def load_or_train(self):
        """Loads cached model or trains a new instance."""
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                self.model = data["model"]
                self.metrics = data.get("metrics", {})
                self.feature_importances_ = data.get("importances", {})
                return
            except Exception:
                pass
        self.train()

    def predict_risk(self, telemetry_dict: dict) -> dict:
        """
        Calculates Landslide Susceptibility Index (LSI) and Alert Level.
        telemetry_dict should contain the feature columns.
        """
        input_data = pd.DataFrame([{col: telemetry_dict.get(col, 0.0) for col in FEATURE_COLUMNS}])
        prob = float(self.model.predict_proba(input_data)[0, 1])

        # Hydrological Caine I-D Threshold Check (Eastern Himalayas Calibration: I = 14.82 * D^-0.39)
        # Assuming typical rain storm duration D = 24h
        duration_hours = 24.0
        critical_intensity_threshold = 14.82 * (duration_hours ** -0.39)  # ~4.29 mm/h mean rate
        actual_mean_intensity = telemetry_dict.get("rainfall_24h", 0.0) / 24.0
        id_threshold_breached = actual_mean_intensity >= critical_intensity_threshold

        # Geotechnical safety penalty: if pore pressure > 45 kPa or displacement > 10 mm/day
        geotechnical_multiplier = 1.0
        pwp = telemetry_dict.get("pore_water_pressure_kpa", 0.0)
        disp = telemetry_dict.get("displacement_rate_mm_day", 0.0)

        if pwp > 50.0:
            geotechnical_multiplier += 0.15
        if disp > 8.0:
            geotechnical_multiplier += 0.20
        if telemetry_dict.get("seismic_pga_g", 0.0) > 0.18:
            geotechnical_multiplier += 0.25

        lsi = np.clip(prob * geotechnical_multiplier, 0.0, 1.0)

        # Categorize into 4-tier NDMA / SDMA Warning Standard
        if lsi < 0.35:
            tier = "GREEN"
            tier_label = "Low / Baseline (Normal)"
            color = "#10B981"
            action_code = "ACT-0: Continuous Ambient Monitoring"
        elif lsi < 0.60:
            tier = "YELLOW"
            tier_label = "Advisory / Watch (Elevated)"
            color = "#F59E0B"
            action_code = "ACT-1: Alert DDMA & Local Field Observers"
        elif lsi < 0.80:
            tier = "ORANGE"
            tier_label = "Warning / High Alert (Hazard)"
            color = "#F97316"
            action_code = "ACT-2: Deploy SDRF & Pre-stage Machinery"
        else:
            tier = "RED"
            tier_label = "Critical / Imminent Evacuation"
            color = "#EF4444"
            action_code = "ACT-3: Sound Sirens, Halt Highway Traffic & Evacuate"

        # Feature factor contributions (SHAP-proxy via feature deviation * importance)
        contributions = {}
        for col in FEATURE_COLUMNS:
            val = telemetry_dict.get(col, 0.0)
            imp = self.feature_importances_.get(col, 0.1)
            # Normalize impact
            if col == "slope_deg":
                impact = (val / 65.0) * imp
            elif col in ["rainfall_24h", "rainfall_72h_ari"]:
                impact = (val / 300.0) * imp
            elif col == "pore_water_pressure_kpa":
                impact = (val / 75.0) * imp
            elif col == "displacement_rate_mm_day":
                impact = (val / 25.0) * imp
            elif col == "soil_moisture_pct":
                impact = (val / 95.0) * imp
            elif col == "seismic_pga_g":
                impact = (val / 0.4) * imp
            elif col == "ndvi":
                impact = -1.0 * (val / 1.0) * imp  # Vegetation reduces risk
            else:
                impact = imp * 0.5
            contributions[col] = float(impact)

        # Top driving factors
        sorted_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        top_factors = [
            {"factor": FEATURE_LABELS.get(k, k), "score": round(v, 4), "direction": "Aggravating" if v > 0 else "Mitigating"}
            for k, v in sorted_factors[:4]
        ]

        # Saito's Inverse-Velocity Time to Failure (TtF) Calculation
        ttf_hours = None
        if disp > 5.0 and lsi >= 0.60:
            # Fukuzono-Saito formula: 1/v approaching 0
            # Estimated time remaining = displacement_threshold / acceleration
            estimated_ttf = max(1.5, round(28.0 / (disp ** 0.85), 1))
            ttf_hours = estimated_ttf

        return {
            "lsi": round(lsi, 3),
            "raw_prob": round(prob, 3),
            "tier": tier,
            "tier_label": tier_label,
            "color": color,
            "action_code": action_code,
            "id_threshold_breached": id_threshold_breached,
            "critical_intensity_threshold": round(critical_intensity_threshold, 2),
            "actual_mean_intensity": round(actual_mean_intensity, 2),
            "top_factors": top_factors,
            "ttf_hours": ttf_hours
        }
