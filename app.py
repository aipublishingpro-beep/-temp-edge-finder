import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz
import re
import math

st.set_page_config(page_title="Temp Edge Finder", page_icon="🌡️", layout="wide")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("🎯 EDGE COLORS")
    st.markdown("""
    🟢 **GREEN** — Our model ≥2° different
    → Edge exists, bet our direction
    
    🟡 **YELLOW** — 1-2° difference
    → Small edge, proceed with caution
    
    ⚪ **GRAY** — Within ±1°
    → No edge, skip
    """)
    
    st.divider()
    
    st.header("📊 OUR MODEL INPUTS")
    st.markdown("""
    - Current temp
    - Dew point (LOW floor)
    - Cloud cover %
    - Wind speed
    - Hours to peak/sunrise
    - Seasonal patterns
    """)
    
    st.divider()
    st.caption("v5.0 | Our Model vs Market")

# ========== CITIES (with exact settlement stations) ==========
CITIES = {
    "NYC": {
        "name": "New York (Central Park)", 
        "tz": "America/New_York",
        "high_ticker": "KXHIGHNY", 
        "low_ticker": "KXLOWTNYC", 
        "station": "KNYC",  # Central Park - EXACT settlement station
        "nws_office": "OKX", 
        "grid_x": 33, 
        "grid_y": 37,
        "lat": 40.78,
        "lon": -73.97
    },
    "Chicago": {
        "name": "Chicago (O'Hare)", 
        "tz": "America/Chicago",
        "high_ticker": "KXHIGHCHI", 
        "low_ticker": "KXLOWTCHI", 
        "station": "KORD",
        "nws_office": "LOT", 
        "grid_x": 65, 
        "grid_y": 76,
        "lat": 41.98,
        "lon": -87.90
    },
    "LA": {
        "name": "Los Angeles (LAX)", 
        "tz": "America/Los_Angeles",
        "high_ticker": "KXHIGHLA", 
        "low_ticker": "KXLOWTLAX", 
        "station": "KLAX",
        "nws_office": "LOX", 
        "grid_x": 149, 
        "grid_y": 48,
        "lat": 33.94,
        "lon": -118.41
    },
    "Miami": {
        "name": "Miami", 
        "tz": "America/New_York",
        "high_ticker": "KXHIGHMIA", 
        "low_ticker": "KXLOWTMIA", 
        "station": "KMIA",
        "nws_office": "MFL", 
        "grid_x": 109, 
        "grid_y": 50,
        "lat": 25.79,
        "lon": -80.29
    },
    "Denver": {
        "name": "Denver", 
        "tz": "America/Denver",
        "high_ticker": "KXHIGHDEN", 
        "low_ticker": "KXLOWTDEN", 
        "station": "KDEN",
        "nws_office": "BOU", 
        "grid_x": 62, 
        "grid_y": 60,
        "lat": 39.85,
        "lon": -104.65
    },
}

