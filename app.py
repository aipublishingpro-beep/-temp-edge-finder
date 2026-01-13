import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Temp Edge Finder", page_icon="🌡️", layout="wide")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("📖 LEGEND")
    st.markdown("""
    **Edge = 2°F+ difference**
    
    **Your pred LOWER than market:**
    - BUY YES on YOUR bracket
    - BUY NO on market's bracket
    
    **Your pred HIGHER than market:**
    - BUY YES on YOUR bracket  
    - BUY NO on lower brackets
    """)
    st.divider()
    st.caption("v2.3 | Morning Data Only")

# ========== CITIES ==========
CITIES = {
    "NYC": {"name": "New York (Central Park)", "tz": "America/New_York", "series_ticker": "KXHIGHNY", "nws_station": "KNYC"},
    "Chicago": {"name": "Chicago (O'Hare)", "tz": "America/Chicago", "series_ticker": "KXHIGHCHI", "nws_station": "KORD"},
    "LA": {"name": "Los Angeles (LAX)", "tz": "America/Los_Angeles", "series_ticker": "KXHIGHLA", "nws_station": "KLAX"},
    "Miami": {"name": "Miami", "tz": "America/New_York", "series_ticker": "KXHIGHMIA", "nws_station": "KMIA"},
    "Denver": {"name": "Denver", "tz": "America/Denver", "series_ticker": "KXHIGHDEN", "nws_station": "KDEN"},
}

# ========== FUNCTIONS ==========
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
            tl = txt.lower()
            
            if "below" in tl:
                try: mid = int(''.join(filter(str.isdigit, txt.split('°')[0]))) - 1
                except: mid = 30
            elif "above" in tl:
                try: mid = int(''.join(filter(str.isdigit, txt.split('°')[0]))) + 1
                except: mid = 60
            elif "to" in tl:
                try:
                    p = txt.replace('°','').lower().split('to')
                    mid = (int(''.join(filter(str.isdigit, p[0]))) + int(''.join(filter(str.isdigit, p[1])))) / 2
                except: mid = 45
            
            yb, ya = m.get("yes_bid", 0), m.get("yes_ask", 0)
            yp = (yb + ya) / 2 if yb and ya else ya or yb or 0
            brackets.append({"range": txt, "mid": mid, "yes": yp})
        
        brackets.sort(key=lambda x: x['mid'] or 0)
        return brackets
    except:
        return None

def calc_market_forecast(brackets):
    if not brackets:
        return None
    ws, tp = 0, 0
    for b in brackets:
        if b['mid'] and b['yes']:
            ws += b['mid'] * b['yes']
            tp += b['yes']
    return round(ws / tp, 1) if tp > 0 else None

def fetch_nws_history(station):
    url = f"https://api.weather.gov/stations/{station}/observations"
    try:
        resp = requests.get(url, headers={"User-Agent": "Temp/2.3"}, timeout=15)
        if resp.status_code != 200:
            return None
        readings = []
        for f in resp.json().get("features", [])[:24]:
            p = f.get("properties", {})
            tc = p.get("temperature", {}).get("value")
            if tc is not None:
                readings.append({"time": p.get("timestamp", ""), "temp": tc * 9/5 + 32})
        return readings
    except:
        return None

def fetch_weather(station):
    url = f"https://api.weather.gov/stations/{station}/observations/latest"
    try:
        resp = requests.get(url, headers={"User-Agent": "Temp/2.3"}, timeout=10)
        if resp.status_code == 200:
            p = resp.json().get("properties", {})
            tc = p.get("temperature", {}).get("value")
            dc = p.get("dewpoint", {}).get("value")
            ws = p.get("windSpeed", {}).get("value")
            wd = p.get("windDirection", {}).get("value")
            desc = p.get("textDescription", "")
            dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            wn = dirs[round(wd/22.5)%16] if wd else ""
            return {
                "temp": tc * 9/5 + 32 if tc else None,
                "dew": dc * 9/5 + 32 if dc else None,
                "wind": f"{ws*2.237:.0f} mph {wn}" if ws else None,
                "desc": desc
            }
    except:
        pass
    return None

def predict_high(readings, tz):
    if not readings or len(readings) < 2:
        return None, None, []
    
    local_tz = pytz.timezone(tz)
    now = datetime.now(local_tz)
    today = now.date()
    
    todays = []
    for r in readings:
        try:
            ts = datetime.fromisoformat(r['time'].replace('Z','+00:00')).astimezone(local_tz)
            if ts.date() == today:
                todays.append({"hr": ts.hour + ts.minute/60, "temp": r['temp'], "t": ts.strftime("%I:%M %p")})
        except:
            continue
    
    if len(todays) < 2:
        return None, None, ["Need more data"]
    
    todays.sort(key=lambda x: x['hr'])
    
    # MORNING ONLY 6AM-12PM
    am = [r for r in todays if 6 <= r['hr'] <= 12]
    
    info = ["**Morning Readings:**"]
    for r in reversed(am):
        info.append(f"  {r['t']}: {r['temp']:.1f}°F")
    
    if len(am) < 2:
        info.append("⏳ Need morning data")
        return None, None, info
    
    start, end = am[0], am[-1]
    hrs = end['hr'] - start['hr']
    rate = (end['temp'] - start['temp']) / hrs if hrs > 0 else 1.5
    
    info.append(f"**Rate:** {rate:.2f}°F/hr")
    
    to_peak = max(0, 14.5 - end['hr'])
    factor = 0.8 if end['hr'] < 11 else 0.6 if end['hr'] < 12 else 0.5
    remaining = rate * to_peak * factor
    raw = end['temp'] + remaining
    
    # +1°F bias
    low = raw + 1
    high = low + 1
    
    info.append(f"**Projection:** {low:.0f}-{high:.0f}°F")
    
    return low, high, info

