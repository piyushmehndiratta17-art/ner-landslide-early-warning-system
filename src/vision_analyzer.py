"""
Vision Analysis Module for Drone / Aerial Slope Inspection in NER.
Analyzes aerial slope imagery for tension cracks, surface fissures, and vegetation loss.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import os

class DroneSlopeAnalyzer:
    def __init__(self):
        pass

    def analyze_image(self, pil_image: Image.Image) -> dict:
        """
        Analyzes an aerial slope image for geomorphological instability markers:
        - Fissure & Tension Crack Density (edge gradients)
        - Vegetation loss / Bare soil ratio
        - Surface roughness / texture irregularity
        """
        # Convert to RGB
        img_rgb = pil_image.convert("RGB")
        width, height = img_rgb.size

        # Resize for consistent rapid analysis
        img_resized = img_rgb.resize((400, 300))
        img_np = np.array(img_resized)

        # 1. Vegetation Index (Green vs Red/Blue ratio)
        r = img_np[:, :, 0].astype(float)
        g = img_np[:, :, 1].astype(float)
        b = img_np[:, :, 2].astype(float)

        # Excess Green Index (2G - R - B)
        exg = (2 * g - r - b)
        vegetation_mask = exg > 15
        vegetation_pct = float(np.mean(vegetation_mask) * 100.0)
        bare_soil_pct = round(100.0 - vegetation_pct, 1)

        # 2. Structural Edge / Crack Detection
        gray_img = img_resized.convert("L")
        # Apply high-pass edge filter
        edges = gray_img.filter(ImageFilter.FIND_EDGES)
        edges_np = np.array(edges)
        
        # High intensity edges represent sharp fissure boundaries / tension cracks
        crack_mask = edges_np > 55
        crack_density_pct = round(float(np.mean(crack_mask) * 100.0), 2)

        # 3. Surface Roughness (Local standard deviation)
        roughness_score = round(float(np.std(edges_np) / 255.0), 3)

        # 4. Composite Visual Instability Index (VII: 0.0 - 1.0)
        # Higher cracks + higher bare soil + higher roughness = higher risk
        raw_vii = (
            (crack_density_pct / 12.0) * 0.45 +
            (bare_soil_pct / 100.0) * 0.35 +
            (roughness_score / 0.35) * 0.20
        )
        vii = round(float(np.clip(raw_vii, 0.05, 0.98)), 3)

        # Categorize Visual Threat Level
        if vii < 0.30:
            tier = "LOW"
            color = "#10B981"
            diagnosis = "Stable Slope: High vegetative canopy cover, no discernible structural shear cracks."
        elif vii < 0.60:
            tier = "MODERATE"
            color = "#F59E0B"
            diagnosis = "Incipient Instability: Minor surface erosion and localized tension micro-cracks observed."
        elif vii < 0.80:
            tier = "HIGH"
            color = "#F97316"
            diagnosis = "Active Subsidence Scarp: Pronounced tension cracks and extensive slope face exposure."
        else:
            tier = "CRITICAL"
            color = "#EF4444"
            diagnosis = "Imminent Slope Failure: Major structural shear fractures and massive talus overburden detachment."

        # Create Annotated Visualization overlay highlighting cracks
        annotated = img_resized.copy()
        draw = ImageDraw.Draw(annotated)
        
        # Highlight regions with high crack concentration
        y_indices, x_indices = np.where(edges_np > 75)
        step = max(1, len(x_indices) // 150)
        for i in range(0, len(x_indices), step):
            px_x, px_y = x_indices[i], y_indices[i]
            draw.rectangle([px_x - 1, px_y - 1, px_x + 1, px_y + 1], outline="#EF4444", fill="#EF4444")

        return {
            "vii_score": vii,
            "tier": tier,
            "color": color,
            "diagnosis": diagnosis,
            "crack_density_pct": crack_density_pct,
            "bare_soil_pct": bare_soil_pct,
            "vegetation_pct": round(vegetation_pct, 1),
            "roughness_score": roughness_score,
            "annotated_image": annotated
        }

def generate_sample_images(output_dir: str):
    """Generates synthetic test drone images for expo demonstration."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Stable Forested Slope
    img_stable = Image.new("RGB", (400, 300), color=(45, 95, 45))
    draw_s = ImageDraw.Draw(img_stable)
    np.random.seed(42)
    # add canopy textures
    for _ in range(600):
        x = np.random.randint(0, 400)
        y = np.random.randint(0, 300)
        r = np.random.randint(25, 65)
        g = np.random.randint(85, 155)
        b = np.random.randint(25, 60)
        draw_s.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(r, g, b))
    img_stable.save(os.path.join(output_dir, "sample_stable_slope.jpg"))

    # 2. Developing Tension Crack Slope
    img_crack = Image.new("RGB", (400, 300), color=(90, 80, 60))
    draw_c = ImageDraw.Draw(img_crack)
    # patchy vegetation
    for _ in range(350):
        x = np.random.randint(0, 400)
        y = np.random.randint(0, 300)
        draw_c.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(50, 110, 45))
    # draw noticeable tension fracture lines
    for _ in range(3):
        start_x = np.random.randint(50, 200)
        start_y = np.random.randint(50, 150)
        points = [(start_x, start_y)]
        curr_x, curr_y = start_x, start_y
        for step in range(8):
            curr_x += np.random.randint(15, 30)
            curr_y += np.random.randint(-8, 18)
            points.append((curr_x, curr_y))
        draw_c.line(points, fill=(25, 20, 15), width=3)
    img_crack.save(os.path.join(output_dir, "sample_tension_crack_slope.jpg"))

    # 3. Severe Scarp / Collapse Zone
    img_severe = Image.new("RGB", (400, 300), color=(145, 120, 95))
    draw_sev = ImageDraw.Draw(img_severe)
    # rock and talus debris
    for _ in range(500):
        x = np.random.randint(0, 400)
        y = np.random.randint(0, 300)
        shade = np.random.randint(80, 180)
        draw_sev.rectangle([x, y, x + 4, y + 4], fill=(shade, shade - 20, shade - 35))
    # deep jagged fissures across the face
    for line_idx in range(6):
        start_x = np.random.randint(20, 250)
        start_y = 30 + line_idx * 40
        pts = [(start_x, start_y)]
        cx, cy = start_x, start_y
        for _ in range(12):
            cx += np.random.randint(10, 25)
            cy += np.random.randint(-12, 16)
            pts.append((cx, cy))
        draw_sev.line(pts, fill=(15, 10, 10), width=4)
    img_severe.save(os.path.join(output_dir, "sample_severe_collapse_scarp.jpg"))