# ========== FETCH CURRENT OBSERVATIONS ==========
def fetch_station_observations(station):
    """Fetch recent observations and find most recent VALID reading"""
    # Fetch last 24 hours of observations instead of just "latest"
    url = f"https://api.weather.gov/stations/{station}/observations?limit=24"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempEdge/5.0 (contact@example.com)"}, timeout=10)
        
        if resp.status_code != 200:
            return None
        
        features = resp.json().get("features", [])
        
        # Find most recent observation with valid temperature
        for feature in features:
            p = feature.get("properties", {})
            
            # Temperature (C to F)
            temp_obj = p.get("temperature", {})
            temp_c = temp_obj.get("value") if isinstance(temp_obj, dict) else None
            
            # Skip if no valid temperature or temp is clearly wrong (< -50 or exactly 0 when it shouldn't be)
            if temp_c is None:
                continue
            
            temp_f = round(temp_c * 9/5 + 32, 1)
            
            # Skip clearly bad readings (0°F exactly is suspicious unless it's actually that cold)
            # We check if it's exactly 32°F (0°C) which might be a default/error value
            if temp_f == 32.0 and temp_c == 0:
                # Could be real or could be error - check dew point too
                dew_obj = p.get("dewpoint", {})
                dew_c = dew_obj.get("value") if isinstance(dew_obj, dict) else None
                if dew_c is None or dew_c == 0:
                    continue  # Likely bad data
            
            # Dew Point (C to F)
            dew_obj = p.get("dewpoint", {})
            dew_c = dew_obj.get("value") if isinstance(dew_obj, dict) else None
            dew_f = round(dew_c * 9/5 + 32, 1) if dew_c is not None else None
            
            # Wind Speed
            wind_obj = p.get("windSpeed", {})
            wind_val = wind_obj.get("value") if isinstance(wind_obj, dict) else None
            wind_unit = wind_obj.get("unitCode", "") if isinstance(wind_obj, dict) else ""
            if wind_val is not None:
                if "km" in wind_unit.lower():
                    wind_mph = round(wind_val * 0.621371, 1)
                else:
                    wind_mph = round(wind_val * 2.237, 1)
            else:
                wind_mph = 0
            
            # Cloud cover
            cloud_text = p.get("textDescription", "") or ""
            cloud_lower = cloud_text.lower()
            if "clear" in cloud_lower or "sunny" in cloud_lower or "fair" in cloud_lower:
                cloud_pct = 0
            elif "few" in cloud_lower:
                cloud_pct = 15
            elif "scattered" in cloud_lower or "partly" in cloud_lower:
                cloud_pct = 40
            elif "broken" in cloud_lower or "mostly cloudy" in cloud_lower:
                cloud_pct = 70
            elif "overcast" in cloud_lower or "cloudy" in cloud_lower:
                cloud_pct = 95
            else:
                cloud_pct = 50
            
            # Observation time
            obs_time = p.get("timestamp", "")
            
            # Calculate how old this observation is
            obs_age_mins = None
            if obs_time:
                try:
                    obs_dt = datetime.fromisoformat(obs_time.replace('Z', '+00:00'))
                    now_utc = datetime.now(pytz.UTC)
                    obs_age_mins = (now_utc - obs_dt).total_seconds() / 60
                except:
                    pass
            
            return {
                "temp": temp_f,
                "dew_point": dew_f,
                "wind": wind_mph,
                "cloud_pct": cloud_pct,
                "cloud_text": cloud_text,
                "obs_time": obs_time,
                "obs_age_mins": obs_age_mins
            }
        
        return None
    except Exception as e:
        return None

def fetch_station_observations_backup(lat, lon):
    """Backup: fetch from nearest station using lat/lon"""
    try:
        # Get nearest stations
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        resp = requests.get(points_url, headers={"User-Agent": "TempEdge/5.0"}, timeout=10)
        if resp.status_code == 200:
            obs_url = resp.json().get("properties", {}).get("observationStations")
            if obs_url:
                stations_resp = requests.get(obs_url, headers={"User-Agent": "TempEdge/5.0"}, timeout=10)
                if stations_resp.status_code == 200:
                    stations = stations_resp.json().get("features", [])
                    if stations:
                        # Get first station's latest observation
                        station_id = stations[0].get("properties", {}).get("stationIdentifier")
                        if station_id:
                            return fetch_station_observations(station_id), station_id
    except:
        pass
    return None, None

# ========== FETCH NWS FORECAST ==========
def fetch_nws_forecast(office, grid_x, grid_y):
    """Fetch NWS official forecast"""
    url = f"https://api.weather.gov/gridpoints/{office}/{grid_x},{grid_y}/forecast"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempEdge/5.0"}, timeout=10)
        if resp.status_code == 200:
            periods = resp.json().get("properties", {}).get("periods", [])
            if periods:
                today_high = None
                today_low = None
                
                for period in periods[:4]:
                    temp = period.get("temperature")
                    is_day = period.get("isDaytime", True)
                    
                    if is_day and today_high is None:
                        today_high = temp
                    elif not is_day and today_low is None:
                        today_low = temp
                
                return {"high": today_high, "low": today_low}
    except:
        pass
    return {"high": None, "low": None}

