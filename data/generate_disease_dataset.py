"""
Generate a realistic Plant Disease Detection dataset.

This script creates 'Disease_Detection.csv' with image-derived color features
mapped to plant disease labels. The features simulate what would be extracted
from real leaf images using color analysis (RGB means, std devs, color ratios,
texture approximation).

Disease categories are based on common crop diseases found in Indian agriculture,
consistent with the smart farming project scope.

Data is generated using realistic statistical distributions based on published
research on plant disease image analysis.
"""
from __future__ import annotations

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import random
from typing import Any

random.seed(42)
np.random.seed(42)

# ─── Disease Profiles ───────────────────────────────────────────────────────
# Each disease has characteristic color signatures when analyzed from leaf images.
# Format: (mean, std) for each feature
disease_profiles = {
    "Healthy": {
        "avg_red": (85, 15),
        "avg_green": (145, 20),
        "avg_blue": (60, 12),
        "std_red": (25, 8),
        "std_green": (30, 10),
        "std_blue": (18, 6),
        "green_ratio": (0.52, 0.06),
        "disease_ratio": (0.05, 0.03),
        "brown_ratio": (0.04, 0.02),
        "yellow_ratio": (0.06, 0.03),
        "texture_contrast": (0.15, 0.05),
        "texture_energy": (0.72, 0.08),
        "brightness": (110, 18),
        "saturation": (0.45, 0.08),
        "samples": 200,
    },
    "Early Blight": {
        "avg_red": (120, 18),
        "avg_green": (105, 15),
        "avg_blue": (55, 10),
        "std_red": (35, 10),
        "std_green": (28, 8),
        "std_blue": (20, 7),
        "green_ratio": (0.30, 0.07),
        "disease_ratio": (0.28, 0.08),
        "brown_ratio": (0.22, 0.06),
        "yellow_ratio": (0.15, 0.05),
        "texture_contrast": (0.42, 0.10),
        "texture_energy": (0.48, 0.10),
        "brightness": (95, 15),
        "saturation": (0.35, 0.07),
        "samples": 180,
    },
    "Late Blight": {
        "avg_red": (95, 16),
        "avg_green": (90, 14),
        "avg_blue": (72, 12),
        "std_red": (32, 9),
        "std_green": (25, 7),
        "std_blue": (25, 8),
        "green_ratio": (0.25, 0.06),
        "disease_ratio": (0.32, 0.09),
        "brown_ratio": (0.18, 0.05),
        "yellow_ratio": (0.10, 0.04),
        "texture_contrast": (0.50, 0.12),
        "texture_energy": (0.40, 0.09),
        "brightness": (85, 14),
        "saturation": (0.28, 0.06),
        "samples": 170,
    },
    "Leaf Spot": {
        "avg_red": (110, 17),
        "avg_green": (115, 16),
        "avg_blue": (50, 11),
        "std_red": (40, 12),
        "std_green": (35, 10),
        "std_blue": (22, 7),
        "green_ratio": (0.35, 0.07),
        "disease_ratio": (0.22, 0.07),
        "brown_ratio": (0.25, 0.07),
        "yellow_ratio": (0.12, 0.04),
        "texture_contrast": (0.55, 0.13),
        "texture_energy": (0.42, 0.10),
        "brightness": (100, 16),
        "saturation": (0.38, 0.07),
        "samples": 170,
    },
    "Rust": {
        "avg_red": (155, 20),
        "avg_green": (110, 15),
        "avg_blue": (40, 10),
        "std_red": (30, 9),
        "std_green": (25, 8),
        "std_blue": (15, 5),
        "green_ratio": (0.22, 0.06),
        "disease_ratio": (0.35, 0.08),
        "brown_ratio": (0.15, 0.05),
        "yellow_ratio": (0.25, 0.07),
        "texture_contrast": (0.38, 0.09),
        "texture_energy": (0.50, 0.08),
        "brightness": (105, 17),
        "saturation": (0.50, 0.08),
        "samples": 160,
    },
    "Powdery Mildew": {
        "avg_red": (140, 18),
        "avg_green": (145, 18),
        "avg_blue": (130, 16),
        "std_red": (22, 7),
        "std_green": (24, 8),
        "std_blue": (28, 9),
        "green_ratio": (0.28, 0.06),
        "disease_ratio": (0.18, 0.06),
        "brown_ratio": (0.08, 0.03),
        "yellow_ratio": (0.10, 0.04),
        "texture_contrast": (0.25, 0.07),
        "texture_energy": (0.62, 0.09),
        "brightness": (140, 18),
        "saturation": (0.15, 0.05),
        "samples": 150,
    },
    "Bacterial Blight": {
        "avg_red": (100, 16),
        "avg_green": (100, 14),
        "avg_blue": (60, 11),
        "std_red": (38, 11),
        "std_green": (32, 9),
        "std_blue": (20, 7),
        "green_ratio": (0.28, 0.07),
        "disease_ratio": (0.30, 0.08),
        "brown_ratio": (0.20, 0.06),
        "yellow_ratio": (0.18, 0.06),
        "texture_contrast": (0.48, 0.11),
        "texture_energy": (0.44, 0.09),
        "brightness": (88, 14),
        "saturation": (0.32, 0.07),
        "samples": 160,
    },
    "Mosaic Virus": {
        "avg_red": (95, 15),
        "avg_green": (130, 18),
        "avg_blue": (55, 10),
        "std_red": (30, 9),
        "std_green": (40, 12),
        "std_blue": (18, 6),
        "green_ratio": (0.38, 0.08),
        "disease_ratio": (0.15, 0.06),
        "brown_ratio": (0.08, 0.03),
        "yellow_ratio": (0.28, 0.08),
        "texture_contrast": (0.35, 0.09),
        "texture_energy": (0.52, 0.10),
        "brightness": (98, 15),
        "saturation": (0.40, 0.07),
        "samples": 140,
    },
    "Downy Mildew": {
        "avg_red": (105, 16),
        "avg_green": (120, 16),
        "avg_blue": (80, 13),
        "std_red": (28, 8),
        "std_green": (30, 9),
        "std_blue": (25, 8),
        "green_ratio": (0.32, 0.07),
        "disease_ratio": (0.22, 0.07),
        "brown_ratio": (0.12, 0.04),
        "yellow_ratio": (0.18, 0.06),
        "texture_contrast": (0.32, 0.08),
        "texture_energy": (0.55, 0.09),
        "brightness": (105, 16),
        "saturation": (0.30, 0.06),
        "samples": 140,
    },
    "Anthracnose": {
        "avg_red": (90, 15),
        "avg_green": (80, 13),
        "avg_blue": (55, 10),
        "std_red": (35, 10),
        "std_green": (28, 8),
        "std_blue": (22, 7),
        "green_ratio": (0.22, 0.06),
        "disease_ratio": (0.35, 0.09),
        "brown_ratio": (0.28, 0.07),
        "yellow_ratio": (0.08, 0.03),
        "texture_contrast": (0.58, 0.14),
        "texture_energy": (0.38, 0.09),
        "brightness": (78, 13),
        "saturation": (0.33, 0.06),
        "samples": 140,
    },
}

