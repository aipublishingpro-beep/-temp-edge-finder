import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="Temp Edge Finder", page_icon="🌡️", layout="wide")

if "temp_positions" not in st.session_state:
    st.session_state.temp_positions = []

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("📖 LEGEND")
    st.markdown("""
    **Edge Strategy:**
    - Your prediction < Market → BUY NO on upper brackets
    - Your prediction > Market → BUY NO on lower brackets
    - Within 1°F → No edge
    
    **Prediction Method:**
    1. Use 6AM-12PM readings ONLY
    2. Calculate real °F/hr rate
    3. Project to peak (2-3 PM)
    4. Add +1°F bias
    
    **Best Trading Window:**
    10 AM - 12 PM
    """)
    st.divider()
    st.caption("v2.2 | NWS Morning Data Only")

# ========== CITIES ==========
CITIES = {
    "NYC": {"name": "New York (Central Park)", "lat": 40.7829, "lon": -73.9654, "tz": "America/New_York", "series_ticker": "KXHIGHNY", "nws_station": "KNYC"},
    "Chicago": {"name": "Chicago (O'Hare)", "lat": 41.9742, "lon": -87.9073, "tz": "America/Chicago", "series_ticker": "KXHIGHCHI", "nws_station": "KORD"},
    "LA": {"name": "Los Angeles (LAX)", "lat": 33.9425, "lon": -118.4081, "tz": "America/Los_Angeles", "series_ticker": "KXHIGHLA", "nws_station": "KLAX"},
    "Miami": {"name": "Miami", "lat": 25.7617, "lon": -80.1918, "tz": "America/New_York", "series_ticker": "KXHIGHMIA", "nws_station": "KMIA"},
    "Denver": {"name": "Denver", "lat": 39.8561, "lon": -104.6737, "tz": "America/Denver", "series_ticker": "KXHIGHDEN", "nws_station": "KDEN"},
    "Austin": {"name": "Austin", "lat": 30.1944, "lon": -97.6700, "tz": "America/Chicago", "series_ticker": "KXHIGHAUS", "nws_station": "KAUS"}
}