# ========== OUR FORECASTING MODEL ==========
def calculate_our_forecast(obs, tz_name, is_high=True):
    """
    Our forecasting model using real-time station data
    
    HIGH TEMP MODEL:
    - Base: Current temp
    - Add: Solar heating potential (based on clouds, time to peak)
    - Adjust: Wind mixing effect
    
    LOW TEMP MODEL:
    - Floor: Dew point (temp rarely drops below this)
    - Base: Current temp or projected evening temp
    - Subtract: Radiative cooling (based on clouds, wind)
    """
    if obs is None or obs.get("temp") is None:
        return None
    
    current_temp = obs["temp"]
    dew_point = obs.get("dew_point") or (current_temp - 15)  # Estimate if missing
    cloud_pct = obs.get("cloud_pct", 50)
    wind = obs.get("wind", 5)
    
    # Get current hour in local timezone
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    hour = now.hour
    
    if is_high:
        # ===== HIGH TEMP MODEL =====
        # Peak heating typically 2-4 PM (14-16)
        peak_hour = 15
        hours_to_peak = max(0, peak_hour - hour)
        
        if hour >= peak_hour:
            # Past peak - high is likely current or slightly higher
            heating_potential = max(0, 2 - (hour - peak_hour))
        else:
            # Before peak - calculate heating potential
            # Clear sky: ~3-5°F per hour before noon, ~1-2°F per hour after
            if hour < 12:
                base_heating_rate = 3.5  # °F per hour morning
            else:
                base_heating_rate = 1.5  # °F per hour afternoon
            
            # Cloud adjustment (clouds block solar heating)
            cloud_factor = 1 - (cloud_pct / 100) * 0.7
            
            # Wind adjustment (wind mixes air, reduces surface heating)
            wind_factor = 1 - min(0.3, wind / 30)
            
            heating_potential = hours_to_peak * base_heating_rate * cloud_factor * wind_factor
        
        # January seasonal cap (sun angle limits heating)
        month = now.month
        if month in [12, 1, 2]:
            heating_potential = min(heating_potential, 12)  # Winter cap
        elif month in [6, 7, 8]:
            heating_potential = min(heating_potential, 20)  # Summer cap
        else:
            heating_potential = min(heating_potential, 15)  # Spring/Fall cap
        
        forecast_high = current_temp + heating_potential
        return round(forecast_high, 0)
    
    else:
        # ===== LOW TEMP MODEL =====
        # Key insight: Temp rarely drops below dew point
        
        # Hours until sunrise (approx 7 AM)
        if hour >= 19:  # Evening
            hours_of_cooling = (24 - hour) + 7
        elif hour < 7:  # Pre-dawn
            hours_of_cooling = 7 - hour
        else:  # Daytime - low may have already occurred
            hours_of_cooling = 0
        
        # Base cooling rate (clear, calm night)
        base_cooling_rate = 2.0  # °F per hour
        
        # Cloud adjustment (clouds TRAP heat, reduce cooling)
        cloud_factor = 1 - (cloud_pct / 100) * 0.8
        
        # Wind adjustment (wind PREVENTS radiative cooling)
        wind_factor = 1 - min(0.5, wind / 20)
        
        cooling_potential = hours_of_cooling * base_cooling_rate * cloud_factor * wind_factor
        
        # Calculate projected low
        projected_low = current_temp - cooling_potential
        
        # DEW POINT FLOOR - temp rarely drops more than 2-3° below dew point
        dew_floor = dew_point - 2
        
        # Low is the HIGHER of: projected cooling OR dew point floor
        forecast_low = max(projected_low, dew_floor)
        
        # If it's already morning, low may have occurred
        if 5 <= hour <= 9:
            # Low likely within 2-3° of current temp
            forecast_low = min(forecast_low, current_temp + 2)
        
        return round(forecast_low, 0)

