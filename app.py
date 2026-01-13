import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Temp Edge Finder", page_icon="🌡️", layout="wide")

CITIES = {
    "NYC": {"lat": 40.7829, "lon": -73.9654, "name": "NYC (Central Park)", "tz": "America/New_York"},
    "Chicago": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago (O'Hare)", "tz": "America/Chicago"},
    "LA": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles", "tz": "America/Los_Angeles"},
    "Miami": {"lat": 25.7617, "lon": -80.1918, "name": "Miami", "tz": "America/New_York"},
    "Denver": {"lat": 39.7392, "lon": -104.9903, "name": "Denver", "tz": "America/Denver"},
}

def get_wind_direction(degrees):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(degrees / 45) % 8
    return dirs[idx]

def fetch_weather(city_key):
    city = CITIES[city_key]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}&current=temperature_2m,cloud_cover,wind_speed_10m,wind_direction_10m&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone={city['tz']}&forecast_days=1"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        return {
            "temp": current.get("temperature_2m", 0),
            "cloud": current.get("cloud_cover", 0),
            "wind": current.get("wind_speed_10m", 0),
            "wind_dir": current.get("wind_direction_10m", 0),
            "forecast_high": daily.get("temperature_2m_max", [0])[0],
            "forecast_low": daily.get("temperature_2m_min", [0])[0],
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_projection(weather, morning_low, current_hour):
    # Peak time based on cloud cover
    if weather["cloud"] >= 70:
        peak_hour = 14  # 2 PM overcast
    elif weather["cloud"] >= 40:
        peak_hour = 15  # 3 PM partly cloudy
    else:
        peak_hour = 16  # 4 PM clear
    
    # If past peak, current temp is near the high
    if current_hour >= peak_hour:
        return {
            "projected": weather["temp"],
            "method": "POST-PEAK",
            "confidence": "HIGH",
            "peak_hour": peak_hour,
            "pace": 0,
            "hours_remaining": 0
        }
    
    # Calculate warming pace
    warming_start = 7  # 7 AM
    hours_elapsed = max(current_hour - warming_start, 0.5)
    hours_remaining = peak_hour - current_hour
    
    temp_rise = weather["temp"] - morning_low
    pace = temp_rise / hours_elapsed
    
    # Project forward
    projected = weather["temp"] + (pace * hours_remaining)
    
    # Cloud cover dampening
    if weather["cloud"] >= 70:
        projected = min(projected, weather["temp"] + 3)
    elif weather["cloud"] >= 50:
        projected = min(projected, weather["temp"] + 5)
    
    # Wind advection adjustment
    wind_dir = get_wind_direction(weather["wind_dir"])
    if wind_dir in ["SW", "S"] and weather["wind"] >= 8:
        projected += 2  # Warm air
    elif wind_dir in ["NW", "N", "NE"] and weather["wind"] >= 8:
        projected -= 2  # Cold air
    
    # Confidence
    if current_hour >= 12:
        confidence = "HIGH"
    elif current_hour >= 10.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    return {
        "projected": round(projected, 1),
        "method": "PACE-FORWARD",
        "confidence": confidence,
        "peak_hour": peak_hour,
        "pace": round(pace, 2),
        "hours_remaining": round(hours_remaining, 1)
    }

# ========== MAIN APP ==========
st.title("🌡️ TEMP EDGE FINDER")

now = datetime.now(pytz.timezone('America/New_York'))
current_hour = now.hour + now.minute / 60
st.caption(f"Last update: {now.strftime('%I:%M:%S %p ET')}")

# City selection
selected_city = st.selectbox("City", list(CITIES.keys()), index=0)

# Fetch weather
weather = fetch_weather(selected_city)

if not weather["success"]:
    st.error(f"Failed to fetch weather: {weather.get('error', 'Unknown')}")
    st.stop()

st.success(f"🟢 Live data for {CITIES[selected_city]['name']}")

