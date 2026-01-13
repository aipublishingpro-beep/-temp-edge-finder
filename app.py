import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Temp Edge Finder", page_icon="🌡️", layout="wide")

# ========== SIDEBAR LEGEND ==========
with st.sidebar:
    st.header("📖 LEGEND")
    
    st.subheader("⚡ Edge Score")
    st.markdown("""
    🟢 **8-10** → STRONG — Size up  
    🟢 **6-7** → GOOD — Standard  
    🟡 **4-5** → LEAN — Small size  
    🔴 **0-3** → SKIP — No edge
    """)
    
    st.divider()
    
    st.subheader("Cushion Score (max +4)")
    st.markdown("""
    **≥ +3.0°F** → +4  
    **+2.0 to +2.9** → +3  
    **+1.0 to +1.9** → +2  
    **+0.5 to +0.9** → +1  
    **< +0.5** → 0
    """)
    
    st.divider()
    
    st.subheader("Pace Score (max +3)")
    st.markdown("""
    **≤ 0.3°F/hr** → +3 (slow)  
    **0.31–0.5** → +2  
    **0.51–0.8** → +1  
    **0.81–1.0** → 0  
    **> 1.0** → −1 (risky)
    """)
    
    st.divider()
    
    st.subheader("Time Window (max +2)")
    st.markdown("""
    **Before 10:30 AM** → +0 (noise)  
    **10:30–12:00** → +1 (forming)  
    **12:00–2:00 PM** → +2 (signal)  
    **After 2:00 PM** → −1 (late risk)
    """)
    
    st.divider()
    
    st.subheader("Weather Modifiers")
    st.markdown("""
    ☁️ **Heavy clouds (≥70%)** → +1  
    💨 **Wind ≥10 mph** → +1  
    ☀️ **Clear skies (<30%)** → −1  
    🌡️ **Heat advection (SW)** → −2  
    ❄️ **Cold advection (NW/N)** → +2
    """)
    
    st.divider()
    st.caption("v1.0 | Settlement: NWS Daily Climate Report")

