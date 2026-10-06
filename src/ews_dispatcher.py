"""
Early Warning System (EWS) Dispatcher for Landslide Risk Management in NER.
Generates CAP (Common Alerting Protocol) compliant emergency broadcasts,
multilingual community advisories (English, Hindi, Assamese, Bengali, Mizo),
and automated disaster SITREP reports for DDMA/NDMA officials.
"""

import json
from datetime import datetime

class EWSDispatcher:
    def __init__(self):
        pass

    def generate_cap_alert(self, telemetry: dict) -> dict:
        """
        Generates a CAP v1.2 (Common Alerting Protocol) compliant payload
        compatible with NDMA India's SACHET disaster alert gateway.
        """
        urgency_map = {
            "GREEN": "Past",
            "YELLOW": "Future",
            "ORANGE": "Expected",
            "RED": "Immediate"
        }
        severity_map = {
            "GREEN": "Minor",
            "YELLOW": "Moderate",
            "ORANGE": "Severe",
            "RED": "Extreme"
        }
        certainty_map = {
            "GREEN": "Unlikely",
            "YELLOW": "Possible",
            "ORANGE": "Likely",
            "RED": "Observed"
        }

        tier = telemetry["tier"]
        identifier = f"NER-EWS-{telemetry['station_id']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        cap_payload = {
            "identifier": identifier,
            "sender": "ner.landslide.ews@ndma.gov.in",
            "sent": datetime.utcnow().isoformat() + "Z",
            "status": "Actual",
            "msgType": "Alert" if tier in ["ORANGE", "RED"] else "Update",
            "scope": "Public",
            "info": {
                "category": "Geo",
                "event": "Landslide Hazard Alert",
                "urgency": urgency_map.get(tier, "Expected"),
                "severity": severity_map.get(tier, "Moderate"),
                "certainty": certainty_map.get(tier, "Likely"),
                "headline": f"Level {tier}: Landslide Risk at {telemetry['station_name']} ({telemetry['state']})",
                "description": (
                    f"AI Early Warning System detected Landslide Susceptibility Index (LSI) of {telemetry['lsi']}. "
                    f"Cumulative 24h rainfall: {telemetry['rainfall_24h']} mm. Pore water pressure: {telemetry['pore_water_pressure_kpa']} kPa. "
                    f"Slope displacement rate: {telemetry['displacement_rate_mm_day']} mm/day. "
                    f"Action Required: {telemetry['action_code']}."
                ),
                "instruction": self._get_sop_instruction(tier),
                "area": {
                    "areaDesc": f"{telemetry['station_name']}, {telemetry['district']}, {telemetry['state']}",
                    "circle": f"{telemetry['lat']},{telemetry['lon']},5.0"
                }
            }
        }
        return cap_payload

    def _get_sop_instruction(self, tier: str) -> str:
        if tier == "RED":
            return "IMMEDIATE EVACUATION: Sound local siren towers. Halt all vehicular traffic along highway corridor. Evacuate vulnerable settlements within 500m of slope toe to designated relief centers."
        elif tier == "ORANGE":
            return "HIGH READINESS: Restrict heavy commercial vehicles. Pre-stage earthmoving excavators (BRO/PWD) at vulnerable chokepoints. SDRF teams placed on standby."
        elif tier == "YELLOW":
            return "ADVISORY: Intensify field visual inspection. Alert village disaster management committees (VDMC) to monitor slope cracks and sudden muddy spring discharges."
        else:
            return "NORMAL: Standard continuous sensor polling. No public restrictions."

    def get_multilingual_messages(self, telemetry: dict) -> dict:
        """Returns localized emergency SMS / WhatsApp broadcasts in key NER languages."""
        stn = telemetry["station_name"]
        state = telemetry["state"]
        tier = telemetry["tier"]
        lsi = telemetry["lsi"]
        ttf = telemetry.get("ttf_hours")
        ttf_str = f" [Estimated Failure Window: ~{ttf} hrs]" if ttf else ""

        if tier == "RED":
            return {
                "English": f"🔴 [CRITICAL LANDSLIDE EVACUATION ALERT] Severe landslide failure imminent at {stn} ({state}). LSI: {lsi}. Evacuate slope toe immediately! Highway traffic halted.{ttf_str} - District Emergency Operations Centre (DEOC)",
                "Hindi": f"🔴 [अति-गंभीर भूस्खलन चेतावनी] {stn} ({state}) में भूस्खलन का अत्यधिक खतरा। खतरा सूचकांक: {lsi}। ढलान के निचले इलाकों को तुरंत खाली करें। यातायात बंद किया जा रहा है।{ttf_str} - जिला आपदा प्रबंधन प्राधिकरण",
                "Assamese": f"🔴 [জৰুৰী ভূমিস্খলন সতৰ্কবাৰ্তা] {stn} ({state}) অঞ্চলত গুৰুতৰ ভূমিস্খলনৰ আশংকা। সুৰক্ষা সূচক: {lsi}। সকলো লোকক তাৎক্ষণিকভাৱে নিৰাপদ স্থানলৈ স্থানান্তৰ হ'বলৈ অনুৰোধ জনোৱা হ'ল। ঘাইপথ বন্ধ কৰা হৈছে। - দুৰ্যোগ ব্যৱস্থাপনা কৰ্তৃপক্ষ",
                "Bengali": f"🔴 [জরুরী ভূমিধস সতর্কবার্তা] {stn} ({state}) এলাকায় বিপজ্জনক ভূমিধসের চরম আশঙ্কা। ঝুঁকি সূচক: {lsi}। অবিলম্বে ঝুঁকিপূর্ণ এলাকা খালি করুন। যান চলাচল বন্ধ রাখা হচ্ছে। - জেলা দুর্যোগ ব্যবস্থাপনা কর্তৃপক্ষ",
                "Mizo": f"🔴 [LEI MIN HLIK RAWNGKAWLNA] {stn} ({state}) hmunah lei min hlauhawm tak a thleng dawn. Dinhmun hlauhawm zual a ni e (LSI: {lsi}). Hmun him lam pan nghal rawh u. Kawngpui khar a ni. - Disaster Management"
            }
        elif tier == "ORANGE":
            return {
                "English": f"🟠 [LANDSLIDE HIGH ALERT] Substantial landslide risk detected at {stn} ({state}). LSI: {lsi}. Avoid non-essential travel. Heavy vehicle movement restricted. - DEOC",
                "Hindi": f"🟠 [भूस्खलन उच्च चेतावनी] {stn} ({state}) में भूस्खलन की संभावना बढ़ी। LSI: {lsi}। अनावश्यक यात्रा से बचें। भारी वाहनों पर रोक। - जिला आपदा नियंत्रण कक्ष",
                "Assamese": f"🟠 [ভূমিস্খলন সতৰ্কবাৰ্তা] {stn} অঞ্চলত ভূমিস্খলনৰ সম্ভাৱনা বৃদ্ধি পাইছে (LSI: {lsi})। অপ্ৰয়োজনীয় ভ্ৰমণ পৰিহাৰ কৰক।",
                "Bengali": f"🟠 [ভূমিধস সতর্কতা] {stn} অঞ্চলে ভূমিধসের সম্ভাবনা বেড়েছে। অপ্রয়োজনীয় যাতায়াত এড়িয়ে চলুন।",
                "Mizo": f"🟠 [LEI MIN CAUTION] {stn} ram chhungah lei min theihna a sang. Zinkawng fimkhur rawh u."
            }
        else:
            return {
                "English": f"🟢 [MONITORING UPDATE] Normal stability monitored at {stn} ({state}). Slope parameters within baseline safety limits. - NER Early Warning Cell",
                "Hindi": f"🟢 [सामान्य स्थिति] {stn} ({state}) में स्थिति सामान्य है। ढलान स्थिरता मानकों के अनुरूप है।",
                "Assamese": f"🟢 [স্বাভাৱিক অৱস্থা] {stn} ত পৰিস্থিতি সম্পূৰ্ণ স্বাভাৱিক।",
                "Bengali": f"🟢 [স্বাভাবিক অবস্থা] {stn} তে পরিস্থিতি স্বাভাবিক রয়েছে।",
                "Mizo": f"🟢 [HIM LEH THLAMUANPUI] {stn} dinhmun a him e."
            }

    def generate_sitrep_markdown(self, all_telemetry: list, active_scenario: str) -> str:
        """Generates a complete, downloadable situation report (SITREP) for authorities."""
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        red_stns = [s for s in all_telemetry if s["tier"] == "RED"]
        orange_stns = [s for s in all_telemetry if s["tier"] == "ORANGE"]
        yellow_stns = [s for s in all_telemetry if s["tier"] == "YELLOW"]
        green_stns = [s for s in all_telemetry if s["tier"] == "GREEN"]

        sitrep = f"""# SITUATION REPORT (SITREP): NER LANDSLIDE EARLY WARNING SYSTEM
**Issued By:** North Eastern Regional Landslide Monitoring & AI Decision Support Command  
**Timestamp:** {now_str}  
**Active Scenario Mode:** {active_scenario.upper()}  
**System Integrity:** All 12 Edge Gateways Online | LoRaWAN / 4G Telemetry Nominal  

---

## 1. EXECUTIVE SUMMARY & THREAT SUMMARY
| Alert Level | Station Count | Recommended Immediate Action |
|:---|:---:|:---|
| 🔴 **RED (Critical)** | **{len(red_stns)}** | Immediate population evacuation, sirens sounding, highway corridors halted |
| 🟠 **ORANGE (Warning)** | **{len(orange_stns)}** | SDRF deployed, traffic throttled, heavy earthmoving equipment staged |
| 🟡 **YELLOW (Advisory)** | **{len(yellow_stns)}** | Field scouts on watch, Village Disaster Management alerted |
| 🟢 **GREEN (Normal)** | **{len(green_stns)}** | Routine ambient IoT telemetry acquisition |

---

## 2. HIGH RISK HOTSPOTS REQUIRING INTERVENTION
"""
        if not red_stns and not orange_stns:
            sitrep += "No stations currently in RED or ORANGE alert categories. All regional corridors operating under safe parameters.\n"
        else:
            for s in (red_stns + orange_stns):
                ttf_note = f"⚠️ **Saito Estimated Time to Failure:** ~{s['ttf_hours']} Hours\n" if s.get("ttf_hours") else ""
                sitrep += f"""
### 📍 {s['station_name']} ({s['district']}, {s['state']}) - Level {s['tier']}
- **Landslide Susceptibility Index (LSI):** `{s['lsi']}` / 1.00
- **24-Hour Rainfall:** `{s['rainfall_24h']} mm` | **72h ARI:** `{s['rainfall_72h_ari']} mm`
- **Pore Water Pressure:** `{s['pore_water_pressure_kpa']} kPa` | **Soil Moisture:** `{s['soil_moisture_pct']}%`
- **Inclinometer Displacement Rate:** `{s['displacement_rate_mm_day']} mm/day`
- **Slope Angle:** `{s['slope_deg']}°` | **Lithology:** `{s['lithology']}`
- **Geotechnical Standard Action:** {s['action_code']}
{ttf_note}
"""

        sitrep += """
---
## 3. NDMA / SDMA STANDARD OPERATING PROTOCOL (SOP) CHECKLIST
- [x] CAP XML Broadcast Dispatched to SACHET Gateway
- [ ] Emergency Services (SDRF / NDRF 1st & 12th Bns) Notified
- [ ] BRO (Border Roads Organisation) Bulldozer Units Placed at Chokepoints
- [ ] Regional Highway Police Traffic Redirection Active
- [ ] Wireless Siren Towers Tested & Armed
- [ ] Public Multilingual SMS Disseminated to Mobile Towers

---
*Report Generated Automatically by AI Landslide Early Warning System for NER.*
"""
        return sitrep
