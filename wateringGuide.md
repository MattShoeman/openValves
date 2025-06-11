# 🌱 Smart Irrigation Watering Guide

## 💧 Understanding Plant Water Needs

### Key Watering Concepts
| Term            | Definition                          | Measurement               | Importance                     |
|-----------------|-------------------------------------|---------------------------|--------------------------------|
| **Water Depth** | Vertical water penetration          | Inches per session        | Ensures enough moisture        |
| **Root Depth**  | Depth of plant's root system        | Inches below soil         | Determines watering duration   |
| **Infiltration**| Soil's water absorption rate        | Inches per hour           | Prevents runoff               |

## 🌱 Plant Watering Requirements

### Weekly Recommendations
| Plant Type       | Water Depth | Root Depth | Ideal Frequency | Soil Preference |
|------------------|-------------|------------|-----------------|-----------------|
| Lawn Grass       | 1-1.5"      | 6-8"       | 2-3x/week       | Loam            |
| Vegetables       | 1-2"        | 12-18"     | Daily           | Sandy Loam      |
| Flower Beds      | 0.5-1"      | 6-12"      | 2x/week         | Loam            |
| Shrubs           | 1-1.5"      | 12-24"     | 1-2x/week       | Clay Loam       |
| Trees (Mature)   | 2-3"        | 24-36"     | 1x/week         | Varied          |

*Note: 1" water depth = 0.623 gallons per sq ft*

## ⚡ Sprinkler System Calculations

### 90° Pop-Up Sprinklers (3 GPM)
```math
\text{Coverage Area} = \pi r^2 \times \frac{\text{angle}}{360} = 314 \text{ sq ft}
\text{Runtime (min)} = \frac{\text{Area} \times \text{Depth} \times 0.623}{\text{GPM}}
```

Lawn Area: 400 sq ft  
Sprinklers: 2 × 3GPM  
Runtime: (400 × 1 × 0.623) / 6 = 42 minutes

Soil-Specific Strategies
Soil Type	Infiltration Rate	Watering Method	Visual Cue
Sand	2.0"/hr	Single long session	Water drains instantly
Loam	0.5-1.0"/hr	Two 30-min sessions	Moderate absorption
Clay	0.25"/hr	Four 15-min cycles	Puddles form quickly
💦 Drip Irrigation Guide

Tree Watering Example:
plaintext

3 × 1GPH emitters × 62 hours = 186 gallons
Expected Penetration in Clay:
[0-2hrs]  → Top 4" moist
[24hrs]   → Reaches 12"
[62hrs]   → Deep soak to 16"

⚙️ System Configuration Tips

    Morning Watering (5-9 AM) reduces evaporation

    Cycle & Soak for clay soils:
    yaml

    zone1:
      runtime: 15 min
      soak_time: 60 min
      cycles: 4

    Rain Sensor Settings:

        Skip if >0.5" rainfall

        Reduce by 50% if 0.25-0.5" forecasted

🌦️ Weather-Based Adjustments
python

# Smart system logic example
def adjust_watering(base_time, weather):
    if weather['rain'] > 0.5:
        return 0
    elif weather['temp'] > 85:
        return base_time * 1.25
    elif weather['humidity'] < 30:
        return base_time * 1.15
    else:
        return base_time

📊 Watering Cheat Sheet

Quick Reference:
plaintext

Plant Type      | Summer Runtime
----------------|---------------
Lawn (500 sq ft)| 52 min (1")
Vegetable Garden| 20 min daily
New Tree        | 60 min drip 2x/week
