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
    
    st.header("🟠 TRADE SIGNALS")
    st.markdown("""
    **Orange = Recommended Trade**
    
    🟠 **BUY YES** — Our model says temp lands here
    
    🟠 **BUY NO** — Our model says temp WON'T be here
    
    *Both can win if our forecast is right!*
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
    st.caption("v5.3 | Our Model vs Market")

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

# ========== FETCH TODAY'S HIGH/LOW FROM OBSERVATIONS ==========
def fetch_todays_actual_high_low(station):
    """Fetch today's actual recorded high and low from observations"""
    url = f"https://api.weather.gov/stations/{station}/observations?limit=50"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempEdge/5.0"}, timeout=10)
        if resp.status_code != 200:
            return None, None
        
        features = resp.json().get("features", [])
        
        # Get today's date in ET
        today_et = datetime.now(pytz.timezone('US/Eastern')).date()
        
        today_temps = []
        
        for feature in features:
            p = feature.get("properties", {})
            
            # Get observation time
            obs_time = p.get("timestamp", "")
            if not obs_time:
                continue
            
            try:
                obs_dt = datetime.fromisoformat(obs_time.replace('Z', '+00:00'))
                obs_date = obs_dt.astimezone(pytz.timezone('US/Eastern')).date()
                
                # Only include today's observations
                if obs_date != today_et:
                    continue
            except:
                continue
            
            # Get temperature
            temp_obj = p.get("temperature", {})
            temp_c = temp_obj.get("value") if isinstance(temp_obj, dict) else None
            
            if temp_c is None:
                continue
            
            temp_f = round(temp_c * 9/5 + 32, 1)
            
            # Skip clearly bad readings
            if temp_f < -20 or temp_f > 130:
                continue
            if temp_f == 32.0 and temp_c == 0:
                continue
            
            today_temps.append(temp_f)
        
        if today_temps:
            return max(today_temps), min(today_temps)
        
        return None, None
    except:
        return None, None
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
            
            # Get market ticker for URL
            ticker = m.get("ticker", "")
            event_ticker = m.get("event_ticker", "")
            
            # Build Kalshi URL - use the ticker directly
            # Format: https://kalshi.com/markets/kxlowtnyc/kxlowtnyc-26jan15-t27
            kalshi_url = f"https://kalshi.com/markets/{series_ticker.lower()}/{ticker.lower()}" if ticker else "#"
            
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
            brackets.append({
                "range": display, 
                "mid": mid, 
                "yes": yp,
                "ticker": ticker,
                "url": kalshi_url
            })
        
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
        
        # Check open-ended brackets first
        if "or above" in range_text or "above" in range_text:
            # Extract the threshold number
            threshold = mid - 0.5 if mid else 27
            if temp >= threshold:
                return b
        elif "or below" in range_text or "below" in range_text:
            threshold = mid + 0.5 if mid else 20
            if temp <= threshold:
                return b
        else:
            # Regular range bracket
            if abs(temp - mid) <= 1.5:
                return b
    
    # If no match found, find closest bracket
    closest = None
    min_dist = float('inf')
    for b in brackets:
        if b['mid']:
            dist = abs(temp - b['mid'])
            if dist < min_dist:
                min_dist = dist
                closest = b
    return closest

def get_trade_recommendations(brackets, our_temp, market_temp):
    """
    Get YES and NO trade recommendations based on our forecast vs market
    Returns: (yes_bracket, no_bracket, direction)
    """
    if not brackets or our_temp is None:
        return None, None, None
    
    # Always find YES bracket for our forecast
    yes_bracket = find_bracket_for_temp(brackets, our_temp)
    
    no_bracket = None
    direction = None
    
    # Only calculate edge direction if we have market temp
    if market_temp is not None:
        gap = our_temp - market_temp
        
        if gap >= 2:
            # Our model says HIGHER - buy NO on lower brackets
            direction = "HIGHER"
            # Find the lowest bracket (to fade)
            for b in brackets:
                if b['mid'] and b['mid'] < our_temp - 3:
                    if "below" in b['range'].lower():
                        no_bracket = b
                        break
            # If no "below" bracket, get lowest regular bracket
            if not no_bracket:
                for b in brackets:
                    if b['mid'] and b['mid'] < our_temp - 3:
                        no_bracket = b
                        break
                        
        elif gap <= -2:
            # Our model says LOWER - buy NO on higher brackets
            direction = "LOWER"
            # Find the highest bracket (to fade)
            for b in reversed(brackets):
                if b['mid'] and b['mid'] > our_temp + 3:
                    if "above" in b['range'].lower():
                        no_bracket = b
                        break
            # If no "above" bracket, get highest regular bracket
            if not no_bracket:
                for b in reversed(brackets):
                    if b['mid'] and b['mid'] > our_temp + 3:
                        no_bracket = b
                        break
    
    return yes_bracket, no_bracket, direction

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
st.caption(f"v5.4 — Our Model vs NWS vs Market | {now_et.strftime('%I:%M %p ET')}")

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
    
    # Fetch today's actual recorded high/low
    actual_high, actual_low = fetch_todays_actual_high_low(cfg['station'])
    
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
    
    # Show TODAY'S actual high/low recorded
    if actual_high or actual_low:
        c1, c2 = st.columns(2)
        with c1:
            if actual_high:
                st.metric("📈 Today's High (so far)", f"{actual_high}°F")
        with c2:
            if actual_low:
                st.metric("📉 Today's Low (so far)", f"{actual_low}°F")
    
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
high_locked = False
low_locked = False

# Get current hour
current_hour = datetime.now(pytz.timezone(cfg['tz'])).hour

# HIGH TEMP LOGIC
# If we have actual high and it's past peak hours (after 3 PM), use actual
if actual_high is not None:
    if current_hour >= 15:
        # Past peak - high is locked
        our_high = actual_high
        high_locked = True
    else:
        # Still heating - use max of actual so far or forecast
        forecast_high = calculate_our_forecast(obs, cfg['tz'], is_high=True) if obs and obs.get("temp") else None
        if forecast_high:
            our_high = max(actual_high, forecast_high)
        else:
            our_high = actual_high
elif obs and obs.get("temp") is not None:
    our_high = calculate_our_forecast(obs, cfg['tz'], is_high=True)

# LOW TEMP LOGIC
# Low usually occurs around sunrise (5-7 AM) or before midnight
if actual_low is not None:
    if 7 <= current_hour <= 18:
        # Daytime - low may have already occurred this morning
        # But could drop more before midnight, so use forecast
        forecast_low = calculate_our_forecast(obs, cfg['tz'], is_high=False) if obs and obs.get("temp") else None
        if forecast_low:
            our_low = min(actual_low, forecast_low)
        else:
            our_low = actual_low
    else:
        # Evening/night - low still developing
        forecast_low = calculate_our_forecast(obs, cfg['tz'], is_high=False) if obs and obs.get("temp") else None
        if forecast_low:
            our_low = min(actual_low, forecast_low)
        else:
            our_low = actual_low
elif obs and obs.get("temp") is not None:
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
        label = "🎯 ACTUAL HIGH" if high_locked else "🎯 OUR MODEL"
        st.metric(label, f"{our_high}°F" if our_high else "—")
    with c2:
        st.metric("NWS Forecast", f"{nws_high}°F" if nws_high else "—")
    with c3:
        st.metric("Market Implied", f"{market_high}°F" if market_high else "—")
    
    # Show if high is locked
    if high_locked:
        st.success(f"✅ **HIGH LOCKED: {our_high}°F** — Already recorded today")
    elif actual_high:
        st.info(f"📊 Today's high so far: {actual_high}°F (could go higher)")
    
    # Edge display
    display_edge(our_high, nws_high, market_high, "HIGH")
    
    # Get trade recommendations
    yes_bracket, no_bracket, direction = get_trade_recommendations(high_brackets, our_high, market_high)
    
    # Show YES recommendation
    if yes_bracket:
        yes_url = yes_bracket.get('url', '#')
        st.markdown(f"""
        <div style="background-color: #FF8C00; padding: 10px; border-radius: 6px; margin: 5px 0;">
            <span style="color: white; font-weight: bold;">🟠 BUY YES: {yes_bracket['range']}</span><br>
            <span style="color: white;">YES @ {yes_bracket['yes']:.0f}¢ | Potential return: {100 - yes_bracket['yes']:.0f}¢</span><br>
            <a href="{yes_url}" target="_blank" style="color: #90EE90; font-weight: bold; text-decoration: underline;">→ BUY ON KALSHI</a>
        </div>""", unsafe_allow_html=True)
    
    if no_bracket:
        no_price = 100 - no_bracket['yes']
        no_url = no_bracket.get('url', '#')
        st.markdown(f"""
        <div style="background-color: #FF8C00; padding: 10px; border-radius: 6px; margin: 5px 0;">
            <span style="color: white; font-weight: bold;">🟠 BUY NO: {no_bracket['range']}</span><br>
            <span style="color: white;">NO @ {no_price:.0f}¢ | Potential return: {no_bracket['yes']:.0f}¢</span><br>
            <a href="{no_url}" target="_blank" style="color: #90EE90; font-weight: bold; text-decoration: underline;">→ BUY ON KALSHI</a>
        </div>""", unsafe_allow_html=True)
    
    # All brackets
    if high_brackets:
        with st.expander("View All Brackets"):
            for b in high_brackets:
                is_yes = yes_bracket and b['range'] == yes_bracket['range']
                is_no = no_bracket and b['range'] == no_bracket['range']
                bracket_url = b.get('url', '#')
                
                if is_yes:
                    st.markdown(f"""
                    <div style="background-color: #FF8C00; padding: 6px; border-radius: 4px; margin: 2px 0;">
                        <span style="color: white;">🟠 YES → {b['range']} — YES {b['yes']:.0f}¢ | NO {100-b['yes']:.0f}¢</span>
                        <a href="{bracket_url}" target="_blank" style="color: #90EE90; margin-left: 10px; text-decoration: underline;">BUY</a>
                    </div>""", unsafe_allow_html=True)
                elif is_no:
                    st.markdown(f"""
                    <div style="background-color: #FF8C00; padding: 6px; border-radius: 4px; margin: 2px 0;">
                        <span style="color: white;">🟠 NO → {b['range']} — YES {b['yes']:.0f}¢ | NO {100-b['yes']:.0f}¢</span>
                        <a href="{bracket_url}" target="_blank" style="color: #90EE90; margin-left: 10px; text-decoration: underline;">BUY</a>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f'{b["range"]} — YES {b["yes"]:.0f}¢ | NO {100-b["yes"]:.0f}¢ <a href="{bracket_url}" target="_blank" style="color: #4CAF50;">BUY</a>', unsafe_allow_html=True)
    else:
        st.error("No high temp brackets available")

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
    
    # Show actual low so far
    if actual_low:
        st.info(f"📊 Today's low so far: {actual_low}°F — could drop more by midnight")
    
    # Edge display
    display_edge(our_low, nws_low, market_low, "LOW")
    
    # Get trade recommendations for LOW
    low_yes_bracket, low_no_bracket, low_direction = get_trade_recommendations(low_brackets, our_low, market_low)
    
    # Show YES recommendation with link
    if low_yes_bracket:
        low_yes_url = low_yes_bracket.get('url', '#')
        st.markdown(
            f'<div style="background-color: #FF8C00; padding: 10px; border-radius: 6px; margin: 5px 0;">'
            f'<span style="color: white; font-weight: bold;">🟠 BUY YES: {low_yes_bracket["range"]}</span><br>'
            f'<span style="color: white;">YES @ {low_yes_bracket["yes"]:.0f}¢ | Potential return: {100 - low_yes_bracket["yes"]:.0f}¢</span><br>'
            f'<a href="{low_yes_url}" target="_blank" style="color: #90EE90; font-weight: bold; text-decoration: underline;">→ BUY ON KALSHI</a>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    # Show NO recommendation with link
    if low_no_bracket:
        low_no_price = 100 - low_no_bracket['yes']
        low_no_url = low_no_bracket.get('url', '#')
        st.markdown(
            f'<div style="background-color: #FF8C00; padding: 10px; border-radius: 6px; margin: 5px 0;">'
            f'<span style="color: white; font-weight: bold;">🟠 BUY NO: {low_no_bracket["range"]}</span><br>'
            f'<span style="color: white;">NO @ {low_no_price:.0f}¢ | Potential return: {low_no_bracket["yes"]:.0f}¢</span><br>'
            f'<a href="{low_no_url}" target="_blank" style="color: #90EE90; font-weight: bold; text-decoration: underline;">→ BUY ON KALSHI</a>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    # All brackets with highlighting and links
    if low_brackets:
        with st.expander("View All Brackets"):
            for b in low_brackets:
                is_yes_rec = low_yes_bracket and b['range'] == low_yes_bracket['range']
                is_no_rec = low_no_bracket and b['range'] == low_no_bracket['range']
                b_url = b.get('url', '#')
                
                if is_yes_rec:
                    st.markdown(
                        f'<div style="background-color: #FF8C00; padding: 6px; border-radius: 4px; margin: 2px 0;">'
                        f'<span style="color: white;">🟠 YES → {b["range"]} — YES {b["yes"]:.0f}¢ | NO {100-b["yes"]:.0f}¢</span> '
                        f'<a href="{b_url}" target="_blank" style="color: #90EE90; text-decoration: underline;">BUY</a>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                elif is_no_rec:
                    st.markdown(
                        f'<div style="background-color: #FF8C00; padding: 6px; border-radius: 4px; margin: 2px 0;">'
                        f'<span style="color: white;">🟠 NO → {b["range"]} — YES {b["yes"]:.0f}¢ | NO {100-b["yes"]:.0f}¢</span> '
                        f'<a href="{b_url}" target="_blank" style="color: #90EE90; text-decoration: underline;">BUY</a>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'{b["range"]} — YES {b["yes"]:.0f}¢ | NO {100-b["yes"]:.0f}¢ '
                        f'<a href="{b_url}" target="_blank" style="color: #4CAF50;">BUY</a>',
                        unsafe_allow_html=True
                    )
    else:
        st.error("No low temp brackets available")

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
    
    **🟠 Orange Trade Signals:**
    - **BUY YES** on bracket where our model says temp will land
    - **BUY NO** on bracket in opposite direction (hedge/confirmation)
    - Both trades win if our forecast is correct!
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