# ========== FUNCTIONS ==========
def fetch_kalshi_temp_brackets(series_ticker):
    url = f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series_ticker}&status=open"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None, f"API {resp.status_code}"
        data = resp.json()
        markets = data.get("markets", [])
        if not markets:
            return None, "No markets"
        
        today_et = datetime.now(pytz.timezone('US/Eastern'))
        today_str1 = today_et.strftime('%y%b%d').upper()
        today_str2 = today_et.strftime('%b-%d').upper()
        today_str3 = today_et.strftime('%Y-%m-%d')
        
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
            return None, "No markets today"
        
        brackets = []
        for market in today_markets:
            range_text = market.get("subtitle", "") or market.get("title", "")
            midpoint = None
            rl = range_text.lower()
            
            if "or below" in rl or "under" in rl:
                try:
                    num = int(''.join(filter(str.isdigit, range_text.split('°')[0].split()[-1])))
                    midpoint = num - 1
                except:
                    midpoint = 30
            elif "or above" in rl or "over" in rl:
                try:
                    num = int(''.join(filter(str.isdigit, range_text.split('°')[0].split()[-1])))
                    midpoint = num + 1
                except:
                    midpoint = 50
            elif "to" in rl or "-" in range_text:
                try:
                    parts = range_text.replace('°', '').lower().split('to') if "to" in rl else range_text.replace('°', '').split('-')
                    midpoint = (int(''.join(filter(str.isdigit, parts[0]))) + int(''.join(filter(str.isdigit, parts[1])))) / 2
                except:
                    midpoint = 40
            
            yes_bid = market.get("yes_bid", 0)
            yes_ask = market.get("yes_ask", 0)
            brackets.append({
                "range": range_text,
                "midpoint": midpoint,
                "yes_price": (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else yes_ask or yes_bid or 0
            })
        
        brackets.sort(key=lambda x: x['midpoint'] if x['midpoint'] else 0)
        return brackets, None
    except Exception as e:
        return None, str(e)

def calc_market_forecast(brackets):
    if not brackets:
        return None
    weighted_sum = 0
    total_prob = 0
    for b in brackets:
        if b['midpoint'] and b['yes_price']:
            weighted_sum += b['midpoint'] * b['yes_price']
            total_prob += b['yes_price']
    return round(weighted_sum / total_prob, 1) if total_prob > 0 else None

def fetch_nws_history(station_id="KNYC"):
    url = f"https://api.weather.gov/stations/{station_id}/observations"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempEdge/2.2"}, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        readings = []
        for f in data.get("features", [])[:24]:
            props = f.get("properties", {})
            temp_c = props.get("temperature", {}).get("value")
            if temp_c is not None:
                readings.append({"time": props.get("timestamp", ""), "temp": (temp_c * 9/5) + 32})
        return readings
    except:
        return None

def fetch_current_weather(station_id="KNYC"):
    url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempEdge/2.2"}, timeout=10)
        if resp.status_code == 200:
            props = resp.json().get("properties", {})
            temp_c = props.get("temperature", {}).get("value")
            dew_c = props.get("dewpoint", {}).get("value")
            wind_mps = props.get("windSpeed", {}).get("value")
            wind_dir = props.get("windDirection", {}).get("value")
            desc = props.get("textDescription", "")
            
            cloud = 50
            if "clear" in desc.lower() or "sunny" in desc.lower():
                cloud = 10
            elif "partly" in desc.lower():
                cloud = 40
            elif "mostly cloudy" in desc.lower():
                cloud = 70
            elif "cloudy" in desc.lower() or "overcast" in desc.lower():
                cloud = 90
            
            dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            wind_name = dirs[round(wind_dir / 22.5) % 16] if wind_dir else ""
            
            return {
                "temp": (temp_c * 9/5) + 32 if temp_c else None,
                "dewpoint": (dew_c * 9/5) + 32 if dew_c else None,
                "wind": f"{wind_mps * 2.237:.0f} mph {wind_name}" if wind_mps else None,
                "clouds": cloud,
                "desc": desc,
                "source": "NWS"
            }
    except:
        pass
    return None

def calc_heating_rate_and_predict(readings, city_tz):
    """MORNING DATA ONLY (6AM-12PM) + 1°F bias"""
    if not readings or len(readings) < 2:
        return None, None, []
    
    local_tz = pytz.timezone(city_tz)
    now = datetime.now(local_tz)
    today_date = now.date()
    
    today_readings = []
    for r in readings:
        try:
            ts = datetime.fromisoformat(r['time'].replace('Z', '+00:00')).astimezone(local_tz)
            if ts.date() == today_date:
                today_readings.append({"hour": ts.hour + ts.minute/60, "temp": r['temp'], "time_str": ts.strftime("%I:%M %p")})
        except:
            continue
    
    if len(today_readings) < 2:
        return None, None, ["Need more readings"]
    
    today_readings.sort(key=lambda x: x['hour'])
    
    # MORNING ONLY: 6 AM - 12 PM
    morning = [r for r in today_readings if 6 <= r['hour'] <= 12]
    
    factors = ["**Morning Readings (6AM-12PM):**"]
    for r in morning:
        factors.append(f"  {r['time_str']}: {r['temp']:.1f}°F")
    
    if len(morning) < 2:
        factors.append("")
        factors.append("⏳ Need more morning data")
        return None, None, factors
    
    start = morning[0]
    end = morning[-1]
    
    hours = end['hour'] - start['hour']
    rise = end['temp'] - start['temp']
    rate = rise / hours if hours > 0 else 1.5
    
    factors.append("")
    factors.append(f"**Rate:** {rate:.2f}°F/hr")
    
    peak_hour = 14.5
    hours_to_peak = max(0, peak_hour - end['hour'])
    
    if end['hour'] < 11:
        factor = 0.8
    elif end['hour'] < 12:
        factor = 0.6
    else:
        factor = 0.5
    
    remaining = rate * hours_to_peak * factor
    raw = end['temp'] + remaining
    
    # +1°F bias
    pred_low = raw + 1
    pred_high = pred_low + 1
    
    factors.append(f"**To peak:** {hours_to_peak:.1f}h × {factor}")
    factors.append(f"**Remaining:** +{remaining:.1f}°F")
    factors.append(f"**Raw:** {raw:.1f}°F")
    factors.append(f"**+1°F bias → {pred_low:.0f}-{pred_high:.0f}°F**")
    
    return pred_low, pred_high, factors

# ========== HEADER ==========
now = datetime.now(pytz.timezone('US/Eastern'))
st.title("🌡️ TEMP EDGE FINDER")
st.caption(f"{now.strftime('%I:%M %p ET')} | v2.2 | Morning Data Only")

# ========== CITY ==========
city = st.selectbox("City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
cfg = CITIES[city]

# ========== FETCH ==========
brackets, err = fetch_kalshi_temp_brackets(cfg['series_ticker'])
weather = fetch_current_weather(cfg['nws_station'])
history = fetch_nws_history(cfg['nws_station'])

st.divider()

# ========== CURRENT ==========
st.subheader("🌤️ Current")
if weather:
    st.success(f"📡 {weather['source']} — {weather['desc']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Temp", f"{weather['temp']:.1f}°F" if weather['temp'] else "—")
    c2.metric("Wind", weather['wind'] or "—")
    c3.metric("Dewpoint", f"{weather['dewpoint']:.1f}°F" if weather['dewpoint'] else "—")
    c4.metric("Clouds", f"{weather['clouds']}%")

st.divider()

# ========== PREDICTION ==========
st.subheader("🎯 HIGH PREDICTION")

if history:
    pred_low, pred_high, factors = calc_heating_rate_and_predict(history, cfg['tz'])
    
    if pred_low and pred_high:
        p1, p2, p3 = st.columns(3)
        p1.metric("🎯 YOUR Prediction", f"{pred_low:.0f}-{pred_high:.0f}°F")
        
        if brackets:
            mkt = calc_market_forecast(brackets)
            if mkt:
                p2.metric("Market", f"{mkt:.1f}°F")
                diff = ((pred_low + pred_high) / 2) - mkt
                
                if diff < -2:
                    p3.metric("Edge", f"{diff:+.1f}°F", "LOWER")
                    st.success(f"🎯 BUY NO on {int(mkt)}°F+ brackets!")
                elif diff > 2:
                    p3.metric("Edge", f"{diff:+.1f}°F", "HIGHER")
                    st.success(f"🎯 BUY NO on brackets below {int(pred_low)}°F!")
                else:
                    p3.metric("Edge", f"{diff:+.1f}°F", "NO EDGE")
        
        with st.expander("📊 Details"):
            for f in factors:
                st.markdown(f)
    else:
        st.info("⏳ Need morning data (after 9 AM)")
        if factors:
            with st.expander("Data"):
                for f in factors:
                    st.markdown(f)

st.divider()

# ========== BRACKETS ==========
st.subheader("📊 Kalshi Brackets")

if err:
    st.error(err)

if brackets:
    mkt = calc_market_forecast(brackets)
    st.metric("Market Forecast", f"{mkt}°F" if mkt else "—")
    
    for b in brackets:
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.write(b['range'])
        yp = b['yes_price']
        if yp >= 90:
            c2.markdown(f"<span style='color:#00ff00'>**YES {yp:.0f}¢**</span>", unsafe_allow_html=True)
        else:
            c2.write(f"YES {yp:.0f}¢")
        c3.write(f"NO {100-yp:.0f}¢")

st.divider()

# ========== NO FINDER ==========
st.subheader("💰 NO EDGE FINDER")

if brackets and history:
    pred_low, pred_high, _ = calc_heating_rate_and_predict(history, cfg['tz'])
    
    if pred_low and pred_high:
        st.markdown(f"**Your Prediction: {pred_low:.0f}-{pred_high:.0f}°F**")
        
        winner = max(brackets, key=lambda x: x['yes_price'] or 0)
        if winner['yes_price'] >= 90:
            st.error(f"🏆 {winner['range']} @ {winner['yes_price']:.0f}¢ — SETTLED")
        else:
            edges = []
            for b in brackets:
                if b['midpoint'] and 10 < b['yes_price'] < 85:
                    if b['midpoint'] < pred_low - 1:
                        dist = pred_low - b['midpoint']
                        edges.append({"b": b, "dir": "BELOW", "dist": dist})
                    elif b['midpoint'] > pred_high + 1:
                        dist = b['midpoint'] - pred_high
                        edges.append({"b": b, "dir": "ABOVE", "dist": dist})
            
            if edges:
                edges.sort(key=lambda x: -x['dist'])
                st.markdown("**Best NO Targets:**")
                for e in edges:
                    conf = "🟢 HIGH" if e['dist'] >= 4 else "🟡 MED"
                    st.markdown(f"**{e['b']['range']}** — NO @ {100-e['b']['yes_price']:.0f}¢ — {e['dir']} — {conf}")
            else:
                st.info("No edges — prediction matches market")
    else:
        st.info("⏳ Need prediction first")

st.divider()
st.caption("⚠️ Not financial advice")
