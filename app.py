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
    
    st.subheader("Prediction Method")
    st.markdown("""
    1. Fetch NWS hourly history
    2. Calculate real °F/hr rate
    3. Project to peak (2-3 PM)
    4. Add +1 to +2°F bias
    """)
    
    st.divider()
    
    st.subheader("NO Edge Strategy")
    st.markdown("""
    **Your prediction < Market** → BUY NO on upper brackets
    
    **Your prediction > Market** → BUY NO on lower brackets
    
    **Within 1°F** → No edge, skip
    """)
    
    st.divider()
    st.caption("v2.1 | Settlement: NWS Daily Climate Report")

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

# ========== FUNCTIONS ==========
def fetch_kalshi_temp_brackets(series_ticker):
    """Fetch live Kalshi temperature brackets"""
    url = f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series_ticker}&status=open"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None, f"API returned {resp.status_code}"
        
        data = resp.json()
        markets = data.get("markets", [])
        
        if not markets:
            return None, "No markets found"
        
        # Get today's date
        today_et = datetime.now(pytz.timezone('US/Eastern'))
        today_str1 = today_et.strftime('%y%b%d').upper()
        today_str2 = today_et.strftime('%b-%d').upper()
        today_str3 = today_et.strftime('%Y-%m-%d')
        
        # Filter to today
        today_markets = []
        for m in markets:
            event_ticker = m.get("event_ticker", "").upper()
            close_time = m.get("close_time", "")
            if today_str1 in event_ticker or today_str2 in event_ticker or today_str3 in close_time[:10]:
                today_markets.append(m)
        
        if not today_markets and markets:
            first_event = markets[0].get("event_ticker", "")
            today_markets = [m for m in markets if m.get("event_ticker") == first_event]
        
        if not today_markets:
            return None, "No markets for today"
        
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
    """Calculate market forecast from bracket prices"""
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
    
    if total_prob > 0:
        return round(weighted_sum / total_prob, 1)
    return None

def fetch_nws_history(station_id="KNYC"):
    """Fetch last 24 hours of NWS observations"""
    url = f"https://api.weather.gov/stations/{station_id}/observations"
    
    try:
        headers = {"User-Agent": "TempEdgeFinder/2.1"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        features = data.get("features", [])
        
        readings = []
        for f in features[:24]:
            props = f.get("properties", {})
            temp_c = props.get("temperature", {}).get("value")
            if temp_c is None:
                continue
            temp_f = (temp_c * 9/5) + 32
            timestamp = props.get("timestamp", "")
            readings.append({"time": timestamp, "temp": temp_f})
        
        return readings
    except:
        return None

def fetch_current_weather(lat, lon, station_id="KNYC"):
    """Fetch current weather from NWS"""
    nws_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    
    try:
        headers = {"User-Agent": "TempEdgeFinder/2.1"}
        resp = requests.get(nws_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            props = data.get("properties", {})
            
            temp_c = props.get("temperature", {}).get("value")
            temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
            
            dewpoint_c = props.get("dewpoint", {}).get("value")
            dewpoint_f = (dewpoint_c * 9/5) + 32 if dewpoint_c is not None else None
            
            wind_speed_mps = props.get("windSpeed", {}).get("value")
            wind_speed_mph = wind_speed_mps * 2.237 if wind_speed_mps else None
            
            wind_dir = props.get("windDirection", {}).get("value")
            obs_time = props.get("timestamp", "")
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
    except:
        pass
    
    # Fallback
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
            "obs_time": ""
        }
    except:
        return None

def get_wind_direction_name(degrees):
    """Convert wind degrees to direction name"""
    if degrees is None:
        return "Unknown"
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / 22.5) % 16
    return dirs[idx]

f}-{projected_high:.0f}°F**")
        
        return projected_low, projected_high, factors
    else:
        factors.append("")
        factors.append("⏳ Need more data (check after 9 AM)")
        return None, None, factors

# ========== HEADER ==========
now = datetime.now(pytz.timezone('US/Eastern'))
st.title("🌡️ TEMPERATURE EDGE FINDER")
st.caption(f"Last update: {now.strftime('%I:%M:%S %p ET')} | v2.1 | NWS Real Data")