# ─── Crop Types affected by each disease ─────────────────────────────────
disease_crops = {
    "Healthy": ["Rice", "Wheat", "Maize", "Tomato", "Potato", "Cotton", "Sugarcane", "Soybean", "Groundnut", "Grape"],
    "Early Blight": ["Tomato", "Potato", "Chili"],
    "Late Blight": ["Tomato", "Potato"],
    "Leaf Spot": ["Rice", "Wheat", "Maize", "Cotton", "Groundnut", "Soybean"],
    "Rust": ["Wheat", "Maize", "Soybean", "Sugarcane", "Coffee"],
    "Powdery Mildew": ["Grape", "Wheat", "Tomato", "Mango", "Rose"],
    "Bacterial Blight": ["Rice", "Cotton", "Pomegranate", "Citrus"],
    "Mosaic Virus": ["Tomato", "Tobacco", "Cassava", "Sugarcane"],
    "Downy Mildew": ["Grape", "Maize", "Sunflower", "Cucumber"],
    "Anthracnose": ["Mango", "Chili", "Grape", "Papaya", "Banana"],
}

# ─── Treatment recommendations ───────────────────────────────────────────
disease_treatments = {
    "Healthy": "No treatment needed. Continue regular maintenance and monitoring.",
    "Early Blight": "Apply Mancozeb or Chlorothalonil fungicide. Remove affected leaves. Ensure proper spacing.",
    "Late Blight": "Apply Metalaxyl + Mancozeb. Remove infected plants immediately. Avoid overhead irrigation.",
    "Leaf Spot": "Apply Carbendazim or Copper oxychloride. Improve air circulation. Use disease-free seeds.",
    "Rust": "Apply Propiconazole or Tebuconazole. Remove infected plant debris. Choose resistant varieties.",
    "Powdery Mildew": "Apply Sulphur-based fungicide or Karathane. Prune dense canopy. Avoid excess nitrogen.",
    "Bacterial Blight": "Apply Streptomycin or Copper hydroxide. Use resistant varieties. Avoid field work in wet conditions.",
    "Mosaic Virus": "No cure available. Remove and destroy infected plants. Control aphid vectors with Imidacloprid.",
    "Downy Mildew": "Apply Metalaxyl or Ridomil Gold. Ensure good drainage. Avoid overhead watering.",
    "Anthracnose": "Apply Carbendazim or Thiophanate-methyl. Prune affected parts. Maintain field hygiene.",
}

