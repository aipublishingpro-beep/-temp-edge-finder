import streamlit as st
import requests
from datetime import datetime
import pytz
import re

st.set_page_config(page_title="Temp Quick Trade", page_icon="🌡️", layout="wide")

# ========== SIDEBAR LEGEND ==========
with st.sidebar:
    st.header("🎯 EDGE COLORS")
    st.markdown("""
    🟢 **GREEN** — NWS ≥2° higher than market
    → Buy YES on higher brackets
    
    🔴 **RED** — NWS ≥2° lower than market
    → Buy YES on lower brackets
    
    ⚪ **GRAY** — Within ±2°
    → No clear edge
    """)
    
    st.divider()
    
    st.header("⏰ BEST TIME TO BUY")
    st.markdown("""
    🟡 **6-8 AM** — Risky, forecast forming
    🟢 **8-10 AM** — BEST TIME!
    🔵 **10-12 PM** — Good, prices rising
    🔴 **12 PM+** — Late, prices baked in
    """)
    
    st.divider()
    st.caption("v4.0 | NWS Edge Finder")

# ========== CITIES ==========
CITIES = {
    "NYC": {"name": "New York (Central Park)", "tz": "America/New_York", 
            "high_ticker": "KXHIGHNY", "low_ticker": "KXLOWTNYC", "nws_station": "KNYC",
            "nws_office": "OKX", "grid_x": 33, "grid_y": 37},
    "Chicago": {"name": "Chicago (O'Hare)", "tz": "America/Chicago", 
                "high_ticker": "KXHIGHCHI", "low_ticker": "KXLOWTCHI", "nws_station": "KORD",
                "nws_office": "LOT", "grid_x": 65, "grid_y": 76},
    "LA": {"name": "Los Angeles (LAX)", "tz": "America/Los_Angeles", 
           "high_ticker": "KXHIGHLA", "low_ticker": "KXLOWTLAX", "nws_station": "KLAX",
           "nws_office": "LOX", "grid_x": 149, "grid_y": 48},
    "Miami": {"name": "Miami", "tz": "America/New_York", 
              "high_ticker": "KXHIGHMIA", "low_ticker": "KXLOWTMIA", "nws_station": "KMIA",
              "nws_office": "MFL", "grid_x": 109, "grid_y": 50},
    "Denver": {"name": "Denver", "tz": "America/Denver", 
               "high_ticker": "KXHIGHDEN", "low_ticker": "KXLOWTDEN", "nws_station": "KDEN",
               "nws_office": "BOU", "grid_x": 62, "grid_y": 60},
}

# ========== FETCH NWS FORECAST (HIGH/LOW) ==========
def fetch_nws_forecast(office, grid_x, grid_y):
    """Fetch NWS forecast for high and low temps"""
    url = f"https://api.weather.gov/gridpoints/{office}/{grid_x},{grid_y}/forecast"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempQuick/4.0"}, timeout=10)
        if resp.status_code == 200:
            periods = resp.json().get("properties", {}).get("periods", [])
            if periods:
                # Find today's forecast
                today_high = None
                today_low = None
                
                for period in periods[:4]:  # Check first 4 periods
                    name = period.get("name", "").lower()
                    temp = period.get("temperature")
                    is_day = period.get("isDaytime", True)
                    
                    if is_day and today_high is None:
                        today_high = temp
                    elif not is_day and today_low is None:
                        today_low = temp
                
                return {"high": today_high, "low": today_low}
    except Exception as e:
        pass
    return {"high": None, "low": None}

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
    """Calculate weighted average forecast from market brackets"""
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

