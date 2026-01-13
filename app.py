import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="Temp Edge Finder", page_icon="🌡️", layout="wide")

if "temp_positions" not in st.session_state:
    st.session_state.temp_positions = []

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
    st.caption("v1.1 | Settlement: NWS Daily Climate Report")

# ========== CITY CONFIGS ==========
CITIES = {
    "NYC": {
        "name": "New York (Central Park)",
        "lat": 40.7829,
        "lon": -73.9654,
        "tz": "America/New_York",
        "series_ticker": "KXHIGHNY",
        "nws_station": "KNYC"
    },
    "Chicago": {
        "name": "Chicago (O'Hare)",
        "lat": 41.9742,
        "lon": -87.9073,
        "tz": "America/Chicago",
        "series_ticker": "KXHIGHCHI",
        "nws_station": "KORD"
    },
    "LA": {
        "name": "Los Angeles (LAX)",
        "lat": 33.9425,
        "lon": -118.4081,
        "tz": "America/Los_Angeles",
        "series_ticker": "KXHIGHLA",
        "nws_station": "KLAX"
    },
    "Miami": {
        "name": "Miami",
        "lat": 25.7617,
        "lon": -80.1918,
        "tz": "America/New_York",
        "series_ticker": "KXHIGHMIA",
        "nws_station": "KMIA"
    },
    "Denver": {
        "name": "Denver",
        "lat": 39.8561,
        "lon": -104.6737,
        "tz": "America/Denver",
        "series_ticker": "KXHIGHDEN",
        "nws_station": "KDEN"
    },
    "Austin": {
        "name": "Austin",
        "lat": 30.1944,
        "lon": -97.6700,
        "tz": "America/Chicago",
        "series_ticker": "KXHIGHAUS",
        "nws_station": "KAUS"
    }
}