# ─── Severity levels ─────────────────────────────────────────────────────
severity_levels = ["Mild", "Moderate", "Severe"]


def generate_sample(disease_name: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Generate a single sample with slight random variation."""
    sample: dict[str, Any] = {}
    
    for feature in ["avg_red", "avg_green", "avg_blue", "std_red", "std_green",
                     "std_blue", "green_ratio", "disease_ratio", "brown_ratio",
                     "yellow_ratio", "texture_contrast", "texture_energy",
                     "brightness", "saturation"]:
        mean, std = profile[feature]
        value = np.random.normal(mean, std)
        
        # Clamp values to realistic ranges
        if feature in ["avg_red", "avg_green", "avg_blue", "brightness"]:
            value = np.clip(value, 0, 255)
        elif feature in ["std_red", "std_green", "std_blue"]:
            value = np.clip(value, 1, 80)
        elif feature in ["green_ratio", "disease_ratio", "brown_ratio",
                         "yellow_ratio", "texture_contrast", "texture_energy",
                         "saturation"]:
            value = np.clip(value, 0.0, 1.0)
        
        sample[feature] = round(value, 4)
    
    # Assign crop type
    sample["crop_type"] = random.choice(disease_crops[disease_name])
    
    # Severity (only for diseases, not Healthy)
    if disease_name == "Healthy":
        sample["severity"] = "None"
    else:
        # Weight severity based on disease_ratio
        dr = float(sample["disease_ratio"])
        if dr < 0.20:
            sample["severity"] = "Mild"
        elif dr < 0.35:
            sample["severity"] = "Moderate"
        else:
            sample["severity"] = "Severe"
    
    sample["treatment"] = disease_treatments[disease_name]
    sample["label"] = disease_name
    
    return sample


# ─── Generate Dataset ────────────────────────────────────────────────────
all_samples = []

for disease_name, profile in disease_profiles.items():
    n_samples = int(profile["samples"])  # type: ignore[arg-type]
    for _ in range(n_samples):
        sample = generate_sample(disease_name, profile)
        all_samples.append(sample)

# Shuffle
random.shuffle(all_samples)

# Create DataFrame
df = pd.DataFrame(all_samples)

# Reorder columns
column_order = [
    "avg_red", "avg_green", "avg_blue",
    "std_red", "std_green", "std_blue",
    "green_ratio", "disease_ratio", "brown_ratio", "yellow_ratio",
    "texture_contrast", "texture_energy",
    "brightness", "saturation",
    "crop_type", "severity", "treatment", "label"
]
df = df[column_order]

# Save
output_path = "data/Disease_Detection.csv"
df.to_csv(output_path, index=False)

print(f"✅ Dataset generated successfully!")
print(f"   📁 File: {output_path}")
print(f"   📊 Total samples: {len(df)}")
print(f"   🏷️  Classes: {df['label'].nunique()}")
print(f"\n   Distribution:")
print(df['label'].value_counts().to_string())
print(f"\n   Feature columns: {len(column_order) - 4} features + crop_type + severity + treatment + label")
print(f"\n   First 5 rows:")
print(df.head().to_string())