def get_edge_bracket(brackets, nws_temp, market_temp):
    """Find the bracket to buy based on NWS vs Market gap"""
    if not brackets or nws_temp is None or market_temp is None:
        return None, None
    
    gap = nws_temp - market_temp
    
    # Find bracket containing NWS forecast
    best_bracket = None
    for b in brackets:
        mid = b['mid']
        if mid is None:
            continue
        range_text = b['range'].lower()
        
        # Check if NWS temp falls in this bracket
        if "or above" in range_text:
            if nws_temp >= mid - 0.5:
                best_bracket = b
        elif "or below" in range_text:
            if nws_temp <= mid + 0.5:
                best_bracket = b
        else:
            # Regular bracket - check if within range
            if abs(nws_temp - mid) <= 1.5:
                best_bracket = b
    
    return best_bracket, gap

# ========== FETCH NWS CURRENT TEMP ==========
def fetch_nws_temp(station):
    url = f"https://api.weather.gov/stations/{station}/observations/latest"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempQuick/4.0"}, timeout=10)
        if resp.status_code == 200:
            p = resp.json().get("properties", {})
            tc = p.get("temperature", {}).get("value")
            if tc is not None:
                return round(tc * 9/5 + 32, 1)
    except:
        pass
    return None

# ========== MAIN ==========
now_et = datetime.now(pytz.timezone('US/Eastern'))
hour = now_et.hour

st.title("🌡️ TEMP QUICK TRADE")
st.caption(f"v4.0 — NWS Edge Finder | {now_et.strftime('%I:%M %p ET')}")

# Timing indicator
if 6 <= hour < 8:
    st.warning("⏳ **6-8 AM** — Forecast forming. Prices cheapest but risky.")
elif 8 <= hour < 10:
    st.success("🎯 **8-10 AM** — BEST TIME TO BUY. Forecast stable, prices still cheap!")
elif 10 <= hour < 12:
    st.info("📈 **10 AM-12 PM** — Good entry. Forecast locked, prices rising.")
else:
    st.error("⚠️ **After 12 PM** — Late entry. Prices already reflect outcome.")

st.divider()