# Current conditions
st.subheader("CURRENT CONDITIONS")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Now", f"{weather['temp']:.1f}°F")
c2.metric("Clouds", f"{weather['cloud']}%")
c3.metric("Wind", f"{weather['wind']:.0f} mph")
c4.metric("Direction", get_wind_direction(weather['wind_dir']))

st.divider()

# Morning low input
morning_low = st.number_input("Morning Low (°F)", 0.0, 100.0, weather["forecast_low"], 1.0)

# Calculate projection
projection = calculate_projection(weather, morning_low, current_hour)

# Display projection vs forecast
st.subheader("PROJECTION VS MARKET")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📊 MARKET FORECAST")
    st.markdown(f"## {weather['forecast_high']:.0f}°F")
    st.caption("Open-Meteo forecast (what Kalshi prices)")

with col2:
    st.markdown("### 📍 OUR PROJECTION")
    st.markdown(f"## {projection['projected']:.1f}°F")
    st.caption(f"{projection['confidence']} confidence • {projection['method']}")

# Gap detection
gap = abs(projection["projected"] - weather["forecast_high"])
if gap >= 2:
    st.warning(f"⚡ **{gap:.1f}°F GAP DETECTED** — Edge opportunity!")
    if projection["projected"] < weather["forecast_high"]:
        target = int(weather["forecast_high"])
        st.info(f"Projection BELOW forecast → Look for **NO** on {target-1}-{target}°F and {target}-{target+1}°F brackets")
    else:
        target = int(weather["forecast_high"])
        st.info(f"Projection ABOVE forecast → Look for **NO** on {target}-{target+1}°F and {target+1}-{target+2}°F brackets")

st.divider()

# Projection details
st.subheader("PROJECTION DETAILS")
d1, d2, d3, d4 = st.columns(4)
d1.metric("Pace", f"{projection['pace']}°F/hr")
d2.metric("Hours to Peak", f"{projection['hours_remaining']}h")
d3.metric("Est. Peak", f"{projection['peak_hour']}:00")
d4.metric("Morning Low", f"{morning_low:.0f}°F")

st.divider()

# Bracket scanner
st.subheader("BRACKET SCANNER")

proj_int = int(round(projection["projected"]))
fcst_int = int(round(weather["forecast_high"]))
center = (proj_int + fcst_int) // 2

brackets = []
for i in range(-5, 6):
    low = center + i
    high = low + 1
    brackets.append((low, high))

cols = st.columns(len(brackets))
for i, (low, high) in enumerate(brackets):
    is_proj = proj_int == low or proj_int == high
    is_fcst = fcst_int == low or fcst_int == high
    
    label = f"**{low}-{high}°F**"
    
    if is_proj and is_fcst:
        cols[i].markdown(f"🎯 {label}")
        cols[i].caption("PROJ + FCST")
    elif is_proj:
        cols[i].markdown(f"📍 {label}")
        cols[i].caption("OUR PROJ")
    elif is_fcst:
        cols[i].markdown(f"📊 {label}")
        cols[i].caption("MARKET")
    elif gap >= 2 and ((projection["projected"] < weather["forecast_high"] and low >= fcst_int - 1 and low <= fcst_int) or
                       (projection["projected"] > weather["forecast_high"] and low <= fcst_int + 1 and low >= fcst_int)):
        cols[i].markdown(f"⚡ {label}")
        cols[i].caption("NO EDGE")
    else:
        cols[i].markdown(label)

st.divider()

with st.expander("📖 HOW IT WORKS"):
    st.markdown("""
    **Edge Finding Logic:**
    
    1. **Market Forecast** = Open-Meteo's predicted high (what Kalshi likely prices)
    2. **Our Projection** = Built from current temp + warming pace + conditions
    3. **Gap** = When they differ by 2°F+, edge exists
    
    **If projection < forecast:** Market is overpricing high brackets → NO edge
    **If projection > forecast:** Market is underpricing high brackets → YES edge on higher brackets
    
    **Best Window:** 10:30 AM - 2:00 PM for reliable signals
    """)

st.caption("v2.0 | Temp Edge Finder")