# ========== CITY SELECTOR ==========
selected_city = st.selectbox("Select City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
city_config = CITIES[selected_city]

# ========== FETCH ALL DATA ==========
with st.spinner("Fetching Kalshi brackets..."):
    brackets, bracket_error = fetch_kalshi_temp_brackets(city_config['series_ticker'])

with st.spinner("Fetching NWS current weather..."):
    weather = fetch_current_weather(city_config['lat'], city_config['lon'], city_config.get('nws_station', 'KNYC'))

with st.spinner("Fetching NWS hourly history..."):
    nws_history = fetch_nws_history(city_config.get('nws_station', 'KNYC'))

st.divider()

# ========== CURRENT CONDITIONS ==========
st.subheader("🌤️ Current Conditions")

if weather:
    source = weather.get('source', 'Unknown')
    if "NWS" in source:
        st.success(f"📡 **{source}** — Same source Kalshi uses!")
    else:
        st.warning(f"📡 **{source}**")
    
    if weather.get('description'):
        st.caption(f"Conditions: {weather['description']}")
    
    wc1, wc2, wc3, wc4 = st.columns(4)
    wc1.metric("Temperature", f"{weather['temp']:.1f}°F" if weather['temp'] else "—")
    wc2.metric("Wind", f"{weather['wind_speed']:.0f} mph {get_wind_direction_name(weather['wind_dir'])}" if weather['wind_speed'] else "—")
    wc3.metric("Dewpoint", f"{weather['dewpoint']:.1f}°F" if weather.get('dewpoint') else "—")
    wc4.metric("Clouds", f"{weather['cloud_cover']}%" if weather['cloud_cover'] else "—")
else:
    st.warning("Could not fetch weather")

st.divider()

# ========== HIGH PREDICTION ==========
st.subheader("🎯 HIGH TEMP PREDICTION")

if nws_history:
    pred_low, pred_high, pred_factors = calc_heating_rate_and_predict(nws_history, city_config['tz'])
    
    if pred_low and pred_high:
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("🎯 YOUR Prediction", f"{pred_low:.0f}-{pred_high:.0f}°F")
        
        if brackets:
            market_forecast = calc_market_forecast(brackets)
            if market_forecast:
                pc2.metric("Market Forecast", f"{market_forecast:.1f}°F")
                diff = ((pred_low + pred_high) / 2) - market_forecast
                
                if diff < -2:
                    pc3.metric("Edge", f"{diff:+.1f}°F", "YOU SEE LOWER")
                    st.success(f"🎯 **EDGE:** You predict LOWER → **BUY NO on {int(market_forecast)}°F+ brackets!**")
                elif diff > 2:
                    pc3.metric("Edge", f"{diff:+.1f}°F", "YOU SEE HIGHER")
                    st.success(f"🎯 **EDGE:** You predict HIGHER → **BUY NO on brackets below {int(pred_low)}°F!**")
                else:
                    pc3.metric("Edge", f"{diff:+.1f}°F", "NO EDGE")
                    st.info("Your prediction matches market — no edge")
        
        with st.expander("📊 Calculation Details"):
            for f in pred_factors:
                st.markdown(f)
    else:
        st.info("⏳ Need more daytime data. Best after 9-10 AM.")
        if pred_factors:
            with st.expander("Data So Far"):
                for f in pred_factors:
                    st.markdown(f)
else:
    st.warning("Could not fetch NWS history")

st.divider()

# ========== MARKET OVERVIEW ==========
st.subheader(f"📊 {city_config['name']} Kalshi Market")

if bracket_error:
    st.error(f"⚠️ {bracket_error}")

if brackets:
    market_forecast = calc_market_forecast(brackets)
    
    mc1, mc2 = st.columns(2)
    mc1.metric("Market Forecast", f"{market_forecast}°F" if market_forecast else "—")
    mc2.metric("Brackets", len(brackets))
    
    st.markdown("### Live Prices")
    
    for b in brackets:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        col1.write(b['range'])
        
        yes_price = b['yes_price']
        if yes_price >= 90:
            col2.markdown(f"<span style='color:#00ff00'>**YES {yes_price:.0f}¢**</span>", unsafe_allow_html=True)
        elif yes_price >= 50:
            col2.markdown(f"**YES {yes_price:.0f}¢**")
        else:
            col2.write(f"YES {yes_price:.0f}¢")
        
        col3.write(f"NO {100-yes_price:.0f}¢")
        col4.write(f"Mid: {b['midpoint']}°")

st.divider()

# ========== NO EDGE FINDER ==========
st.subheader("💰 NO EDGE FINDER")

if brackets and nws_history:
    pred_low, pred_high, _ = calc_heating_rate_and_predict(nws_history, city_config['tz'])
    
    if pred_low and pred_high:
        predicted_mid = (pred_low + pred_high) / 2
        
        st.markdown(f"**Your Prediction: {pred_low:.0f}-{pred_high:.0f}°F**")
        
        # Check if market settled
        winning_bracket = max(brackets, key=lambda x: x['yes_price'] if x['yes_price'] else 0)
        
        if winning_bracket['yes_price'] and winning_bracket['yes_price'] >= 90:
            st.error(f"🏆 **{winning_bracket['range']}** @ {winning_bracket['yes_price']:.0f}¢ — Market settled!")
        else:
            no_edges = []
            for b in brackets:
                if b['midpoint'] and b['yes_price']:
                    yes_price = b['yes_price']
                    if yes_price >= 85 or yes_price <= 10:
                        continue
                    
                    if b['midpoint'] < pred_low - 1:
                        direction = "BELOW"
                        distance = pred_low - b['midpoint']
                        conf = "HIGH" if distance >= 4 else "MED"
                        no_edges.append({"b": b, "dir": direction, "dist": distance, "conf": conf})
                    elif b['midpoint'] > pred_high + 1:
                        direction = "ABOVE"
                        distance = b['midpoint'] - pred_high
                        conf = "HIGH" if distance >= 4 else "MED"
                        no_edges.append({"b": b, "dir": direction, "dist": distance, "conf": conf})
            
            if no_edges:
                no_edges.sort(key=lambda x: -x['dist'])
                st.markdown("### Best NO Targets:")
                for e in no_edges:
                    b = e['b']
                    color = "#00ff00" if e['conf'] == "HIGH" else "#ffff00"
                    st.markdown(f"**{b['range']}** — NO @ {100-b['yes_price']:.0f}¢ — {e['dir']} your range — <span style='color:{color}'>{e['conf']}</span>", unsafe_allow_html=True)
            else:
                st.info("No clear NO edges — prices align with your prediction")
    else:
        st.info("⏳ Need prediction first (check after 9 AM)")
else:
    st.warning("Need brackets and NWS data")

st.divider()

# ========== POSITION TRACKER ==========
st.subheader("📈 Positions")

with st.expander("➕ Add Position"):
    pc1, pc2, pc3 = st.columns(3)
    pos_bracket = pc1.text_input("Bracket", "47-48")
    pos_side = pc2.selectbox("Side", ["NO", "YES"])
    pos_price = pc3.number_input("Price ¢", 1, 99, 75)
    pos_contracts = st.number_input("Contracts", 1, 1000, 100)
    
    if st.button("Add"):
        st.session_state.temp_positions.append({
            "bracket": pos_bracket,
            "side": pos_side,
            "price": pos_price,
            "contracts": pos_contracts
        })
        st.rerun()

if st.session_state.temp_positions:
    for i, p in enumerate(st.session_state.temp_positions):
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{p['side']}** {p['bracket']}")
        c2.write(f"{p['price']}¢ × {p['contracts']}")
        if c3.button("❌", key=f"del_{i}"):
            st.session_state.temp_positions.pop(i)
            st.rerun()
    
    total = sum(p['price'] * p['contracts'] for p in st.session_state.temp_positions) / 100
    st.markdown(f"**Total Risk: ${total:.2f}**")

st.divider()
st.caption("⚠️ For entertainment only. Not financial advice.")
