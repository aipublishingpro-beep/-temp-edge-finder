import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Temp Quick Trade", page_icon="🌡️", layout="wide")

# ========== SIDEBAR LEGEND ==========
with st.sidebar:
    st.header("⏰ BEST TIME TO BUY")
    st.markdown("""
    🟡 **6-8 AM** — Risky, forecast forming
    
    🟢 **8-10 AM** — BEST TIME!
    
    🔵 **10-12 PM** — Good, prices rising
    
    🔴 **12 PM+** — Late, prices baked in
    """)
    
    st.divider()
    
    st.header("📖 STRATEGY")
    st.markdown("""
    1. Check **Market Forecast**
    2. **BUY YES** on that bracket
    3. Optional: **BUY NO** on bracket above
    4. Sell for profit or hold
    """)
    
    st.divider()
    
    st.header("💡 HEDGE PLAY")
    st.markdown("""
    If forecast = 52°F:
    - **YES 51-52** → wins if 51-52
    - **NO 53+** → wins if ≤52
    
    Both win if temp = 51-52°F!
    """)
    
    st.divider()
    st.caption("v3.1 | Quick Trade")

# ========== CITIES ==========
CITIES = {
    "NYC": {"name": "New York (Central Park)", "tz": "America/New_York", "series_ticker": "KXHIGHNY", "nws_station": "KNYC"},
    "Chicago": {"name": "Chicago (O'Hare)", "tz": "America/Chicago", "series_ticker": "KXHIGHCHI", "nws_station": "KORD"},
    "LA": {"name": "Los Angeles (LAX)", "tz": "America/Los_Angeles", "series_ticker": "KXHIGHLA", "nws_station": "KLAX"},
    "Miami": {"name": "Miami", "tz": "America/New_York", "series_ticker": "KXHIGHMIA", "nws_station": "KMIA"},
    "Denver": {"name": "Denver", "tz": "America/Denver", "series_ticker": "KXHIGHDEN", "nws_station": "KDEN"},
}

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
        if b['mid'] and 5 <= b['yes'] <= 95:
            ws += b['mid'] * b['yes']
            tp += b['yes']
    return round(ws / tp, 1) if tp > 0 else None

def get_buy_bracket(brackets):
    """Find the bracket with the highest YES price (market's pick)"""
    if not brackets:
        return None
    return max(brackets, key=lambda b: b['yes'])

# ========== FETCH NWS CURRENT TEMP ==========
def fetch_nws_temp(station):
    url = f"https://api.weather.gov/stations/{station}/observations/latest"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempQuick/3.0"}, timeout=10)
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
st.caption(f"v3.1 | {now_et.strftime('%I:%M %p ET')}")

# ========== TIMING INDICATOR ==========
if 6 <= hour < 8:
    st.warning("⏳ **6-8 AM** — Forecast forming. Prices cheapest but risky.")
elif 8 <= hour < 10:
    st.success("🎯 **8-10 AM** — BEST TIME TO BUY. Forecast stable, prices still cheap!")
elif 10 <= hour < 12:
    st.info("📈 **10 AM-12 PM** — Good entry. Forecast locked, prices rising.")
else:
    st.error("⚠️ **After 12 PM** — Late entry. Prices already reflect outcome.")

st.divider()

city = st.selectbox("City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
cfg = CITIES[city]

brackets = fetch_kalshi_brackets(cfg['series_ticker'])
nws_temp = fetch_nws_temp(cfg['nws_station'])

# ========== MARKET FORECAST (THE HIDDEN NUMBER) ==========
st.subheader("🎯 MARKET FORECAST")

if brackets:
    forecast = calc_market_forecast(brackets)
    buy_bracket = get_buy_bracket(brackets)
    
    if forecast:
        st.markdown(f"# {forecast}°F")
        st.caption("This is what Kalshi hides until you buy a contract")
        
        if buy_bracket:
            st.success(f"### → BUY YES on: **{buy_bracket['range']}** @ {buy_bracket['yes']:.0f}¢")
    else:
        st.warning("Could not calculate forecast")
else:
    st.error("❌ No Kalshi data available")

st.divider()

# ========== CURRENT NWS TEMP (SETTLEMENT SOURCE) ==========
st.subheader("📡 NWS TEMP (Settlement Source)")

if nws_temp:
    st.markdown(f"# {nws_temp}°F")
    st.caption("Official source for settlement")
else:
    st.warning("NWS data unavailable")

st.divider()

# ========== ALL BRACKETS ==========
st.subheader("📊 All Brackets")

if brackets:
    forecast = calc_market_forecast(brackets)
    buy_bracket = get_buy_bracket(brackets)
    
    for b in brackets:
        is_buy = buy_bracket and b['range'] == buy_bracket['range']
        
        if is_buy:
            st.markdown(
                f"""<div style="background-color: #FF8C00; padding: 10px; border-radius: 8px; margin: 5px 0;">
                <span style="color: white; font-weight: bold;">{b['range']} 🎯</span>
                <span style="color: white; font-weight: bold; margin-left: 40px;">YES {b['yes']:.0f}¢</span>
                <span style="color: white; margin-left: 40px;">NO {100-b['yes']:.0f}¢</span>
                </div>""",
                unsafe_allow_html=True
            )
        else:
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(b['range'])
            col2.write(f"YES {b['yes']:.0f}¢")
            col3.write(f"NO {100-b['yes']:.0f}¢")
else:
    st.warning("No brackets available")

st.divider()

# ========== QUICK GUIDE ==========
with st.expander("📖 How to Use"):
    st.markdown("""
    **Your Strategy:**
    1. Check MARKET FORECAST (free intel Kalshi hides)
    2. Buy YES on that bracket between **8-10 AM**
    3. Price rises as day confirms
    4. Sell for profit or hold to settlement
    
    **Settlement:** NWS Climatological Report (official)
    
    **Best Entry:** 8-10 AM — forecast stable, prices cheap
    """)

st.caption("⚠️ Not financial advice")