# ========== MAIN ==========
now = datetime.now(pytz.timezone('US/Eastern'))
st.title("🌡️ TEMP EDGE FINDER")
st.caption(f"{now.strftime('%I:%M %p ET')} | v2.3")

city = st.selectbox("City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
cfg = CITIES[city]

brackets = fetch_kalshi_brackets(cfg['series_ticker'])
weather = fetch_weather(cfg['nws_station'])
history = fetch_nws_history(cfg['nws_station'])

st.divider()

# ========== WEATHER ==========
st.subheader("🌤️ Current")
if weather:
    c1, c2, c3 = st.columns(3)
    c1.metric("Temp", f"{weather['temp']:.1f}°F" if weather['temp'] else "—")
    c2.metric("Wind", weather['wind'] or "—")
    c3.metric("Conditions", weather['desc'] or "—")

st.divider()

# ========== PREDICTION ==========
st.subheader("🎯 YOUR PREDICTION")

if history:
    pred_low, pred_high, info = predict_high(history, cfg['tz'])
    
    if pred_low and pred_high:
        pred_mid = (pred_low + pred_high) / 2
        
        # Find which Kalshi bracket YOUR prediction falls into
        your_bracket = None
        if brackets:
            for b in brackets:
                if b['mid']:
                    # Check if prediction midpoint is within this bracket range
                    if b['mid'] - 1 <= pred_mid <= b['mid'] + 1:
                        your_bracket = b
                        break
        
        # Display prediction with ACTUAL bracket
        st.markdown(f"### 🎯 {pred_low:.0f}-{pred_high:.0f}°F")
        
        if your_bracket:
            st.success(f"**→ BUY YES on: {your_bracket['range']}** (currently {your_bracket['yes']:.0f}¢)")
        
        # Compare to market
        if brackets:
            mkt = calc_market_forecast(brackets)
            if mkt:
                diff = pred_mid - mkt
                
                st.markdown(f"**Market Forecast:** {mkt:.1f}°F | **Diff:** {diff:+.1f}°F")
                
                # Find market's bracket
                mkt_bracket = None
                for b in brackets:
                    if b['mid'] and b['mid'] - 1 <= mkt <= b['mid'] + 1:
                        mkt_bracket = b
                        break
                
                if abs(diff) >= 2:
                    st.success("## 🎯 EDGE FOUND!")
                    
                    if diff < 0:
                        st.markdown("### You predict LOWER than market:")
                        st.markdown(f"✅ **BUY YES:** {your_bracket['range']} @ {your_bracket['yes']:.0f}¢" if your_bracket else "")
                        if mkt_bracket:
                            st.markdown(f"❌ **BUY NO:** {mkt_bracket['range']} @ {100-mkt_bracket['yes']:.0f}¢")
                    else:
                        st.markdown("### You predict HIGHER than market:")
                        st.markdown(f"✅ **BUY YES:** {your_bracket['range']} @ {your_bracket['yes']:.0f}¢" if your_bracket else "")
                        if mkt_bracket:
                            st.markdown(f"❌ **BUY NO:** {mkt_bracket['range']} @ {100-mkt_bracket['yes']:.0f}¢")
                else:
                    st.info("No edge — your prediction matches market (within 2°F)")
        
        with st.expander("📊 Calculation"):
            for i in info:
                st.markdown(i)
    else:
        st.warning("⏳ Need morning data (after 9 AM)")
        with st.expander("Data"):
            for i in info:
                st.markdown(i)

st.divider()

# ========== BRACKETS ==========
st.subheader("📊 Kalshi Brackets")

if brackets:
    mkt = calc_market_forecast(brackets)
    st.caption(f"Market Forecast: {mkt}°F" if mkt else "")
    
    for b in brackets:
        c1, c2, c3 = st.columns([2,1,1])
        c1.write(b['range'])
        if b['yes'] >= 90:
            c2.markdown(f"**YES {b['yes']:.0f}¢** ✅")
        else:
            c2.write(f"YES {b['yes']:.0f}¢")
        c3.write(f"NO {100-b['yes']:.0f}¢")
else:
    st.warning("No brackets found")

st.divider()
st.caption("⚠️ Not financial advice")
