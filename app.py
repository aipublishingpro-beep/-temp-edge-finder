import streamlit as st
import requests
from datetime import datetime
import pytz
import re

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
    st.caption("v3.3 | High & Low Temps")

# ========== CITIES ==========
CITIES = {
    "NYC": {"name": "New York (Central Park)", "tz": "America/New_York", 
            "high_ticker": "KXHIGHNY", "low_ticker": "KXLOWTNYC", "nws_station": "KNYC"},
    "Chicago": {"name": "Chicago (O'Hare)", "tz": "America/Chicago", 
                "high_ticker": "KXHIGHCHI", "low_ticker": "KXLOWTCHI", "nws_station": "KORD"},
    "LA": {"name": "Los Angeles (LAX)", "tz": "America/Los_Angeles", 
           "high_ticker": "KXHIGHLA", "low_ticker": "KXLOWTLAX", "nws_station": "KLAX"},
    "Miami": {"name": "Miami", "tz": "America/New_York", 
              "high_ticker": "KXHIGHMIA", "low_ticker": "KXLOWTMIA", "nws_station": "KMIA"},
    "Denver": {"name": "Denver", "tz": "America/Denver", 
               "high_ticker": "KXHIGHDEN", "low_ticker": "KXLOWTDEN", "nws_station": "KDEN"},
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
            display = txt
            tl = txt.lower()
            
            # Format 1: "47° to 48°" or "to" style
            if " to " in tl and "below" not in tl and "above" not in tl:
                try:
                    p = txt.replace('°','').lower().split('to')
                    low = int(''.join(filter(str.isdigit, p[0])))
                    high = int(''.join(filter(str.isdigit, p[1])))
                    mid = (low + high) / 2
                    display = f"{low}° to {high}°"
                except: mid = 45
            # Format 2: "40° or below" or "<19°"
            elif "below" in tl or "<" in txt:
                try: 
                    num = int(''.join(filter(str.isdigit, txt.split('°')[0].split('<')[-1])))
                    # "<19°" means less than 19, so "18° or below"
                    if "<" in txt:
                        mid = num - 1
                        display = f"{num - 1}° or below"
                    else:
                        mid = num
                        display = f"{num}° or below"
                except: mid = 30
            # Format 3: "49° or above" or ">26°"  
            elif "above" in tl or ">" in txt:
                try: 
                    num = int(''.join(filter(str.isdigit, txt.split('°')[0].split('>')[-1])))
                    # ">26°" means greater than 26, so "27° or above"
                    if ">" in txt:
                        mid = num + 1
                        display = f"{num + 1}° or above"
                    else:
                        mid = num
                        display = f"{num}° or above"
                except: mid = 60
            # Format 4: "25-26°" range style
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
    buy_bracket = max(brackets, key=lambda b: b['yes'])
    return buy_bracket['mid']

def get_buy_bracket(brackets):
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
st.caption(f"v3.3 | {now_et.strftime('%I:%M %p ET')}")

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

# ========== CITY SELECTION ==========
city = st.selectbox("City", list(CITIES.keys()), format_func=lambda x: CITIES[x]['name'])
cfg = CITIES[city]

# Fetch both high and low brackets
high_brackets = fetch_kalshi_brackets(cfg['high_ticker'])
low_brackets = fetch_kalshi_brackets(cfg['low_ticker'])
nws_temp = fetch_nws_temp(cfg['nws_station'])

# ========== CURRENT NWS TEMP ==========
st.subheader("📡 NWS CURRENT TEMP")
if nws_temp:
    st.markdown(f"# {nws_temp}°F")
    st.caption("Current reading from official settlement source")
else:
    st.warning("NWS data unavailable")

st.divider()

# ========== TWO COLUMN LAYOUT: HIGH & LOW ==========
col_high, col_low = st.columns(2)

# ========== HIGH TEMP COLUMN ==========
with col_high:
    st.subheader("🔥 HIGH TEMP FORECAST")
    
    if high_brackets:
        high_forecast = calc_market_forecast(high_brackets)
        high_buy = get_buy_bracket(high_brackets)
        
        if high_forecast:
            st.markdown(f"# {high_forecast}°F")
            st.caption("Predicted high temperature")
            
            if high_buy:
                if high_buy['yes'] <= 85:
                    st.success(f"→ BUY YES: **{high_buy['range']}** @ {high_buy['yes']:.0f}¢")
                else:
                    st.warning(f"⚠️ No edge — {high_buy['range']} @ {high_buy['yes']:.0f}¢")
        
        st.markdown("**All High Temp Brackets:**")
        for b in high_brackets:
            is_buy = high_buy and b['range'] == high_buy['range']
            if is_buy:
                st.markdown(
                    f"""<div style="background-color: #FF8C00; padding: 8px; border-radius: 6px; margin: 4px 0;">
                    <span style="color: white; font-weight: bold;">🎯 {b['range']}</span><br>
                    <span style="color: white;">YES {b['yes']:.0f}¢ | NO {100-b['yes']:.0f}¢</span>
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.write(f"{b['range']} — YES {b['yes']:.0f}¢ | NO {100-b['yes']:.0f}¢")
    else:
        st.error("❌ No high temp data available")

# ========== LOW TEMP COLUMN ==========
with col_low:
    st.subheader("❄️ LOW TEMP FORECAST")
    
    if low_brackets:
        low_forecast = calc_market_forecast(low_brackets)
        low_buy = get_buy_bracket(low_brackets)
        
        if low_forecast:
            st.markdown(f"# {low_forecast}°F")
            st.caption("Predicted low temperature")
            
            if low_buy:
                if low_buy['yes'] <= 85:
                    st.success(f"→ BUY YES: **{low_buy['range']}** @ {low_buy['yes']:.0f}¢")
                else:
                    st.warning(f"⚠️ No edge — {low_buy['range']} @ {low_buy['yes']:.0f}¢")
        
        st.markdown("**All Low Temp Brackets:**")
        for b in low_brackets:
            is_buy = low_buy and b['range'] == low_buy['range']
            if is_buy:
                st.markdown(
                    f"""<div style="background-color: #FF8C00; padding: 8px; border-radius: 6px; margin: 4px 0;">
                    <span style="color: white; font-weight: bold;">🎯 {b['range']}</span><br>
                    <span style="color: white;">YES {b['yes']:.0f}¢ | NO {100-b['yes']:.0f}¢</span>
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.write(f"{b['range']} — YES {b['yes']:.0f}¢ | NO {100-b['yes']:.0f}¢")
    else:
        st.error("❌ No low temp data available")

st.divider()

# ========== QUICK GUIDE ==========
with st.expander("📖 How to Use"):
    st.markdown("""
    **Your Strategy:**
    1. Check both HIGH and LOW forecasts
    2. Buy YES on orange-highlighted brackets between **8-10 AM**
    3. Price rises as day confirms
    4. Sell for profit or hold to settlement
    
    **Settlement:** NWS Climatological Report (official)
    
    **Best Entry:** 8-10 AM — forecast stable, prices cheap
    """)

st.caption("⚠️ Not financial advice")