def fetch_kalshi_temp_brackets(series_ticker):
    """Fetch live Kalshi temperature brackets - NO CORS in Streamlit!"""
    url = f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series_ticker}&status=open"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None, f"API returned {resp.status_code}"
        
        data = resp.json()
        markets = data.get("markets", [])
        
        if not markets:
            return None, "No markets found for this series"
        
        # Get today's date in Kalshi format (e.g., "26JAN13" or "JAN-13")
        today_et = datetime.now(pytz.timezone('US/Eastern'))
        today_str1 = today_et.strftime('%y%b%d').upper()  # "26JAN13"
        today_str2 = today_et.strftime('%b-%d').upper()   # "JAN-13"
        today_str3 = today_et.strftime('%Y-%m-%d')        # "2026-01-13"
        
        # Filter to only TODAY's markets
        today_markets = []
        for m in markets:
            event_ticker = m.get("event_ticker", "").upper()
            close_time = m.get("close_time", "")
            # Check if event ticker contains today's date
            if today_str1 in event_ticker or today_str2 in event_ticker or today_str3 in close_time[:10]:
                today_markets.append(m)
        
        # If no today markets found, try first event (fallback)
        if not today_markets and markets:
            first_event = markets[0].get("event_ticker", "")
            today_markets = [m for m in markets if m.get("event_ticker") == first_event]
        
        if not today_markets:
            return None, "No markets found for today"
        
        brackets = []
        for market in today_markets:
            ticker = market.get("ticker", "")
            title = market.get("title", "")
            subtitle = market.get("subtitle", "")
            yes_bid = market.get("yes_bid", 0)
            yes_ask = market.get("yes_ask", 0)
            no_bid = market.get("no_bid", 0)
            no_ask = market.get("no_ask", 0)
            
            range_text = subtitle if subtitle else title
            
            midpoint = None
            range_lower = range_text.lower()
            
            if "or below" in range_lower or "under" in range_lower:
                try:
                    num = int(''.join(filter(str.isdigit, range_text.split('°')[0].split()[-1])))
                    midpoint = num - 1
                except:
                    midpoint = 30
            elif "or above" in range_lower or "over" in range_lower:
                try:
                    num = int(''.join(filter(str.isdigit, range_text.split('°')[0].split()[-1])))
                    midpoint = num + 1
                except:
                    midpoint = 50
            elif "to" in range_lower or "-" in range_text:
                try:
                    if "to" in range_lower:
                        parts = range_text.replace('°', '').lower().split('to')
                    else:
                        parts = range_text.replace('°', '').split('-')
                    low = int(''.join(filter(str.isdigit, parts[0])))
                    high = int(''.join(filter(str.isdigit, parts[1])))
                    midpoint = (low + high) / 2
                except:
                    midpoint = 40
            
            brackets.append({
                "ticker": ticker,
                "range": range_text,
                "midpoint": midpoint,
                "yes_bid": yes_bid,
                "yes_ask": yes_ask,
                "no_bid": no_bid,
                "no_ask": no_ask,
                "yes_price": (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else yes_ask or yes_bid or 0,
                "no_price": (no_bid + no_ask) / 2 if no_bid and no_ask else no_ask or no_bid or 0
            })
        
        brackets.sort(key=lambda x: x['midpoint'] if x['midpoint'] else 0)
        
        return brackets, None
    except Exception as e:
        return None, str(e)

def calc_market_forecast(brackets):
    """Calculate market forecast from bracket prices (probability-weighted average)"""
    if not brackets:
        return None
    
    weighted_sum = 0
    total_prob = 0
    
    for b in brackets:
        yes_price = b['yes_price'] if b['yes_price'] else 0
        midpoint = b['midpoint']
        if midpoint and yes_price > 0:
            weighted_sum += midpoint * yes_price
            total_prob += yes_price
    
    # NORMALIZE by total probability (prices may not sum to exactly 100)
    if total_prob > 0:
        return round(weighted_sum / total_prob, 1)
    return None

def fetch_current_weather(lat, lon, station_id="KNYC"):
    """Fetch current weather from NWS (official Kalshi source!)"""
    # Try NWS API first (official source)
    nws_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    
    try:
        headers = {"User-Agent": "TempEdgeFinder/1.0"}
        resp = requests.get(nws_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            props = data.get("properties", {})
            
            # NWS gives temp in Celsius, convert to F
            temp_c = props.get("temperature", {}).get("value")
            temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
            
            # Get dew point
            dewpoint_c = props.get("dewpoint", {}).get("value")
            dewpoint_f = (dewpoint_c * 9/5) + 32 if dewpoint_c is not None else None
            
            wind_speed_mps = props.get("windSpeed", {}).get("value")
            wind_speed_mph = wind_speed_mps * 2.237 if wind_speed_mps else None
            
            wind_dir = props.get("windDirection", {}).get("value")
            
            # Get observation timestamp
            obs_time = props.get("timestamp", "")
            
            # NWS doesn't give cloud % directly, but we can get text description
            text_desc = props.get("textDescription", "")
            if "clear" in text_desc.lower() or "sunny" in text_desc.lower():
                cloud_cover = 10
            elif "partly" in text_desc.lower():
                cloud_cover = 40
            elif "mostly cloudy" in text_desc.lower():
                cloud_cover = 70
            elif "cloudy" in text_desc.lower() or "overcast" in text_desc.lower():
                cloud_cover = 90
            else:
                cloud_cover = 50
            
            return {
                "temp": temp_f,
                "dewpoint": dewpoint_f,
                "wind_speed": wind_speed_mph,
                "wind_dir": wind_dir,
                "cloud_cover": cloud_cover,
                "source": "NWS (Official)",
                "description": text_desc,
                "obs_time": obs_time
            }
    except Exception as e:
        pass
    
    # Fallback to Open-Meteo if NWS fails
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,wind_direction_10m,cloud_cover,dew_point_2m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        current = data.get("current", {})
        
        return {
            "temp": current.get("temperature_2m"),
            "dewpoint": current.get("dew_point_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_dir": current.get("wind_direction_10m"),
            "cloud_cover": current.get("cloud_cover"),
            "source": "Open-Meteo (Backup)",
            "description": "",
            "obs_time": current.get("time", "")
        }
    except:
        return None

def predict_current_temp(weather, city_tz):
    """Predict REAL current temp by interpolating from last NWS reading"""
    if not weather or not weather.get('temp'):
        return None, None, []
    
    last_temp = weather['temp']
    cloud_cover = weather.get('cloud_cover', 50)
    wind_dir = weather.get('wind_dir')
    dewpoint = weather.get('dewpoint')
    obs_time_str = weather.get('obs_time', '')
    
    factors = []
    
    # Get current time and observation time
    local_tz = pytz.timezone(city_tz)
    now = datetime.now(local_tz)
    hour = now.hour + now.minute / 60
    
    # Parse observation time
    if obs_time_str:
        try:
            obs_time = datetime.fromisoformat(obs_time_str.replace('Z', '+00:00'))
            obs_time_local = obs_time.astimezone(local_tz)
            minutes_since_obs = (now - obs_time_local).total_seconds() / 60
        except:
            minutes_since_obs = 30  # Assume 30 min if can't parse
    else:
        minutes_since_obs = 30
    
    factors.append(f"Last NWS reading: {minutes_since_obs:.0f} min ago")
    
    # Base heating rate by time of day
    if hour < 6:
        base_rate = -0.5  # Cooling overnight
        factors.append(f"Time {hour:.1f}h: Pre-dawn cooling (-0.5°F/hr)")
    elif hour < 10:
        base_rate = 1.5  # Morning warming
        factors.append(f"Time {hour:.1f}h: Morning warming (+1.5°F/hr)")
    elif hour < 14:
        base_rate = 0.8  # Peak sun
        factors.append(f"Time {hour:.1f}h: Peak heating (+0.8°F/hr)")
    elif hour < 17:
        base_rate = 0.0  # Plateau
        factors.append(f"Time {hour:.1f}h: Afternoon plateau (0°F/hr)")
    else:
        base_rate = -0.3  # Evening cooling
        factors.append(f"Time {hour:.1f}h: Evening cooling (-0.3°F/hr)")
    
    # Adjust for cloud cover
    if cloud_cover >= 80:
        cloud_factor = 0.3  # Heavy clouds = 30% of normal heating
        factors.append(f"Clouds {cloud_cover}%: Heavy cap (×0.3)")
    elif cloud_cover >= 50:
        cloud_factor = 0.6  # Partial clouds
        factors.append(f"Clouds {cloud_cover}%: Partial cap (×0.6)")
    else:
        cloud_factor = 1.0  # Clear
        factors.append(f"Clouds {cloud_cover}%: Clear sky (×1.0)")
    
    # Adjust for wind direction (advection)
    advection_adj = 0
    if wind_dir:
        dir_name = get_wind_direction_name(wind_dir)
        if dir_name in ["SW", "SSW", "S", "SSE"]:
            advection_adj = 0.3  # Warm advection
            factors.append(f"Wind {dir_name}: Warm advection (+0.3°F/hr)")
        elif dir_name in ["NW", "NNW", "N", "NNE"]:
            advection_adj = -0.5  # Cold advection
            factors.append(f"Wind {dir_name}: Cold advection (-0.5°F/hr)")
        else:
            factors.append(f"Wind {dir_name}: Neutral")
    
    # Adjust for dew point (moisture slows heating)
    if dewpoint:
        dewpoint_spread = last_temp - dewpoint
        if dewpoint_spread < 10:
            moisture_factor = 0.7  # High moisture
            factors.append(f"Dewpoint spread {dewpoint_spread:.0f}°F: High moisture (×0.7)")
        elif dewpoint_spread > 25:
            moisture_factor = 1.2  # Very dry, heats fast
            factors.append(f"Dewpoint spread {dewpoint_spread:.0f}°F: Dry air (×1.2)")
        else:
            moisture_factor = 1.0
            factors.append(f"Dewpoint spread {dewpoint_spread:.0f}°F: Normal")
    else:
        moisture_factor = 1.0
    
    # Calculate predicted change
    adjusted_rate = (base_rate * cloud_factor + advection_adj) * moisture_factor
    hours_since_obs = minutes_since_obs / 60
    temp_change = adjusted_rate * hours_since_obs
    
    predicted_temp = last_temp + temp_change
    
    factors.append(f"---")
    factors.append(f"Adjusted rate: {adjusted_rate:+.2f}°F/hr")
    factors.append(f"Change since reading: {temp_change:+.1f}°F")
    
    return predicted_temp, minutes_since_obs, factors

def get_wind_direction_name(degrees):
    """Convert wind degrees to direction name"""
    if degrees is None:
        return "Unknown"
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / 22.5) % 16
    return dirs[idx]

def calc_edge_score(cushion, pace, hour, cloud_cover, wind_speed, wind_dir):
    """Calculate total edge score (0-10 scale)"""
    score = 0
    breakdown = []
    
    if cushion >= 3.0:
        score += 4
        breakdown.append(f"Cushion +{cushion:.1f}°F → +4")
    elif cushion >= 2.0:
        score += 3
        breakdown.append(f"Cushion +{cushion:.1f}°F → +3")
    elif cushion >= 1.0:
        score += 2
        breakdown.append(f"Cushion +{cushion:.1f}°F → +2")
    elif cushion >= 0.5:
        score += 1
        breakdown.append(f"Cushion +{cushion:.1f}°F → +1")
    else:
        breakdown.append(f"Cushion +{cushion:.1f}°F → +0")
    
    if pace <= 0.3:
        score += 3
        breakdown.append(f"Pace {pace:.2f}°F/hr (slow) → +3")
    elif pace <= 0.5:
        score += 2
        breakdown.append(f"Pace {pace:.2f}°F/hr → +2")
    elif pace <= 0.8:
        score += 1
        breakdown.append(f"Pace {pace:.2f}°F/hr → +1")
    elif pace <= 1.0:
        breakdown.append(f"Pace {pace:.2f}°F/hr → +0")
    else:
        score -= 1
        breakdown.append(f"Pace {pace:.2f}°F/hr (fast!) → -1")
    
    if hour < 10.5:
        breakdown.append(f"Time {hour:.1f}h (early noise) → +0")
    elif hour < 12:
        score += 1
        breakdown.append(f"Time {hour:.1f}h (forming) → +1")
    elif hour < 14:
        score += 2
        breakdown.append(f"Time {hour:.1f}h (signal!) → +2")
    else:
        score -= 1
        breakdown.append(f"Time {hour:.1f}h (late risk) → -1")
    
    if cloud_cover and cloud_cover >= 70:
        score += 1
        breakdown.append(f"Clouds {cloud_cover}% (cap) → +1")
    elif cloud_cover and cloud_cover < 30:
        score -= 1
        breakdown.append(f"Clouds {cloud_cover}% (clear risk) → -1")
    
    if wind_speed and wind_speed >= 10:
        score += 1
        breakdown.append(f"Wind {wind_speed:.0f}mph → +1")
    
    if wind_dir:
        dir_name = get_wind_direction_name(wind_dir)
        if dir_name in ["SW", "SSW", "WSW"]:
            score -= 2
            breakdown.append(f"Wind from {dir_name} (heat advection!) → -2")
        elif dir_name in ["NW", "NNW", "N", "NNE"]:
            score += 2
            breakdown.append(f"Wind from {dir_name} (cold advection) → +2")
    
    return max(0, min(10, score)), breakdown

# ========== HEADER ==========
now = datetime.now(pytz.timezone('US/Eastern'))
st.title("🌡️ TEMPERATURE EDGE FINDER")
st.caption(f"Last update: {now.strftime('%I:%M:%S %p ET')} | v1.1 | Kalshi High Temp Markets")

# ========== CITY SELECTOR ==========
col1, col2 = st.columns([2, 3])
selected_city = col1.selectbox("Select City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
city_config = CITIES[selected_city]

# ========== FETCH DATA ==========
with st.spinner("Fetching Kalshi brackets..."):
    brackets, bracket_error = fetch_kalshi_temp_brackets(city_config['series_ticker'])

with st.spinner("Fetching weather from NWS..."):
    weather = fetch_current_weather(city_config['lat'], city_config['lon'], city_config.get('nws_station', 'KNYC'))

# ========== NO EDGE FINDER ==========
st.subheader("🎯 NO EDGE FINDER")

if brackets and weather and weather['temp']:
    current_temp = weather['temp']
    
    # Estimate final high based on current temp, time of day, and conditions
    local_tz = pytz.timezone(city_config['tz'])
    local_now = datetime.now(local_tz)
    hour = local_now.hour + local_now.minute / 60
    
    # Simple projection: current temp + expected remaining rise
    if hour < 10:
        remaining_rise = 8  # Morning, lots of heating left
    elif hour < 12:
        remaining_rise = 5  # Late morning
    elif hour < 14:
        remaining_rise = 3  # Early afternoon
    elif hour < 16:
        remaining_rise = 1  # Late afternoon
    else:
        remaining_rise = 0  # Evening, high likely set
    
    # Adjust for clouds (cap heating)
    if weather['cloud_cover'] and weather['cloud_cover'] >= 70:
        remaining_rise *= 0.5
    
    projected_high = current_temp + remaining_rise
    projected_rounded = round(projected_high)
    
    st.markdown(f"### 🌡️ Current: **{current_temp:.1f}°F** → Projected High: **{projected_high:.1f}°F** (rounds to {projected_rounded}°F)")
    
    if hour >= 16:
        st.warning("⏰ After 4 PM — High likely already set. Market is probably settled.")
    
    # Find the WINNING bracket (highest YES price = market consensus)
    winning_bracket = max(brackets, key=lambda x: x['yes_price'] if x['yes_price'] else 0)
    
    if winning_bracket['yes_price'] and winning_bracket['yes_price'] >= 90:
        st.error(f"🏆 **{winning_bracket['range']}** already WON @ {winning_bracket['yes_price']:.0f}¢ YES — Market settled, no edge left!")
        st.info("Come back tomorrow between 10 AM - 2 PM for live edge opportunities.")
        no_edges = []
    else:
        # Market NOT settled yet — find NO edges
        # Good NO = bracket FAR from projected high with cheap NO price (YES is high-ish but not 90%+)
        no_edges = []
        for b in brackets:
            if b['midpoint'] and b['yes_price'] is not None:
                yes_price = b['yes_price']
                no_price = 100 - yes_price
                
                # Skip if market already settled this bracket (YES 90%+ or YES 5% or less)
                if yes_price >= 90:
                    continue  # This bracket likely won, NO is dead
                if yes_price <= 5:
                    continue  # NO already at 95¢+, already priced in
                
                # Calculate distance from projected high
                distance = abs(b['midpoint'] - projected_high)
                
                # Good NO target = FAR from projected high
                if distance >= 5:
                    confidence = "HIGH"
                    edge_score = 3
                elif distance >= 3:
                    confidence = "MEDIUM"
                    edge_score = 2
                elif distance >= 2:
                    confidence = "LOW"
                    edge_score = 1
                else:
                    confidence = "SKIP"
                    edge_score = 0
                
                if edge_score > 0:
                    no_edges.append({
                        'range': b['range'],
                        'midpoint': b['midpoint'],
                        'yes_price': yes_price,
                        'no_price': no_price,
                        'distance': distance,
                        'confidence': confidence,
                        'edge_score': edge_score
                    })
        
        # Sort by edge score (highest first), then by NO price (cheaper = better value)
        no_edges.sort(key=lambda x: (-x['edge_score'], x['no_price']))
    
    if no_edges:
        st.markdown("### 💰 Best NO Opportunities")
        st.caption("Buy NO on brackets FAR from projected high")
        
        for edge in no_edges:
            if edge['confidence'] == "HIGH":
                color = "#00ff00"
                emoji = "🟢"
            elif edge['confidence'] == "MEDIUM":
                color = "#ffff00"
                emoji = "🟡"
            else:
                color = "#ff8800"
                emoji = "🟠"
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            col1.markdown(f"**{edge['range']}**")
            col2.markdown(f"NO @ **{edge['no_price']:.0f}¢**")
            col3.markdown(f"{edge['distance']:.1f}°F away")
            col4.markdown(f"<span style='color:{color}'>{emoji} **{edge['confidence']}**</span>", unsafe_allow_html=True)
    elif hour < 16:
        st.info("No clear NO edges right now. Prices may be too settled or too uncertain.")
    
    st.divider()
else:
    st.warning("Need bracket data and weather to find NO edges")
    st.divider()

# ========== MARKET OVERVIEW ==========
st.subheader(f"📊 {city_config['name']} High Temp Market")

if bracket_error:
    st.error(f"⚠️ Could not fetch Kalshi data: {bracket_error}")
    st.info("Market may not be open yet, or ticker format changed. Try manual entry below.")
    brackets = None

if brackets:
    market_forecast = calc_market_forecast(brackets)
    
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Market Forecast", f"{market_forecast}°F" if market_forecast else "—")
    mc2.metric("Brackets Available", len(brackets))
    mc3.metric("Current Temp", f"{weather['temp']:.0f}°F" if weather and weather['temp'] else "—")
    
    st.markdown("### 📈 Live Bracket Prices")
    
    hcols = st.columns([2, 1, 1, 1, 1])
    hcols[0].markdown("**Range**")
    hcols[1].markdown("**Yes Bid**")
    hcols[2].markdown("**Yes Ask**")
    hcols[3].markdown("**No Bid**")
    hcols[4].markdown("**No Ask**")
    
    for b in brackets:
        rcols = st.columns([2, 1, 1, 1, 1])
        rcols[0].write(b['range'])
        
        yes_bid = b['yes_bid']
        yes_ask = b['yes_ask']
        no_bid = b['no_bid']
        no_ask = b['no_ask']
        
        if yes_bid and yes_bid >= 50:
            rcols[1].markdown(f"<span style='color:#00ff00'>**{yes_bid}¢**</span>", unsafe_allow_html=True)
        else:
            rcols[1].write(f"{yes_bid}¢" if yes_bid else "—")
        
        rcols[2].write(f"{yes_ask}¢" if yes_ask else "—")
        rcols[3].write(f"{no_bid}¢" if no_bid else "—")
        rcols[4].write(f"{no_ask}¢" if no_ask else "—")

st.divider()

# ========== CURRENT CONDITIONS ==========
st.subheader("🌤️ Current Conditions")

if weather:
    # Show source prominently
    source = weather.get('source', 'Unknown')
    if "NWS" in source:
        st.success(f"📡 Data Source: **{source}** — Same source Kalshi uses for settlement!")
    else:
        st.warning(f"📡 Data Source: **{source}** — NWS unavailable, using backup")
    
    if weather.get('description'):
        st.caption(f"Conditions: {weather['description']}")
    
    # Calculate predicted current temp
    predicted_temp, mins_ago, prediction_factors = predict_current_temp(weather, city_config['tz'])
    
    # Show both NWS reading and predicted current
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Last NWS Reading", f"{weather['temp']:.1f}°F" if weather['temp'] else "—", 
               f"{mins_ago:.0f} min ago" if mins_ago else None)
    tc2.metric("🎯 Predicted NOW", f"{predicted_temp:.1f}°F" if predicted_temp else "—",
               f"{predicted_temp - weather['temp']:+.1f}°F" if predicted_temp and weather['temp'] else None)
    tc3.metric("Kalshi Rounds To", f"{round(predicted_temp)}°F" if predicted_temp else "—")
    
    wc1, wc2, wc3, wc4 = st.columns(4)
    wc1.metric("Dewpoint", f"{weather['dewpoint']:.1f}°F" if weather.get('dewpoint') else "—")
    wc2.metric("Wind Speed", f"{weather['wind_speed']:.0f} mph" if weather['wind_speed'] else "—")
    wc3.metric("Wind Direction", get_wind_direction_name(weather['wind_dir']) if weather['wind_dir'] else "—")
    wc4.metric("Cloud Cover", f"{weather['cloud_cover']}%" if weather['cloud_cover'] is not None else "—")
    
    # Show prediction breakdown
    with st.expander("🔬 Prediction Model Breakdown"):
        for factor in prediction_factors:
            st.markdown(f"• {factor}")
else:
    st.warning("Could not fetch current weather")
    predicted_temp = None

st.divider()

# ========== EDGE CALCULATOR ==========
st.subheader("🎯 EDGE CALCULATOR")

if brackets and len(brackets) > 0:
    st.caption("Select a bracket from today's Kalshi market")
    
    # Show current temp prominently
    if weather and weather['temp']:
        current_temp = weather['temp']
        rounded_temp = round(current_temp)  # Kalshi rounds to nearest whole number
        st.markdown(f"### 🌡️ Current Temp: **{current_temp:.1f}°F** → Kalshi rounds to **{rounded_temp}°F**")
    else:
        current_temp = 40.0
        st.warning("Could not fetch current temperature")
    
    ec1, ec2 = st.columns([2, 1])
    
    # Dropdown with real brackets
    bracket_options = [b['range'] for b in brackets]
    selected_bracket_name = ec1.selectbox("Select Bracket", bracket_options)
    
    # Find the selected bracket data
    selected_bracket = next((b for b in brackets if b['range'] == selected_bracket_name), None)
    
    bet_side = ec2.selectbox("Bet Side", ["NO (Under)", "YES (Over)"])
    
    # Show bracket details
    if selected_bracket:
        bc1, bc2, bc3, bc4 = st.columns(4)
        bc1.metric("Bracket", selected_bracket['range'])
        bc2.metric("Yes Price", f"{selected_bracket['yes_price']:.0f}¢" if selected_bracket['yes_price'] else "—")
        bc3.metric("No Price", f"{100 - selected_bracket['yes_price']:.0f}¢" if selected_bracket['yes_price'] else "—")
        bc4.metric("Midpoint", f"{selected_bracket['midpoint']}°F" if selected_bracket['midpoint'] else "—")
        
        # User projection input - default to current temp + expected rise
        your_projection = st.number_input("Your High Temp Projection (°F)", 20.0, 100.0, current_temp + 3, 0.5)
        
        # Show what Kalshi will round your projection to
        your_rounded = round(your_projection)
        st.caption(f"💡 Your projection {your_projection}°F → Kalshi rounds to **{your_rounded}°F**")
        
        # Calculate cushion based on bracket and bet side
        if selected_bracket['midpoint']:
            if "NO" in bet_side:
                # NO bet wins if actual high is BELOW the bracket
                # Cushion = how much room before high reaches this bracket
                cushion = selected_bracket['midpoint'] - your_projection
            else:
                # YES bet wins if actual high is IN or ABOVE the bracket
                cushion = your_projection - selected_bracket['midpoint']
            
            target_bracket = selected_bracket['midpoint']
        else:
            cushion = 0
            target_bracket = 45
else:
    st.warning("No brackets loaded. Check Kalshi data above or use manual entry below.")
    current_temp = weather['temp'] if weather and weather['temp'] else 40.0
    your_projection = st.number_input("Your High Temp Projection (°F)", 20.0, 100.0, current_temp + 5, 0.5)
    target_bracket = st.number_input("Target Bracket (°F)", 20.0, 100.0, current_temp + 8, 1.0)
    bet_side = st.selectbox("Bet Side", ["NO (Under)", "YES (Over)"])
    if "NO" in bet_side:
        cushion = target_bracket - your_projection
    else:
        cushion = your_projection - target_bracket

local_tz = pytz.timezone(city_config['tz'])
local_now = datetime.now(local_tz)
hours_since_midnight = local_now.hour + local_now.minute / 60

if weather and weather['temp'] and hours_since_midnight > 6:
    baseline_estimate = weather['temp'] - 5
    pace_estimate = (weather['temp'] - baseline_estimate) / max(1, hours_since_midnight - 6)
else:
    pace_estimate = 0.5

with st.expander("⚙️ Adjust Pace & Conditions", expanded=False):
    pace_override = st.number_input("Pace (°F/hr)", 0.0, 3.0, pace_estimate, 0.1)
    cloud_override = st.number_input("Cloud Cover %", 0, 100, weather['cloud_cover'] if weather and weather['cloud_cover'] else 50)
    wind_override = st.number_input("Wind Speed (mph)", 0, 50, int(weather['wind_speed']) if weather and weather['wind_speed'] else 5)
    wind_dir_override = st.number_input("Wind Direction (°)", 0, 360, int(weather['wind_dir']) if weather and weather['wind_dir'] else 270)

if "NO" in bet_side:
    cushion = target_bracket - your_projection
else:
    cushion = your_projection - target_bracket

edge_score, breakdown = calc_edge_score(
    cushion, 
    pace_override if 'pace_override' in dir() else pace_estimate,
    hours_since_midnight,
    cloud_override if 'cloud_override' in dir() else (weather['cloud_cover'] if weather else 50),
    wind_override if 'wind_override' in dir() else (weather['wind_speed'] if weather else 5),
    wind_dir_override if 'wind_dir_override' in dir() else (weather['wind_dir'] if weather else 270)
)

st.markdown("### 📊 Edge Analysis")

if edge_score >= 8:
    edge_color = "#00ff00"
    edge_label = "🟢 STRONG EDGE"
elif edge_score >= 6:
    edge_color = "#88ff00"
    edge_label = "🟢 GOOD EDGE"
elif edge_score >= 4:
    edge_color = "#ffff00"
    edge_label = "🟡 LEAN"
else:
    edge_color = "#ff4444"
    edge_label = "🔴 NO EDGE"

rc1, rc2, rc3 = st.columns(3)
rc1.markdown(f"<span style='font-size:2em;color:{edge_color}'><b>{edge_score}/10</b></span><br>{edge_label}", unsafe_allow_html=True)
rc2.metric("Cushion", f"{cushion:+.1f}°F")
rc3.metric("Your Projection", f"{your_projection}°F")

with st.expander("📋 Score Breakdown", expanded=True):
    for item in breakdown:
        st.markdown(f"• {item}")

if brackets:
    market_forecast = calc_market_forecast(brackets)
    if market_forecast:
        diff = your_projection - market_forecast
        st.markdown("---")
        st.markdown(f"**Market Forecast:** {market_forecast}°F | **Your Projection:** {your_projection}°F | **Diff:** {diff:+.1f}°F")
        
        if abs(diff) >= 1:
            if diff > 0:
                st.info(f"📈 You predict **HIGHER** than market by {diff:.1f}°F → Look for **YES** edge on higher brackets")
            else:
                st.info(f"📉 You predict **LOWER** than market by {abs(diff):.1f}°F → Look for **NO** edge on higher brackets")

st.divider()

# ========== POSITION TRACKER ==========
st.subheader("📈 ACTIVE POSITIONS")

with st.expander("➕ Add Position", expanded=False):
    pc1, pc2, pc3, pc4 = st.columns(4)
    pos_city = pc1.selectbox("City", list(CITIES.keys()), key="pos_city")
    pos_bracket = pc2.text_input("Bracket (e.g., '41-42')", "41-42")
    pos_side = pc3.selectbox("Side", ["NO", "YES"], key="pos_side")
    pos_price = pc4.number_input("Price ¢", 1, 99, 75, key="pos_price")
    
    pc5, pc6 = st.columns(2)
    pos_contracts = pc5.number_input("Contracts", 1, 1000, 100, key="pos_contracts")
    pos_target = pc6.number_input("Target Temp °F", 20.0, 100.0, 42.0, 0.5, key="pos_target")
    
    if st.button("➕ ADD POSITION", type="primary"):
        st.session_state.temp_positions.append({
            "city": pos_city,
            "bracket": pos_bracket,
            "side": pos_side,
            "price": pos_price,
            "contracts": pos_contracts,
            "target": pos_target,
            "added": datetime.now().isoformat()
        })
        st.rerun()

if st.session_state.temp_positions:
    for idx, pos in enumerate(st.session_state.temp_positions):
        pos_city_config = CITIES[pos['city']]
        pos_weather = fetch_current_weather(pos_city_config['lat'], pos_city_config['lon'], pos_city_config.get('nws_station', 'KNYC'))
        current_temp = pos_weather['temp'] if pos_weather and pos_weather['temp'] else None
        
        if current_temp:
            if pos['side'] == "NO":
                pos_cushion = pos['target'] - current_temp
            else:
                pos_cushion = current_temp - pos['target']
            
            if pos_cushion > 5:
                status = f"🟢 +{pos_cushion:.1f}°F"
            elif pos_cushion > 2:
                status = f"🟡 +{pos_cushion:.1f}°F"
            elif pos_cushion > 0:
                status = f"🟠 +{pos_cushion:.1f}°F"
            else:
                status = f"🔴 {pos_cushion:+.1f}°F"
        else:
            status = "⏳"
            pos_cushion = 0
        
        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 2, 1])
        c1.markdown(f"**{pos['city']}** {pos['bracket']}")
        c2.markdown(f"**{pos['side']}** @ {pos['price']}¢ × {pos['contracts']}")
        c3.markdown(f"Now: {current_temp:.0f}°F" if current_temp else "—")
        c4.markdown(f"**{status}**")
        if c5.button("❌", key=f"del_temp_{idx}"):
            st.session_state.temp_positions.pop(idx)
            st.rerun()
    
    total_risk = sum(p['price'] * p['contracts'] for p in st.session_state.temp_positions) / 100
    total_potential = sum((100 - p['price']) * p['contracts'] for p in st.session_state.temp_positions) / 100
    
    sc1, sc2 = st.columns([4, 1])
    sc1.markdown(f"**💰 Risk: ${total_risk:.2f} | Potential: ${total_potential:.2f}**")
    if sc2.button("🗑️ Clear All", key="clear_temp"):
        st.session_state.temp_positions = []
        st.rerun()
