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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}&current=temperature_2m,cloud_cover,wind_speed_10m,wind_direction_10m&hourly=temperature_2m&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone={city['tz']}&forecast_days=1"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})
        return {
            "temp": current.get("temperature_2m", 0),
            "cloud": current.get("cloud_cover", 0),
            "wind": current.get("wind_speed_10m", 0),
            "wind_dir": current.get("wind_direction_10m", 0),
            "forecast_high": daily.get("temperature_2m_max", [0])[0],
            "forecast_low": daily.get("temperature_2m_min", [0])[0],
            "hourly_temps": hourly.get("temperature_2m", []),
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_high_projection(weather, morning_low, current_hour):
    # Peak time based on cloud cover
    if weather["cloud"] >= 70:
        peak_hour = 14
    elif weather["cloud"] >= 40:
        peak_hour = 15
    else:
        peak_hour = 16
    
    if current_hour >= peak_hour:
        return {
            "projected": weather["temp"],
            "method": "POST-PEAK",
            "confidence": "HIGH",
            "peak_hour": peak_hour,
            "pace": 0,
            "hours_remaining": 0
        }
    
    warming_start = 7
    hours_elapsed = max(current_hour - warming_start, 0.5)
    hours_remaining = peak_hour - current_hour
    
    temp_rise = weather["temp"] - morning_low
    pace = temp_rise / hours_elapsed
    
    projected = weather["temp"] + (pace * hours_remaining)
    
    if weather["cloud"] >= 70:
        projected = min(projected, weather["temp"] + 3)
    elif weather["cloud"] >= 50:
        projected = min(projected, weather["temp"] + 5)
    
    wind_dir = get_wind_direction(weather["wind_dir"])
    if wind_dir in ["SW", "S"] and weather["wind"] >= 8:
        projected += 2
    elif wind_dir in ["NW", "N", "NE"] and weather["wind"] >= 8:
        projected -= 2
    
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

def calculate_low_projection(weather, current_hour, hourly_temps):
    # Low typically occurs at sunrise (~6-7 AM)
    # If before 9 AM, we can still observe/project the low
    # If after 9 AM, the low has already occurred
    
    if current_hour <= 9:
        # Still in low window - current or recent temps matter
        # Find minimum from hourly data (overnight hours 0-9)
        if hourly_temps and len(hourly_temps) >= 9:
            overnight_temps = hourly_temps[0:9]
            observed_low = min(overnight_temps)
        else:
            observed_low = weather["temp"]
        
        # Could still drop if before sunrise
        if current_hour < 7:
            # Pre-sunrise, might drop more
            projected = min(weather["temp"] - 1, observed_low)
            confidence = "MEDIUM"
            method = "PRE-SUNRISE"
        else:
            # Post-sunrise, low is likely set
            projected = observed_low
            confidence = "HIGH"
            method = "OBSERVED"
    else:
        # After 9 AM - low is locked in
        if hourly_temps and len(hourly_temps) >= 9:
            projected = min(hourly_temps[0:9])
        else:
            projected = weather["forecast_low"]
        confidence = "LOCKED"
        method = "OVERNIGHT MIN"
    
    return {
        "projected": round(projected, 1),
        "method": method,
        "confidence": confidence
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

# ========== MARKET TYPE SELECTION ==========
market_type = st.radio("Market Type", ["HIGH", "LOW"], horizontal=True)

st.divider()

if market_type == "HIGH":
    # ========== HIGH TEMPERATURE ==========
    st.header("🔥 HIGH TEMPERATURE")
    
    morning_low = st.number_input("Morning Low (°F)", 0.0, 100.0, weather["forecast_low"], 1.0,
                                   help="Lowest temp this morning - used to calculate warming pace")
    
    projection = calculate_high_projection(weather, morning_low, current_hour)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 MARKET FORECAST")
        st.markdown(f"## {weather['forecast_high']:.0f}°F")
        st.caption("Open-Meteo (what Kalshi prices)")
    
    with col2:
        st.markdown("### 📍 OUR PROJECTION")
        st.markdown(f"## {projection['projected']:.1f}°F")
        st.caption(f"{projection['confidence']} confidence • {projection['method']}")
    
    gap = projection["projected"] - weather["forecast_high"]
    
    if abs(gap) >= 2:
        st.warning(f"⚡ **{abs(gap):.1f}°F GAP** — Edge opportunity!")
        target = int(weather["forecast_high"])
        if gap < 0:
            st.info(f"Projection BELOW forecast → **NO** on {target-1}-{target}°F, {target}-{target+1}°F brackets")
        else:
            st.info(f"Projection ABOVE forecast → **NO** on lower brackets, **YES** on {target}-{target+1}°F+")
    
    st.divider()
    st.subheader("PROJECTION DETAILS")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Pace", f"{projection['pace']}°F/hr")
    d2.metric("Hours to Peak", f"{projection['hours_remaining']}h")
    d3.metric("Est. Peak", f"{projection['peak_hour']}:00")
    d4.metric("Morning Low", f"{morning_low:.0f}°F")

else:
    # ========== LOW TEMPERATURE ==========
    st.header("❄️ LOW TEMPERATURE")
    
    projection = calculate_low_projection(weather, current_hour, weather.get("hourly_temps", []))
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 MARKET FORECAST")
        st.markdown(f"## {weather['forecast_low']:.0f}°F")
        st.caption("Open-Meteo (what Kalshi prices)")
    
    with col2:
        st.markdown("### 📍 OUR PROJECTION")
        st.markdown(f"## {projection['projected']:.1f}°F")
        st.caption(f"{projection['confidence']} confidence • {projection['method']}")
    
    gap = projection["projected"] - weather["forecast_low"]
    
    if abs(gap) >= 2:
        st.warning(f"⚡ **{abs(gap):.1f}°F GAP** — Edge opportunity!")
        target = int(weather["forecast_low"])
        if gap < 0:
            st.info(f"Projection BELOW forecast → **YES** on lower brackets, **NO** on {target}-{target+1}°F+")
        else:
            st.info(f"Projection ABOVE forecast → **NO** on {target-1}-{target}°F, {target}-{target+1}°F brackets")
    
    st.divider()
    
    if current_hour <= 9:
        st.info("🌅 **LOW WINDOW ACTIVE** — Low may still be forming")
    else:
        st.success("🔒 **LOW LOCKED** — Overnight minimum is set")

# ========== BRACKET SCANNER ==========
st.divider()
st.subheader("BRACKET SCANNER")

if market_type == "HIGH":
    proj_int = int(round(projection["projected"]))
    fcst_int = int(round(weather["forecast_high"]))
else:
    proj_int = int(round(projection["projected"]))
    fcst_int = int(round(weather["forecast_low"]))

center = (proj_int + fcst_int) // 2

cols = st.columns(11)
for i, offset in enumerate(range(-5, 6)):
    low = center + offset
    high = low + 1
    
    is_proj = proj_int == low or proj_int == high
    is_fcst = fcst_int == low or fcst_int == high
    
    with cols[i]:
        if is_proj and is_fcst:
            st.markdown(f"🎯 **{low}-{high}**")
            st.caption("BOTH")
        elif is_proj:
            st.markdown(f"📍 **{low}-{high}**")
            st.caption("PROJ")
        elif is_fcst:
            st.markdown(f"📊 **{low}-{high}**")
            st.caption("FCST")
        else:
            st.markdown(f"{low}-{high}")

st.caption("📍 = Our projection | 📊 = Market forecast | 🎯 = Both agree")

st.divider()

with st.expander("📖 HOW IT WORKS"):
    st.markdown("""
    **HIGH Temperature:**
    - Market Forecast = Open-Meteo predicted high
    - Our Projection = Current temp + (warming pace × hours to peak)
    - Adjusted for cloud cover (caps heating) and wind direction (advection)
    - Best window: 10:30 AM - 2:00 PM
    
    **LOW Temperature:**
    - Low occurs around sunrise (6-7 AM)
    - Before 9 AM: Low may still be forming
    - After 9 AM: Low is locked from overnight minimum
    - Check hourly data to find actual overnight low
    
    **Edge = When projection differs from forecast by 2°F+**
    """)

st.caption("v2.1 | High + Low Forecasting")
