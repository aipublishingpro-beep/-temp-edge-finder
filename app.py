import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Temp Edge Finder", page_icon="🌡️", layout="wide")

# ========== SIDEBAR ==========
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
    2. Compare to **NWS Forecast**
    3. **BUY YES** on predicted bracket
    4. Hold to settlement or sell early
    """)
    
    st.divider()
    st.caption("v4.0 | High + Low Temps")

# ========== CITY CONFIGS ==========
CITIES = {
    "NYC": {
        "name": "New York (Central Park)",
        "tz": "America/New_York",
        "high_ticker": "KXHIGHNY",
        "low_ticker": "KXLOWTNYC",
        "nws_station": "KNYC",
        "nws_grid": ("OKX", 33, 37)
    },
    "Chicago": {
        "name": "Chicago (O'Hare)",
        "tz": "America/Chicago",
        "high_ticker": "KXHIGHCHI",
        "low_ticker": "KXLOWTCHI",
        "nws_station": "KORD",
        "nws_grid": ("LOT", 65, 76)
    },
    "LA": {
        "name": "Los Angeles (LAX)",
        "tz": "America/Los_Angeles",
        "high_ticker": "KXHIGHLA",
        "low_ticker": "KXLOWTLA",
        "nws_station": "KLAX",
        "nws_grid": ("LOX", 149, 48)
    },
    "Miami": {
        "name": "Miami",
        "tz": "America/New_York",
        "high_ticker": "KXHIGHMIA",
        "low_ticker": "KXLOWTMIA",
        "nws_station": "KMIA",
        "nws_grid": ("MFL", 109, 65)
    },
    "Denver": {
        "name": "Denver",
        "tz": "America/Denver",
        "high_ticker": "KXHIGHDEN",
        "low_ticker": "KXLOWTDEN",
        "nws_station": "KDEN",
        "nws_grid": ("BOU", 62, 60)
    },
    "Austin": {
        "name": "Austin",
        "tz": "America/Chicago",
        "high_ticker": "KXHIGHAUS",
        "low_ticker": "KXLOWTAUS",
        "nws_station": "KAUS",
        "nws_grid": ("EWX", 156, 91)
    }
}

# ========== FUNCTIONS ==========
def fetch_kalshi_brackets(series_ticker):
    """Fetch live Kalshi temperature brackets"""
    url = f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series_ticker}&status=open"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        markets = data.get("markets", [])
        
        if not markets:
            return None
        
        today_et = datetime.now(pytz.timezone('US/Eastern'))
        today_str1 = today_et.strftime('%y%b%d').upper()
        today_str2 = today_et.strftime('%b-%d').upper()
        today_str3 = today_et.strftime('%Y-%m-%d')
        
        today_markets = []
        for m in markets:
            event_ticker = m.get("event_ticker", "").upper()
            ticker = m.get("ticker", "").upper()
            close_time = m.get("close_time", "")
            
            if today_str1 in event_ticker or today_str1 in ticker or today_str2 in event_ticker or today_str3 in close_time[:10]:
                today_markets.append(m)
        
        if not today_markets:
            return None
        
        brackets = []
        for m in today_markets:
            # YES ASK = what you PAY to buy YES (this is what matters)
            # YES BID = what you GET if you sell YES
            yes_ask = m.get("yes_ask", 0) or 0  # Price to BUY YES
            yes_bid = m.get("yes_bid", 0) or 0  # Price to SELL YES
            yes_price = yes_ask if yes_ask > 0 else yes_bid  # Show buy price
            
            subtitle = m.get("subtitle", "") or m.get("title", "")
            ticker = m.get("ticker", "")
            event_ticker = m.get("event_ticker", "")
            # Use event page URL (shows all brackets) - more reliable
            url = f"https://kalshi.com/events/{event_ticker}" if event_ticker else f"https://kalshi.com/markets/{ticker}"
            
            # Parse temperature range
            mid = None
            range_text = subtitle
            
            if "or above" in subtitle.lower() or ">" in subtitle:
                nums = [int(s) for s in subtitle.replace('°','').replace('>','').split() if s.lstrip('-').isdigit()]
                if nums:
                    mid = nums[0] + 2.5
                    range_text = f"{nums[0]}° or above"
            elif "or below" in subtitle.lower() or "<" in subtitle:
                nums = [int(s) for s in subtitle.replace('°','').replace('<','').split() if s.lstrip('-').isdigit()]
                if nums:
                    mid = nums[0] - 2.5
                    range_text = f"{nums[0]}° or below"
            elif "to" in subtitle.lower() or "-" in subtitle:
                nums = [int(s) for s in subtitle.replace('°','').replace('to',' ').replace('-',' ').split() if s.lstrip('-').isdigit()]
                if len(nums) >= 2:
                    mid = (nums[0] + nums[1]) / 2
                    range_text = f"{nums[0]}° to {nums[1]}°"
            else:
                nums = [int(s) for s in subtitle.replace('°','').split() if s.lstrip('-').isdigit()]
                if nums:
                    mid = nums[0]
                    range_text = f"{nums[0]}°"
            
            brackets.append({
                "range": range_text,
                "yes": yes_price,
                "mid": mid,
                "ticker": ticker,
                "url": url
            })
        
        brackets.sort(key=lambda x: x['mid'] if x['mid'] else 0)
        return brackets
    
    except Exception as e:
        return None

def fetch_nws_current(station):
    """Fetch current temperature from NWS"""
    url = f"https://api.weather.gov/stations/{station}/observations/latest"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempEdgeFinder/4.0"}, timeout=10)
        if resp.status_code == 200:
            props = resp.json().get("properties", {})
            temp_c = props.get("temperature", {}).get("value")
            if temp_c is not None:
                return round(temp_c * 9/5 + 32, 1)
    except:
        pass
    return None

def fetch_nws_forecast(grid):
    """Fetch NWS forecast for high/low"""
    office, x, y = grid
    url = f"https://api.weather.gov/gridpoints/{office}/{x},{y}/forecast"
    try:
        resp = requests.get(url, headers={"User-Agent": "TempEdgeFinder/4.0"}, timeout=10)
        if resp.status_code == 200:
            periods = resp.json().get("properties", {}).get("periods", [])
            high = None
            low = None
            for p in periods[:4]:
                temp = p.get("temperature")
                is_day = p.get("isDaytime", True)
                if is_day and high is None:
                    high = temp
                elif not is_day and low is None:
                    low = temp
            return high, low
    except:
        pass
    return None, None

def calc_market_forecast(brackets):
    """Calculate market-implied forecast using weighted average"""
    if not brackets:
        return None
    
    total_prob = 0
    weighted_sum = 0
    
    for b in brackets:
        if b['mid'] is not None and b['yes'] > 0:
            prob = b['yes'] / 100
            total_prob += prob
            weighted_sum += prob * b['mid']
    
    if total_prob > 0:
        return round(weighted_sum / total_prob)
    return None

def get_buy_bracket(brackets):
    """Get the bracket with highest YES probability"""
    if not brackets:
        return None
    return max(brackets, key=lambda b: b['yes'])

def display_edge(our_temp, nws_temp, market_temp):
    """Display edge comparison"""
    if our_temp and market_temp:
        diff = our_temp - market_temp
        if abs(diff) >= 2:
            if diff > 0:
                st.success(f"📈 **+{diff}° EDGE** — Our forecast HIGHER than market")
            else:
                st.error(f"📉 **{diff}° EDGE** — Our forecast LOWER than market")
        elif abs(diff) >= 1:
            st.info(f"📊 **{diff:+}° edge** — Small opportunity")
        else:
            st.warning("⚖️ **No edge** — Market matches forecast")

# ========== MAIN APP ==========
now = datetime.now(pytz.timezone('US/Eastern'))
hour = now.hour

st.title("🌡️ TEMP EDGE FINDER")
st.caption(f"Updated: {now.strftime('%I:%M %p ET')} | v4.0")

# Trading window indicator
if hour < 8:
    st.warning("🟡 **Before 8 AM** — Forecast still forming. Prices cheapest but risky.")
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
current_temp = fetch_nws_current(cfg['nws_station'])
nws_high, nws_low = fetch_nws_forecast(cfg['nws_grid'])

# Current conditions
st.subheader("📡 CURRENT CONDITIONS")
if current_temp:
    st.markdown(f"### {current_temp}°F")
    st.caption(f"Current reading from {cfg['nws_station']}")
else:
    st.warning("NWS current temp unavailable")

st.divider()

# ========== TWO COLUMNS: HIGH & LOW ==========
col_high, col_low = st.columns(2)

# ========== HIGH TEMP COLUMN ==========
with col_high:
    st.subheader("🔥 HIGH TEMP")
    
    if high_brackets:
        market_high = calc_market_forecast(high_brackets)
        high_buy = get_buy_bracket(high_brackets)
        
        # Forecasts comparison
        c1, c2 = st.columns(2)
        with c1:
            st.metric("NWS Forecast", f"{nws_high}°F" if nws_high else "—")
        with c2:
            st.metric("Market Implied", f"{market_high}°F" if market_high else "—")
        
        # Edge display
        display_edge(nws_high, nws_high, market_high)
        
        # Buy recommendation
        if high_buy:
            if high_buy['yes'] <= 85:
                st.markdown(
                    f'<div style="background-color: #FF8C00; padding: 12px; border-radius: 8px; margin: 10px 0;">'
                    f'<span style="color: white; font-size: 18px; font-weight: bold;">🎯 BUY YES: {high_buy["range"]}</span><br>'
                    f'<span style="color: white;">YES @ {high_buy["yes"]:.0f}¢</span><br>'
                    f'<a href="{high_buy["url"]}" target="_blank" style="color: #90EE90; font-weight: bold;">→ BUY ON KALSHI</a>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.warning(f"⚠️ No edge — {high_buy['range']} @ {high_buy['yes']:.0f}¢ (too expensive)")
        
        # All brackets
        with st.expander("View All HIGH Brackets"):
            for b in high_brackets:
                is_buy = high_buy and b['range'] == high_buy['range']
                if is_buy:
                    st.markdown(f"**🎯 {b['range']}** — YES {b['yes']:.0f}¢")
                else:
                    st.write(f"{b['range']} — YES {b['yes']:.0f}¢")
    else:
        st.error("❌ No HIGH temp markets found for today")

# ========== LOW TEMP COLUMN ==========
with col_low:
    st.subheader("❄️ LOW TEMP")
    
    if low_brackets:
        market_low = calc_market_forecast(low_brackets)
        low_buy = get_buy_bracket(low_brackets)
        
        # Forecasts comparison
        c1, c2 = st.columns(2)
        with c1:
            st.metric("NWS Forecast", f"{nws_low}°F" if nws_low else "—")
        with c2:
            st.metric("Market Implied", f"{market_low}°F" if market_low else "—")
        
        # Edge display
        display_edge(nws_low, nws_low, market_low)
        
        # Buy recommendation
        if low_buy:
            if low_buy['yes'] <= 85:
                st.markdown(
                    f'<div style="background-color: #1E90FF; padding: 12px; border-radius: 8px; margin: 10px 0;">'
                    f'<span style="color: white; font-size: 18px; font-weight: bold;">🎯 BUY YES: {low_buy["range"]}</span><br>'
                    f'<span style="color: white;">YES @ {low_buy["yes"]:.0f}¢</span><br>'
                    f'<a href="{low_buy["url"]}" target="_blank" style="color: #90EE90; font-weight: bold;">→ BUY ON KALSHI</a>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.warning(f"⚠️ No edge — {low_buy['range']} @ {low_buy['yes']:.0f}¢ (too expensive)")
        
        # All brackets
        with st.expander("View All LOW Brackets"):
            for b in low_brackets:
                is_buy = low_buy and b['range'] == low_buy['range']
                if is_buy:
                    st.markdown(f"**🎯 {b['range']}** — YES {b['yes']:.0f}¢")
                else:
                    st.write(f"{b['range']} — YES {b['yes']:.0f}¢")
    else:
        st.error("❌ No LOW temp markets found for today")

# ========== FOOTER ==========
st.divider()
st.caption("⚠️ For educational purposes only. Not financial advice. Settlement based on NWS Daily Climate Report.")