# ========== FETCH KALSHI BRACKETS ==========
def fetch_kalshi_brackets(series_ticker):
    url = f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series_ticker}&status=open"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        markets = resp.json().get("markets", [])
        if not markets:
            return None
        
        today = datetime.now(pytz.timezone('US/Eastern'))
        today_str = today.strftime('%y%b%d').upper()
        
        today_markets = [m for m in markets if today_str in m.get("event_ticker", "").upper()]
        if not today_markets:
            first_event = markets[0].get("event_ticker", "")
            today_markets = [m for m in markets if m.get("event_ticker") == first_event]
        
        brackets = []
        for m in today_markets:
            txt = m.get("subtitle", "") or m.get("title", "")
            mid = None
            display = txt
            tl = txt.lower()
            
            if " to " in tl and "below" not in tl and "above" not in tl:
                try:
                    p = txt.replace('°','').lower().split('to')
                    low = int(''.join(filter(str.isdigit, p[0])))
                    high = int(''.join(filter(str.isdigit, p[1])))
                    mid = (low + high) / 2
                    display = f"{low}° to {high}°"
                except: mid = 45
            elif "below" in tl or "<" in txt:
                try: 
                    num = int(''.join(filter(str.isdigit, txt.split('°')[0].split('<')[-1])))
                    if "<" in txt:
                        mid = num - 1
                        display = f"{num - 1}° or below"
                    else:
                        mid = num
                        display = f"{num}° or below"
                except: mid = 30
            elif "above" in tl or ">" in txt:
                try: 
                    num = int(''.join(filter(str.isdigit, txt.split('°')[0].split('>')[-1])))
                    if ">" in txt:
                        mid = num + 1
                        display = f"{num + 1}° or above"
                    else:
                        mid = num
                        display = f"{num}° or above"
                except: mid = 60
            elif "-" in txt and "°" in txt:
                try:
                    match = re.search(r'(\d+)-(\d+)°', txt)
                    if match:
                        low, high = int(match.group(1)), int(match.group(2))
                        mid = (low + high) / 2
                        display = f"{low}° to {high}°"
                except: mid = 45
            
            yb, ya = m.get("yes_bid", 0), m.get("yes_ask", 0)
            yp = (yb + ya) / 2 if yb and ya else ya or yb or 0
            brackets.append({"range": display, "mid": mid, "yes": yp})
        
        brackets.sort(key=lambda x: x['mid'] or 0)
        return brackets
    except:
        return None

def calc_market_forecast(brackets):
    if not brackets:
        return None
    weighted_sum = 0
    total_prob = 0
    for b in brackets:
        prob = b['yes'] / 100
        mid = b['mid']
        if mid is None or prob <= 0:
            continue
        range_text = b['range'].lower()
        if "or above" in range_text:
            adjusted_mid = mid + 2.5
        elif "or below" in range_text:
            adjusted_mid = mid - 2.5
        else:
            adjusted_mid = mid
        weighted_sum += prob * adjusted_mid
        total_prob += prob
    if total_prob > 0:
        return round(weighted_sum / total_prob, 1)
    return None

def find_bracket_for_temp(brackets, temp):
    """Find which bracket a temperature falls into"""
    if not brackets or temp is None:
        return None
    for b in brackets:
        mid = b['mid']
        if mid is None:
            continue
        range_text = b['range'].lower()
        if "or above" in range_text:
            if temp >= mid - 0.5:
                return b
        elif "or below" in range_text:
            if temp <= mid + 0.5:
                return b
        else:
            if abs(temp - mid) <= 1.0:
                return b
    return None

# ========== DISPLAY EDGE BOX ==========
def display_edge(our_forecast, nws_forecast, market_forecast, label):
    """Display edge comparison with color coding"""
    if our_forecast is None:
        st.warning(f"Cannot calculate {label} forecast")
        return
    
    # Calculate edges
    vs_nws = our_forecast - nws_forecast if nws_forecast else None
    vs_market = our_forecast - market_forecast if market_forecast else None
    
    # Determine edge magnitude (use vs market as primary)
    edge = vs_market if vs_market is not None else vs_nws
    
    if edge is None:
        color = "#383d41"
        text_color = "#e2e3e5"
        icon = "⚪"
        edge_text = "NO DATA"
        action = "Cannot compare"
    elif abs(edge) >= 2:
        color = "#155724"
        text_color = "#d4edda"
        icon = "🟢"
        direction = "HIGHER" if edge > 0 else "LOWER"
        edge_text = f"{edge:+.0f}° EDGE"
        action = f"Our model says {direction} → BUY {direction} BRACKETS"
    elif abs(edge) >= 1:
        color = "#856404"
        text_color = "#fff3cd"
        icon = "🟡"
        direction = "HIGHER" if edge > 0 else "LOWER"
        edge_text = f"{edge:+.0f}° SMALL EDGE"
        action = f"Slight {direction.lower()} lean, proceed with caution"
    else:
        color = "#383d41"
        text_color = "#e2e3e5"
        icon = "⚪"
        edge_text = f"{edge:+.0f}° NO EDGE"
        action = "Market is fairly priced"
    
    st.markdown(f"""
    <div style="background-color: {color}; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <span style="color: {text_color}; font-size: 24px; font-weight: bold;">{icon} {edge_text}</span><br>
        <span style="color: {text_color};">{action}</span>
    </div>""", unsafe_allow_html=True)