# ========== CITY CONFIGS ==========
CITIES = {
    "NYC": {"lat": 40.7829, "lon": -73.9654, "name": "NYC (Central Park)", "tz": "America/New_York"},
    "Chicago": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago (O'Hare)", "tz": "America/Chicago"},
    "LA": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles", "tz": "America/Los_Angeles"},
    "Miami": {"lat": 25.7617, "lon": -80.1918, "name": "Miami", "tz": "America/New_York"},
    "Denver": {"lat": 39.7392, "lon": -104.9903, "name": "Denver", "tz": "America/Denver"},
}

def fetch_weather(city_key):
    """Fetch current weather from Open-Meteo API"""
    city = CITIES[city_key]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}&current=temperature_2m,cloud_cover,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone={city['tz']}"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        current = data.get("current", {})
        return {
            "temp": current.get("temperature_2m", 0),
            "cloud_cover": current.get("cloud_cover", 0),
            "wind_speed": current.get("wind_speed_10m", 0),
            "wind_direction": current.get("wind_direction_10m", 0),
            "time": current.get("time", ""),
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_wind_direction_name(degrees):
    """Convert wind degrees to direction name"""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(degrees / 45) % 8
    return directions[idx]

def calculate_cushion_score(cushion, side):
    """Calculate cushion score (max +4)"""
    if side == "NO":
        # For NO, positive cushion = good (projected below threshold)
        c = cushion
    else:
        # For YES, negative cushion = good (projected above threshold)
        c = -cushion
    
    if c >= 3.0:
        return 4
    elif c >= 2.0:
        return 3
    elif c >= 1.0:
        return 2
    elif c >= 0.5:
        return 1
    else:
        return 0

def calculate_pace_score(pace):
    """Calculate pace score based on warming rate (max +3)"""
    if pace <= 0.3:
        return 3
    elif pace <= 0.5:
        return 2
    elif pace <= 0.8:
        return 1
    elif pace <= 1.0:
        return 0
    else:
        return -1

def calculate_time_score(hour, minute):
    """Calculate time window score (max +2)"""
    time_decimal = hour + minute / 60
    
    if time_decimal < 10.5:
        return 0  # Before 10:30 AM - noise
    elif time_decimal < 12:
        return 1  # 10:30 - 12:00 - trend forming
    elif time_decimal < 14:
        return 2  # 12:00 - 2:00 PM - signal window
    else:
        return -1  # After 2:00 PM - late volatility risk

def calculate_weather_modifiers(cloud_cover, wind_speed, wind_direction):
    """Calculate weather context modifiers"""
    modifier = 0
    tags = []
    
    # Cloud cover
    if cloud_cover >= 70:
        modifier += 1
        tags.append("☁️ Heavy clouds +1")
    elif cloud_cover < 30:
        modifier -= 1
        tags.append("☀️ Clear skies -1")
    
    # Wind speed
    if wind_speed >= 10:
        modifier += 1
        tags.append("💨 Wind ≥10mph +1")
    
    # Wind direction (advection)
    direction = get_wind_direction_name(wind_direction)
    if direction in ["SW", "S"]:
        modifier -= 2
        tags.append("🌡️ Heat advection (SW/S) -2")
    elif direction in ["NW", "N", "NE"]:
        modifier += 2
        tags.append("❄️ Cold advection (NW/N) +2")
    
    return modifier, tags

# ========== MAIN APP ==========
now = datetime.now(pytz.timezone('America/New_York'))
st.title("🌡️ TEMPERATURE EDGE FINDER")
st.caption(f"Last update: {now.strftime('%I:%M:%S %p ET')} | Settlement: NWS Daily Climate Report")

# ========== CITY SELECTION ==========
col1, col2 = st.columns([1, 3])
with col1:
    selected_city = st.selectbox("City", list(CITIES.keys()), index=0)

# ========== FETCH WEATHER ==========
weather = fetch_weather(selected_city)

if weather["success"]:
    st.success(f"🟢 Live weather data for {CITIES[selected_city]['name']}")
    
    # Display current conditions
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Current Temp", f"{weather['temp']:.1f}°F")
    w2.metric("Cloud Cover", f"{weather['cloud_cover']}%")
    w3.metric("Wind Speed", f"{weather['wind_speed']:.1f} mph")
    w4.metric("Wind Direction", f"{weather['wind_direction']}° ({get_wind_direction_name(weather['wind_direction'])})")
else:
    st.error(f"❌ Failed to fetch weather: {weather.get('error', 'Unknown error')}")
    st.stop()

st.divider()

# ========== MANUAL INPUTS ==========
st.subheader("📊 PROJECTION INPUTS")

input_col1, input_col2, input_col3 = st.columns(3)

with input_col1:
    morning_baseline = st.number_input("Morning Baseline (°F)", 0.0, 100.0, 32.0, 1.0, 
                                        help="Lowest temp this morning")
with input_col2:
    projected_high = st.number_input("Projected High (°F)", 0.0, 120.0, weather['temp'] + 3.0, 0.5,
                                     help="Your projected max temp")
with input_col3:
    # Auto-select peak time based on cloud cover
    if weather['cloud_cover'] >= 70:
        default_peak = 1  # 2:00 PM for overcast
    elif weather['cloud_cover'] >= 40:
        default_peak = 2  # 3:00 PM for partly cloudy
    else:
        default_peak = 3  # 4:00 PM for clear
    
    peak_hour = st.selectbox("Expected Peak Time", 
                             ["1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"],
                             index=default_peak,
                             help="Auto-selected based on cloud cover. Clear=4PM, Cloudy=2PM")

# Calculate pace (warming rate per hour)
current_hour = now.hour + now.minute / 60
start_hour = 7  # Assume warming starts at 7 AM
hours_elapsed = max(current_hour - start_hour, 0.5)
temp_rise = weather['temp'] - morning_baseline
pace = temp_rise / hours_elapsed if hours_elapsed > 0 else 0

st.metric("Current Warming Pace", f"{pace:.2f}°F/hr", 
          delta="Slow" if pace < 0.5 else ("Normal" if pace < 1.0 else "Fast"))

st.divider()

# ========== KALSHI BRACKETS ==========
st.subheader("🎯 KALSHI BRACKET ANALYSIS")
st.caption("Enter the bracket thresholds from Kalshi")

bracket_col1, bracket_col2, bracket_col3 = st.columns(3)

with bracket_col1:
    bracket_low = st.number_input("Bracket Low (°F)", 0, 120, 41, 1)
with bracket_col2:
    bracket_high = st.number_input("Bracket High (°F)", 0, 120, 42, 1)
with bracket_col3:
    side = st.selectbox("Your Side", ["NO", "YES"])

bracket_mid = (bracket_low + bracket_high) / 2

# Calculate cushion
if side == "NO":
    cushion = bracket_low - projected_high  # Want projected BELOW bracket
else:
    cushion = projected_high - bracket_high  # Want projected ABOVE bracket

st.divider()

# ========== EDGE CALCULATION ==========
st.subheader("⚡ EDGE SCORE")

# Calculate all scores
cushion_score = calculate_cushion_score(bracket_low - projected_high, side)
pace_score = calculate_pace_score(pace)
time_score = calculate_time_score(now.hour, now.minute)
weather_modifier, weather_tags = calculate_weather_modifiers(
    weather['cloud_cover'], 
    weather['wind_speed'], 
    weather['wind_direction']
)

total_edge = cushion_score + pace_score + time_score + weather_modifier

# Display scores
score_cols = st.columns(5)
score_cols[0].metric("Cushion", f"+{cushion_score}" if cushion_score >= 0 else str(cushion_score))
score_cols[1].metric("Pace", f"+{pace_score}" if pace_score >= 0 else str(pace_score))
score_cols[2].metric("Time Window", f"+{time_score}" if time_score >= 0 else str(time_score))
score_cols[3].metric("Weather", f"+{weather_modifier}" if weather_modifier >= 0 else str(weather_modifier))
score_cols[4].metric("TOTAL", str(total_edge))

# Weather tags
if weather_tags:
    st.caption("Weather modifiers: " + " | ".join(weather_tags))

# Edge rating
if total_edge >= 8:
    edge_color = "#00ff00"
    edge_label = f"🟢 STRONG {side}"
elif total_edge >= 6:
    edge_color = "#00ff00"
    edge_label = f"🟢 GOOD {side}"
elif total_edge >= 4:
    edge_color = "#ffff00"
    edge_label = f"🟡 LEAN {side}"
else:
    edge_color = "#ff0000"
    edge_label = "🔴 SKIP"

st.markdown(f"## <span style='color:{edge_color}'>{total_edge} pts — {edge_label}</span>", unsafe_allow_html=True)

# Cushion display
st.markdown("---")
proj_col1, proj_col2, proj_col3 = st.columns(3)
proj_col1.metric("Projected High", f"{projected_high:.1f}°F")
proj_col2.metric("Bracket", f"{bracket_low}-{bracket_high}°F")
proj_col3.metric("Cushion", f"{cushion:+.1f}°F", 
                  delta="favorable" if cushion > 0 else "unfavorable",
                  delta_color="normal" if cushion > 0 else "inverse")

st.divider()

# ========== BRACKET SCANNER ==========
st.subheader("📋 QUICK BRACKET SCAN")
st.caption("See cushion across multiple brackets")

# Generate common brackets around current temp
base_temp = int(weather['temp'])
brackets = [(base_temp + i, base_temp + i + 1) for i in range(-3, 7)]

scan_cols = st.columns(len(brackets))
for i, (low, high) in enumerate(brackets):
    cushion_no = low - projected_high
    if cushion_no >= 2:
        color = "#00ff00"
    elif cushion_no >= 0.5:
        color = "#ffff00"
    elif cushion_no >= 0:
        color = "#ff8800"
    else:
        color = "#ff0000"
    
    scan_cols[i].markdown(f"**{low}-{high}°F**")
    scan_cols[i].markdown(f"<span style='color:{color}'>{cushion_no:+.1f}</span>", unsafe_allow_html=True)

st.divider()

# ========== HOW TO USE ==========
with st.expander("📚 HOW TO USE"):
    st.markdown("""
    ## Temperature Edge Trading
    
    **Settlement:** NWS Daily Climate Report (released next morning)
    
    ---
    
    ### Workflow
    
    1. **Check current temp** — Auto-fetched from Open-Meteo
    2. **Set morning baseline** — Lowest temp recorded this morning
    3. **Estimate projected high** — Based on current pace + conditions
    4. **Select Kalshi bracket** — The range you're considering
    5. **Check edge score** — 6+ is tradeable
    
    ---
    
    ### Key Signals
    
    **Good NO spots:**
    - Heavy cloud cover (≥70%)
    - Cold advection (NW/N wind)
    - Slow warming pace (<0.5°F/hr)
    - Temperature flattening midday
    
    **Good YES spots:**
    - Clear skies
    - Heat advection (SW/S wind)
    - Fast warming pace (>1.0°F/hr)
    - Morning sun burning off clouds
    
    ---
    
    ### Best Trading Window
    
    **10:30 AM - 2:00 PM** is the signal window. Before that is noise, after that is late risk.
    
    Peak temperature usually occurs **2-4 PM** depending on cloud cover.
    """)

st.caption("v1.0 | Temperature Edge Finder")