# City selection
city = st.selectbox("City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
cfg = CITIES[city]

# Fetch all data
high_brackets = fetch_kalshi_brackets(cfg['high_ticker'])
low_brackets = fetch_kalshi_brackets(cfg['low_ticker'])
nws_forecast = fetch_nws_forecast(cfg['nws_office'], cfg['grid_x'], cfg['grid_y'])
nws_current = fetch_nws_temp(cfg['nws_station'])

# Current temp display
st.subheader("📡 CURRENT TEMP")
if nws_current:
    st.markdown(f"### {nws_current}°F")
else:
    st.warning("NWS current temp unavailable")

st.divider()

# ========== TWO COLUMN LAYOUT ==========
col_high, col_low = st.columns(2)

# ========== HIGH TEMP ==========
with col_high:
    st.subheader("🔥 HIGH TEMP")
    
    nws_high = nws_forecast.get("high")
    market_high = calc_market_forecast(high_brackets) if high_brackets else None
    
    # Display comparison
    c1, c2 = st.columns(2)
    with c1:
        st.metric("NWS Forecast", f"{nws_high}°F" if nws_high else "—")
    with c2:
        st.metric("Market Implied", f"{market_high}°F" if market_high else "—")
    
    # Calculate edge and display
    if nws_high and market_high:
        gap = nws_high - market_high
        
        if gap >= 2:
            st.markdown(f"""
            <div style="background-color: #155724; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <span style="color: #d4edda; font-size: 24px; font-weight: bold;">🟢 +{gap:.1f}° EDGE</span><br>
                <span style="color: #d4edda;">NWS higher than market → BUY HIGHER BRACKETS</span>
            </div>""", unsafe_allow_html=True)
        elif gap <= -2:
            st.markdown(f"""
            <div style="background-color: #721c24; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <span style="color: #f8d7da; font-size: 24px; font-weight: bold;">🔴 {gap:.1f}° EDGE</span><br>
                <span style="color: #f8d7da;">NWS lower than market → BUY LOWER BRACKETS</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color: #383d41; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <span style="color: #e2e3e5; font-size: 24px; font-weight: bold;">⚪ {gap:+.1f}° NO EDGE</span><br>
                <span style="color: #e2e3e5;">Market aligned with NWS forecast</span>
            </div>""", unsafe_allow_html=True)
    
    # Show brackets
    if high_brackets:
        with st.expander("View All Brackets"):
            for b in high_brackets:
                # Highlight bracket containing NWS forecast
                if nws_high and b['mid']:
                    in_bracket = abs(nws_high - b['mid']) <= 1.5
                    if "above" in b['range'].lower() and nws_high >= b['mid'] - 0.5:
                        in_bracket = True
                    if "below" in b['range'].lower() and nws_high <= b['mid'] + 0.5:
                        in_bracket = True
                else:
                    in_bracket = False
                
                if in_bracket:
                    st.markdown(f"**🎯 {b['range']}** — YES {b['yes']:.0f}¢")
                else:
                    st.write(f"{b['range']} — YES {b['yes']:.0f}¢")
    else:
        st.error("No high temp data")

# ========== LOW TEMP ==========
with col_low:
    st.subheader("❄️ LOW TEMP")
    
    nws_low = nws_forecast.get("low")
    market_low = calc_market_forecast(low_brackets) if low_brackets else None
    
    # Display comparison
    c1, c2 = st.columns(2)
    with c1:
        st.metric("NWS Forecast", f"{nws_low}°F" if nws_low else "—")
    with c2:
        st.metric("Market Implied", f"{market_low}°F" if market_low else "—")
    
    # Calculate edge and display
    if nws_low and market_low:
        gap = nws_low - market_low
        
        if gap >= 2:
            st.markdown(f"""
            <div style="background-color: #155724; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <span style="color: #d4edda; font-size: 24px; font-weight: bold;">🟢 +{gap:.1f}° EDGE</span><br>
                <span style="color: #d4edda;">NWS higher than market → BUY HIGHER BRACKETS</span>
            </div>""", unsafe_allow_html=True)
        elif gap <= -2:
            st.markdown(f"""
            <div style="background-color: #721c24; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <span style="color: #f8d7da; font-size: 24px; font-weight: bold;">🔴 {gap:.1f}° EDGE</span><br>
                <span style="color: #f8d7da;">NWS lower than market → BUY LOWER BRACKETS</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color: #383d41; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <span style="color: #e2e3e5; font-size: 24px; font-weight: bold;">⚪ {gap:+.1f}° NO EDGE</span><br>
                <span style="color: #e2e3e5;">Market aligned with NWS forecast</span>
            </div>""", unsafe_allow_html=True)
    
    # Show brackets
    if low_brackets:
        with st.expander("View All Brackets"):
            for b in low_brackets:
                if nws_low and b['mid']:
                    in_bracket = abs(nws_low - b['mid']) <= 1.5
                    if "above" in b['range'].lower() and nws_low >= b['mid'] - 0.5:
                        in_bracket = True
                    if "below" in b['range'].lower() and nws_low <= b['mid'] + 0.5:
                        in_bracket = True
                else:
                    in_bracket = False
                
                if in_bracket:
                    st.markdown(f"**🎯 {b['range']}** — YES {b['yes']:.0f}¢")
                else:
                    st.write(f"{b['range']} — YES {b['yes']:.0f}¢")
    else:
        st.error("No low temp data")

st.divider()

# Quick guide
with st.expander("📖 How This Works"):
    st.markdown("""
    **Edge = NWS Forecast vs Market Implied Price**
    
    - **NWS Forecast**: What the settlement source predicts
    - **Market Implied**: Probability-weighted average from Kalshi
    - **Gap ≥2°**: Potential mispricing opportunity
    
    🟢 **GREEN**: NWS says higher → buy higher brackets
    🔴 **RED**: NWS says lower → buy lower brackets
    ⚪ **GRAY**: No significant gap → no clear edge
    
    **Settlement**: NWS Climatological Report (official)
    """)

st.caption("⚠️ Not financial advice")
