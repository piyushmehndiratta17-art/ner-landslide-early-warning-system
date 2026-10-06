# 🏔️ AI-Based Landslide Early Warning and Risk Monitoring System in NER (North Eastern Region)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/UI-Streamlit%20%7C%20Folium%20%7C%20Plotly-orange.svg)](https://streamlit.io/)
[![Standard](https://img.shields.io/badge/Alerting-NDMA%20CAP%20v1.2-red.svg)](https://sachet.ndma.gov.in/)
[![Status](https://img.shields.io/badge/Project-Tech%20Expo%20Ready-success.svg)]()

> An autonomous, physics-informed AI disaster monitoring and early warning platform engineered for the high-risk mountain corridors of the **North Eastern Region (NER) of India** (Sikkim, Meghalaya, Assam, Arunachal Pradesh, Mizoram, Nagaland, Manipur, and Tripura).

---

## 📌 1. Project Overview & The Regional Challenge

The North Eastern Region (NER) of India represents one of the most landslide-susceptible terrains in the world:
- **Severe Precipitation:** Monsoons in Meghalaya (Mawsynram & Cherrapunji) bring $>11,000\text{ mm}$ of rainfall annually, inducing rapid slope liquefaction and pore water pressure saturation.
- **Seismic Vulnerability:** Falling entirely within **Bureau of Indian Standards (BIS) Seismic Zones V and IV**, frequent tremors exacerbate slope instability.
- **Critical Lifeline Isolation:** Arterial mountain routes like **NH-10** (Sikkim's sole lifeline), **NH-6** (Meghalaya-Assam-Barak Valley), **NH-29** (Kohima corridor), and the **Lumding-Badarpur & Tupul railway axes** suffer chronic blockages, severing medical access and essential logistics.

This project delivers an end-to-end operational prototype bridging **IoT Edge Telemetry**, **Physics-Informed Machine Learning**, and **Emergency Common Alerting Protocol (CAP v1.2)** broadcasting.

---

## 🚀 2. Quickstart Guide (Running the App)

### Option A: Double-Click Launcher (Windows)
Simply double-click:
```bat
run_demo.bat
```

### Option B: Terminal Launch
1. Open PowerShell or Command Prompt in the project folder:
```powershell
# Activate local environment
.\.venv\Scripts\activate

# Launch Streamlit app
streamlit run app.py
```
2. Open your web browser at: **`http://localhost:8501`**

---

## 🏗️ 3. End-to-End System Architecture

```text
[Field IoT Edge Layer]
  ├── Tipping Bucket Rain Gauge (mm & mm/h)
  ├── Campbell TDR Soil Moisture Probe (%)
  ├── Vibrating Wire Piezometer (Pore Pressure in kPa)
  └── MEMS Inclinometer & Geophone (Displacement Rate & PGA)
              │
              ▼ (RS-485 / Modbus)
[Solar Edge Node (ESP32)]
              │
              ▼ (LoRaWAN 865 MHz Mesh / 4G Cellular Failover)
[Central Processing & Analytics Cloud / Fog Server]
              │
              ├── Physics-Informed Random Forest Classifier
              ├── Eastern Himalayan Intensity-Duration (I-D) Threshold Curve
              └── Saito Inverse-Velocity (1/v) Time-to-Failure Extrapolator
              │
              ▼
[Decision Support Command Center & Early Warning System]
  ├── Interactive Geospatial Leaflet GIS Map (NER Corridors)
  ├── NDMA SACHET CAP v1.2 XML/JSON Alert Dispatches
  ├── Multilingual Citizen SMS & WhatsApp Advisories (5 Languages)
  └── Automated Incident Situation Reports (SITREP)
```

---

## 🔬 4. Core Features & Scientific Innovations

### 1. Multi-Parameter Physics-Informed AI Model
- **Input Features:** 24-hr cumulative rainfall, 72-hr antecedent rainfall index (ARI), peak hourly intensity, slope gradient, soil moisture %, pore water pressure, inclinometer tilt velocity, geological lithology factor, elevation, NDVI, and seismic PGA.
- **Ensemble Classifier:** Calibrated Random Forest scoring a **Landslide Susceptibility Index (LSI)** from `0.00` to `1.00`.
- **4-Tier NDMA Alert Standard:**
  - 🟢 **GREEN (Normal / Baseline):** $LSI < 0.35$
  - 🟡 **YELLOW (Advisory / Watch):** $0.35 \le LSI < 0.60$
  - 🟠 **ORANGE (Warning / High Alert):** $0.60 \le LSI < 0.80$
  - 🔴 **RED (Critical / Immediate Evacuation):** $LSI \ge 0.80$

### 2. Geotechnical & Hydrological Stability Envelopes
- **Eastern Himalayan Empirical Rainfall Threshold:**
  $$\text{Critical Intensity } I = 14.82 \cdot D^{-0.39}$$
  *(Calibrated for the Eastern Himalayas based on Geological Survey of India benchmarks).*
- **Saito’s Inverse-Velocity Method ($\frac{1}{v} \to 0$):**
  When accelerated displacement is detected by downhole inclinometers, the system extrapolates the tertiary creep trend to provide an **Estimated Time to Failure (TtF)** countdown window in hours!

### 3. Interactive Leaflet GIS Command Center
- Maps 12 real-world high-risk corridors across Sikkim, Meghalaya, Assam, Arunachal Pradesh, Mizoram, Nagaland, Manipur, and Tripura.
- Real-time color-coded station pins with dynamic hazard radii (5–12 km evacuation zones).

### 4. Live Tech Expo Demo Scenarios
- **Scenario A:** 🟢 Baseline Ambient (Safe Autumn dry conditions across all 8 states).
- **Scenario B:** 🌧️ Extreme Monsoon Deluge (Torrential downpours in Cherrapunji, Mawsynram, and Dima Hasao triggering Red evacuation alerts).
- **Scenario C:** ⚡ Post-Earthquake Slope Destabilization (M5.4 tremor along Sikkim NH-10 corridor causing high tilt velocity).
- **Scenario D:** 🚨 Deep Railway Bed Creep (Saturated slope failure along Manipur Tupul railway & Kohima NH-29).
- **Scenario E:** 🛠️ Interactive Sensor Sandbox (Judges can drag sliders for rainfall, slope, pore pressure, and seismic load to test live AI inference!).

### 5. Multi-Channel & Multilingual Early Warning System
- **NDMA CAP v1.2 Format:** Generates standardized JSON/XML emergency payloads conforming to India's national SACHET disaster warning portal.
- **Multilingual Dispatches:** Automatic translation into **English**, **Hindi**, **Assamese (অসমীয়া)**, **Bengali (বাংলা)**, and **Mizo**.
- **Downloadable Incident SITREP:** Automated Markdown situation reports for District Disaster Management Authorities (DDMA) and SDRF/NDRF teams.
- **Drone Aerial Computer Vision:** Inspects drone orthomosaics for surface tension fissures, scarp deformation, and vegetative canopy loss, performing dual-verification multi-modal risk fusion.
- **Live Real-World Weather Feeds:** Connects directly to Open-Meteo API to stream real-time precipitation and atmospheric telemetry for actual NER coordinates.

---

## 📁 5. Project Directory Structure

```text
tech expo project/
├── .venv/                     # Python virtual environment
├── data/
│   ├── sample_drone_images/   # Test aerial imagery for Computer Vision
│   ├── ner_stations.json      # Station registries & coordinates
│   └── historical_landslides_ner.csv
├── docs/                      # Complete Tech Expo Documentation Suite
│   ├── PROJECT_TECHNICAL_REPORT.md   # IEEE-style comprehensive project paper
│   ├── EXPO_PRESENTATION_SLIDES.md   # 10-slide ready-to-present deck with speaker notes
│   ├── JUDGE_QA_DEFENSE_SHEET.md     # Top 12 tough questions & winning answers
│   └── EXPO_POSTER_LAYOUT.md         # A0/A1 exhibition poster layout & blueprint
├── models/
│   └── landslide_rf_model.joblib    # Trained Random Forest model (ROC-AUC: 0.997)
├── src/
│   ├── __init__.py
│   ├── data_manager.py        # NER stations & geological parameters
│   ├── ai_model.py            # AI predictor, Caine curve & Saito method
│   ├── iot_simulator.py       # Multi-sensor simulator & Open-Meteo live API
│   ├── vision_analyzer.py     # Drone aerial crack & fissure computer vision
│   └── ews_dispatcher.py      # CAP v1.2 alerting & multilingual alerts
├── app.py                     # Main Streamlit command center dashboard
├── run_demo.bat               # One-click Windows launcher
├── requirements.txt           # Project dependencies
└── README.md                  # Quickstart & system documentation
```

---

## 🎤 6. Presentation Script / Walkthrough for Tech Expo

When presenting to judges or visitors at the expo booth:

1. **Hook (30 seconds):**
   > *"Good morning! Landslides in the North Eastern Region of India cause catastrophic loss of life and disconnect entire states during the monsoons. Current warning systems either rely solely on weather forecasts or lack automated action. We built an AI-based early warning system that combines IoT ground sensors with physics-informed AI to predict landslides hours before they occur."*

2. **Geospatial Map Walkthrough (1 minute):**
   > *"On our live command center, you can see 12 high-risk monitoring stations across all 8 Northeastern states—including the NH-10 corridor in Sikkim, the Dima Hasao railway, and Cherrapunji in Meghalaya. Each station monitors 24h rainfall, soil moisture, pore water pressure, and slope displacement."*

3. **Demonstrating Scenario Presets (1 minute):**
   > *"Let's switch to Scenario B: Extreme Monsoon Deluge. Instantly, our AI detects pore water pressure exceeding 55 kPa and rainfall crossing the Eastern Himalayan Intensity-Duration threshold. The stations in Meghalaya and Assam transition into Critical Red alerts."*

4. **Showing Saito Time-to-Failure & Explainable AI (1 minute):**
   > *"Under Station Telemetry, judges can see our Explainable AI bar chart showing exactly why the slope is failing. If displacement accelerates, our system runs Saito's inverse velocity algorithm to calculate the estimated hours remaining until slope collapse."*

5. **Live Judge Sandbox Interaction (1 minute):**
   > *"Judge, feel free to adjust this slider for pore water pressure or rainfall in our Sensor Sandbox tab. Notice how the AI recalculates the Landslide Susceptibility Index in real time!"*

6. **Early Warning & Multilingual Dispatch (30 seconds):**
   > *"Finally, the system doesn't just predict—it acts. It generates NDMA CAP v1.2 alerts and dispatches immediate warning SMS in English, Hindi, Assamese, Bengali, and Mizo, while triggering automated siren protocols."*

---

## 📜 License
Developed for Academic and Exhibition Demonstration purposes under the Apache 2.0 License.