else:
    st.info("No positions yet. Add one above ⬆️")

st.divider()

# ========== MANUAL BRACKET ENTRY ==========
st.subheader("📝 Manual Bracket Entry")
st.caption("If API doesn't work, paste bracket prices here")

manual_brackets = st.text_area(
    "Paste brackets (format: range, yes_price per line)",
    placeholder="39° or below, 5\n40° to 41°, 15\n42° to 43°, 45\n44° to 45°, 30\n46° or above, 5",
    height=150
)

if manual_brackets and st.button("Parse Manual Brackets"):
    parsed = []
    for line in manual_brackets.strip().split('\n'):
        if ',' in line:
            parts = line.split(',')
            range_text = parts[0].strip()
            try:
                yes_price = int(parts[1].strip())
                parsed.append({
                    "range": range_text,
                    "yes_price": yes_price,
                    "midpoint": 40
                })
            except:
                pass
    
    if parsed:
        st.success(f"Parsed {len(parsed)} brackets")
        for p in parsed:
            st.write(f"• {p['range']}: {p['yes_price']}¢")
        
        total = sum(p['yes_price'] for p in parsed)
        st.info(f"Total probability: {total}% (should be ~100%)")

st.divider()

# ========== HOW TO USE ==========
with st.expander("📚 HOW TO USE"):
    st.markdown("""
    ## Temperature Edge Workflow
    
    ### Pre-Market (Before 10 AM)
    1. Check weather forecast for the day
    2. Note overnight low and expected high
    3. Identify cloud cover and wind patterns
    4. **Wait** - signal is noise before 10:30 AM
    
    ### Signal Window (10:30 AM - 2:00 PM)
    1. Monitor current temperature and pace
    2. Compare your projection to Market Forecast
    3. Calculate edge score for target brackets
    4. **Entry point:** Edge score 6+ with 2°F+ cushion
    
    ### The Edge Formula
    - **Cushion** = Your projection vs bracket boundary
    - **Pace** = How fast temp is rising (°F per hour)
    - **Weather** = Clouds cap heat, wind affects feel
    
    ### NO Bet Logic (Under)
    - Clouds ≥70% → Temperature capped
    - Cold front (NW wind) → Heat stalls
    - Pace slowing → Won't reach high
    
    ### YES Bet Logic (Over)
    - Clear skies → Solar heating continues
    - Warm advection (SW wind) → Temps rise
    - Pace accelerating → Will exceed forecast
    
    ### Settlement
    - NWS Daily Climate Report (released ~4-5 PM local)
    - Settlement is official high at reporting station
    """)

st.divider()
st.caption("⚠️ DISCLAIMER: For entertainment and educational purposes only. Not financial advice. Past performance does not guarantee future results.")