# ========== MAIN ==========
now_et = datetime.now(pytz.timezone('US/Eastern'))
hour = now_et.hour

st.title("🌡️ TEMP EDGE FINDER")
st.caption(f"v5.0 — Our Model vs NWS vs Market | {now_et.strftime('%I:%M %p ET')}")

# Timing indicator
if 6 <= hour < 8:
    st.warning("⏳ **6-8 AM** — Early. LOW may be locked, HIGH still developing.")
elif 8 <= hour < 10:
    st.success("🎯 **8-10 AM** — BEST TIME. LOW confirmed, HIGH heating underway.")
elif 10 <= hour < 14:
    st.info("📈 **10 AM-2 PM** — Good for HIGH temp bets. Track heating.")
else:
    st.error("⚠️ **After 2 PM** — Late for HIGH. LOW markets open for tomorrow.")

st.divider()

# City selection
city = st.selectbox("City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
cfg = CITIES[city]

# Fetch all data
used_station = cfg['station']
obs = None

with st.spinner("Fetching station data..."):
    obs = fetch_station_observations(cfg['station'])
    
    # If primary station fails, try backup via lat/lon
    if obs is None or obs.get("temp") is None:
        backup_obs, backup_station = fetch_station_observations_backup(cfg['lat'], cfg['lon'])
        if backup_obs and backup_obs.get("temp") is not None:
            obs = backup_obs
            used_station = backup_station
    
    nws_forecast = fetch_nws_forecast(cfg['nws_office'], cfg['grid_x'], cfg['grid_y'])
    high_brackets = fetch_kalshi_brackets(cfg['high_ticker'])
    low_brackets = fetch_kalshi_brackets(cfg['low_ticker'])

# ========== CURRENT CONDITIONS ==========
st.subheader(f"📡 LIVE: {used_station} Station")

if obs and obs.get("temp") is not None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Current Temp", f"{obs['temp']}°F")
    with c2:
        st.metric("Dew Point", f"{obs['dew_point']}°F" if obs.get('dew_point') else "—")
    with c3:
        st.metric("Wind", f"{obs['wind']} mph")
    with c4:
        st.metric("Clouds", f"{obs['cloud_pct']}%", help=obs.get('cloud_text', ''))
    
    # Show observation age warning
    obs_age = obs.get('obs_age_mins')
    if obs_age:
        if obs_age > 120:
            st.warning(f"⚠️ Data is {obs_age:.0f} minutes old ({obs_age/60:.1f} hrs). Station may be offline.")
        elif obs_age > 60:
            st.caption(f"⏱️ Observation from {obs_age:.0f} minutes ago")
        else:
            st.caption(f"✅ Fresh data ({obs_age:.0f} mins old)")
    
    # Show station used if different from primary
    if used_station != cfg['station']:
        st.caption(f"⚠️ Using backup station {used_station} (primary {cfg['station']} unavailable)")
    
    # Dew point insight for LOW
    if obs.get('dew_point'):
        spread = obs['temp'] - obs['dew_point']
        if spread < 5:
            st.info(f"💧 **Dew Point Spread: {spread:.0f}°F** — Humid. LOW floor is ~{obs['dew_point']-2:.0f}°F")
        else:
            st.info(f"💧 **Dew Point Spread: {spread:.0f}°F** — Dry. More cooling potential tonight.")
else:
    st.error(f"❌ Cannot fetch station data from {cfg['station']}")
    st.caption("Try refreshing. NWS API may be temporarily unavailable.")

st.divider()

# Calculate our forecasts
our_high = None
our_low = None
if obs and obs.get("temp") is not None:
    our_high = calculate_our_forecast(obs, cfg['tz'], is_high=True)
    our_low = calculate_our_forecast(obs, cfg['tz'], is_high=False)

market_high = calc_market_forecast(high_brackets)
market_low = calc_market_forecast(low_brackets)
nws_high = nws_forecast.get("high")
nws_low = nws_forecast.get("low")

# ========== TWO COLUMN LAYOUT ==========
col_high, col_low = st.columns(2)

# ========== HIGH TEMP ==========
with col_high:
    st.subheader("🔥 HIGH TEMP")
    
    # Three forecasts comparison
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🎯 OUR MODEL", f"{our_high}°F" if our_high else "—")
    with c2:
        st.metric("NWS Forecast", f"{nws_high}°F" if nws_high else "—")
    with c3:
        st.metric("Market Implied", f"{market_high}°F" if market_high else "—")
    
    # Edge display
    display_edge(our_high, nws_high, market_high, "HIGH")
    
    # Recommended bracket
    if our_high and high_brackets:
        our_bracket = find_bracket_for_temp(high_brackets, our_high)
        if our_bracket:
            st.markdown(f"**🎯 BUY:** {our_bracket['range']} @ {our_bracket['yes']:.0f}¢")
    
    # All brackets
    if high_brackets:
        with st.expander("View All Brackets"):
            for b in high_brackets:
                highlight = our_high and b['mid'] and abs(our_high - b['mid']) <= 1.5
                if highlight:
                    st.markdown(f"**→ {b['range']}** — YES {b['yes']:.0f}¢")
                else:
                    st.write(f"{b['range']} — YES {b['yes']:.0f}¢")

# ========== LOW TEMP ==========
with col_low:
    st.subheader("❄️ LOW TEMP")
    
    # Three forecasts comparison
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🎯 OUR MODEL", f"{our_low}°F" if our_low else "—")
    with c2:
        st.metric("NWS Forecast", f"{nws_low}°F" if nws_low else "—")
    with c3:
        st.metric("Market Implied", f"{market_low}°F" if market_low else "—")
    
    # Edge display
    display_edge(our_low, nws_low, market_low, "LOW")
    
    # Recommended bracket
    if our_low and low_brackets:
        our_bracket = find_bracket_for_temp(low_brackets, our_low)
        if our_bracket:
            st.markdown(f"**🎯 BUY:** {our_bracket['range']} @ {our_bracket['yes']:.0f}¢")
    
    # All brackets
    if low_brackets:
        with st.expander("View All Brackets"):
            for b in low_brackets:
                highlight = our_low and b['mid'] and abs(our_low - b['mid']) <= 1.5
                if highlight:
                    st.markdown(f"**→ {b['range']}** — YES {b['yes']:.0f}¢")
                else:
                    st.write(f"{b['range']} — YES {b['yes']:.0f}¢")

st.divider()

# ========== MODEL EXPLANATION ==========
with st.expander("📊 How Our Model Works"):
    st.markdown("""
    **HIGH TEMP MODEL:**
    ```
    Forecast = Current Temp + Heating Potential
    
    Heating Potential = Hours to Peak × Base Rate × Cloud Factor × Wind Factor
    - Clear skies = more heating
    - Light wind = more heating
    - Winter cap: +12°F max
    ```
    
    **LOW TEMP MODEL:**
    ```
    Forecast = MAX(Projected Cooling, Dew Point Floor)
    
    - Dew Point sets the FLOOR (temp rarely drops below)
    - Clear skies = more cooling
    - Light wind = more cooling
    - Cloudy/windy = stays warmer
    ```
    
    **Edge Detection:**
    - 🟢 ≥2° difference = Strong edge
    - 🟡 1-2° difference = Small edge
    - ⚪ <1° difference = No edge
    """)

# ========== SETTLEMENT RULES REMINDER ==========
with st.expander("📋 Kalshi Settlement Rules"):
    st.markdown("""
    - **Source:** NWS official station (first non-preliminary report)
    - **Precision:** Full precision, no rounding
    - **Expiration:** 10:00 AM ET next day
    - **Revisions:** Post-expiration revisions don't count
    """)

# ========== DEBUG INFO ==========
with st.expander("🔧 Debug Info"):
    st.write(f"**Primary Station:** {cfg['station']}")
    st.write(f"**Station Used:** {used_station}")
    st.write(f"**Obs Data Received:** {obs is not None}")
    if obs:
        st.write(f"**Temp:** {obs.get('temp')}°F")
        st.write(f"**Dew Point:** {obs.get('dew_point')}°F")
        st.write(f"**Cloud Text:** {obs.get('cloud_text')}")
        st.write(f"**Obs Time:** {obs.get('obs_time')}")
        st.write(f"**Obs Age:** {obs.get('obs_age_mins', 'unknown')} mins")
    st.write(f"**NWS Forecast:** High={nws_high}, Low={nws_low}")
    st.write(f"**Our Model:** High={our_high}, Low={our_low}")
    st.write(f"**Market Implied:** High={market_high}, Low={market_low}")

st.caption("⚠️ Not financial advice. Model is experimental.")
