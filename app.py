import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="NBA Edge Finder (TEST)", page_icon="🎯", layout="wide")

# ========== AUTO-REFRESH SETUP ==========
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

if st.session_state.auto_refresh:
    st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)
    auto_status = "🔄 Auto-refresh ON (30s)"
else:
    auto_status = "⏸️ Auto-refresh OFF"

st.markdown("""
<style>
.stLinkButton > a {
    background-color: #00aa00 !important;
    border-color: #00aa00 !important;
    color: white !important;
}
.stLinkButton > a:hover {
    background-color: #00cc00 !important;
    border-color: #00cc00 !important;
}
</style>
""", unsafe_allow_html=True)

# ========== KALSHI TEAM CODES ==========
KALSHI_CODES = {
    "Atlanta": "atl", "Boston": "bos", "Brooklyn": "bkn", "Charlotte": "cha",
    "Chicago": "chi", "Cleveland": "cle", "Dallas": "dal", "Denver": "den",
    "Detroit": "det", "Golden State": "gsw", "Houston": "hou", "Indiana": "ind",
    "LA Clippers": "lac", "LA Lakers": "lal", "Memphis": "mem", "Miami": "mia",
    "Milwaukee": "mil", "Minnesota": "min", "New Orleans": "nop", "New York": "nyk",
    "Oklahoma City": "okc", "Orlando": "orl", "Philadelphia": "phi", "Phoenix": "phx",
    "Portland": "por", "Sacramento": "sac", "San Antonio": "sas", "Toronto": "tor",
    "Utah": "uta", "Washington": "was"
}

def build_kalshi_totals_url(away_team, home_team):
    away_code = KALSHI_CODES.get(away_team, "xxx")
    home_code = KALSHI_CODES.get(home_team, "xxx")
    today = datetime.now(pytz.timezone('US/Eastern'))
    date_str = today.strftime("%y%b%d").lower()
    ticker = f"kxnbatotal-{date_str}{away_code}{home_code}"
    return f"https://kalshi.com/markets/kxnbatotal/pro-basketball-total-points/{ticker}"

def build_kalshi_ml_url(away_team, home_team):
    away_code = KALSHI_CODES.get(away_team, "xxx")
    home_code = KALSHI_CODES.get(home_team, "xxx")
    today = datetime.now(pytz.timezone('US/Eastern'))
    date_str = today.strftime("%y%b%d").lower()
    ticker = f"kxnbagame-{date_str}{away_code}{home_code}"
    return f"https://kalshi.com/markets/kxnbagame/pro-basketball-moneyline/{ticker}"

if "positions" not in st.session_state:
    st.session_state.positions = []

# ========== STAR PLAYERS DATABASE ==========
STAR_PLAYERS_DB = {
    "Atlanta": {"Trae Young": (3, "O"), "Dejounte Murray": (2, "B"), "Jalen Johnson": (2, "B")},
    "Boston": {"Jayson Tatum": (3, "B"), "Jaylen Brown": (3, "O"), "Derrick White": (2, "D"), "Kristaps Porzingis": (2, "B")},
    "Brooklyn": {"Mikal Bridges": (2, "B"), "Cam Thomas": (2, "O"), "Ben Simmons": (1, "D")},
    "Charlotte": {"LaMelo Ball": (3, "O"), "Brandon Miller": (2, "O"), "Miles Bridges": (2, "B")},
    "Chicago": {"Zach LaVine": (2, "O"), "DeMar DeRozan": (2, "O"), "Coby White": (2, "O")},
    "Cleveland": {"Donovan Mitchell": (3, "O"), "Darius Garland": (2, "O"), "Evan Mobley": (2, "D"), "Jarrett Allen": (2, "D")},
    "Dallas": {"Luka Doncic": (3, "O"), "Kyrie Irving": (3, "O"), "PJ Washington": (2, "D"), "Dereck Lively II": (2, "D")},
    "Denver": {"Nikola Jokic": (3, "B"), "Jamal Murray": (3, "O"), "Aaron Gordon": (2, "D"), "Michael Porter Jr.": (2, "O")},
    "Detroit": {"Cade Cunningham": (2, "O"), "Jaden Ivey": (2, "O"), "Jalen Duren": (1, "D")},
    "Golden State": {"Stephen Curry": (3, "O"), "Draymond Green": (2, "D"), "Andrew Wiggins": (2, "B"), "Klay Thompson": (2, "O")},
    "Houston": {"Jalen Green": (2, "O"), "Alperen Sengun": (2, "B"), "Fred VanVleet": (2, "O"), "Jabari Smith Jr.": (2, "D")},
    "Indiana": {"Tyrese Haliburton": (3, "O"), "Pascal Siakam": (2, "B"), "Myles Turner": (2, "D"), "Bennedict Mathurin": (2, "O")},
    "LA Clippers": {"Kawhi Leonard": (3, "B"), "Paul George": (3, "B"), "James Harden": (3, "O"), "Norman Powell": (2, "O")},
    "LA Lakers": {"LeBron James": (3, "B"), "Anthony Davis": (3, "B"), "Austin Reaves": (2, "O"), "D'Angelo Russell": (2, "O")},
    "Memphis": {"Ja Morant": (3, "O"), "Desmond Bane": (2, "O"), "Jaren Jackson Jr.": (2, "D"), "Marcus Smart": (2, "D")},
    "Miami": {"Jimmy Butler": (3, "B"), "Bam Adebayo": (3, "D"), "Tyler Herro": (2, "O"), "Terry Rozier": (2, "O")},
    "Milwaukee": {"Giannis Antetokounmpo": (3, "B"), "Damian Lillard": (3, "O"), "Khris Middleton": (2, "O"), "Brook Lopez": (2, "D")},
    "Minnesota": {"Anthony Edwards": (3, "O"), "Karl-Anthony Towns": (2, "O"), "Rudy Gobert": (3, "D"), "Jaden McDaniels": (2, "D")},
    "New Orleans": {"Zion Williamson": (3, "O"), "Brandon Ingram": (2, "O"), "CJ McCollum": (2, "O"), "Herb Jones": (2, "D")},
    "New York": {"Jalen Brunson": (3, "O"), "Julius Randle": (2, "B"), "RJ Barrett": (2, "O"), "Mitchell Robinson": (2, "D")},
    "Oklahoma City": {"Shai Gilgeous-Alexander": (3, "O"), "Chet Holmgren": (3, "D"), "Jalen Williams": (2, "B"), "Lu Dort": (2, "D")},
    "Orlando": {"Paolo Banchero": (3, "O"), "Franz Wagner": (2, "B"), "Wendell Carter Jr.": (2, "D"), "Jalen Suggs": (2, "D")},
    "Philadelphia": {"Joel Embiid": (3, "B"), "Tyrese Maxey": (2, "O"), "Tobias Harris": (2, "O")},
    "Phoenix": {"Kevin Durant": (3, "O"), "Devin Booker": (3, "O"), "Bradley Beal": (2, "O"), "Jusuf Nurkic": (2, "D")},
    "Portland": {"Anfernee Simons": (2, "O"), "Scoot Henderson": (2, "O"), "Jerami Grant": (2, "B")},
    "Sacramento": {"De'Aaron Fox": (3, "O"), "Domantas Sabonis": (3, "B"), "Keegan Murray": (2, "O"), "Malik Monk": (2, "O")},
    "San Antonio": {"Victor Wembanyama": (3, "B"), "Devin Vassell": (2, "O"), "Keldon Johnson": (2, "O")},
    "Toronto": {"Scottie Barnes": (2, "B"), "Pascal Siakam": (2, "B"), "RJ Barrett": (2, "O")},
    "Utah": {"Lauri Markkanen": (2, "O"), "Jordan Clarkson": (2, "O"), "Walker Kessler": (2, "D")},
    "Washington": {"Jordan Poole": (2, "O"), "Kyle Kuzma": (2, "O"), "Bilal Coulibaly": (1, "D")}
}

# ========== SIDEBAR LEGEND ==========
with st.sidebar:
    st.header("📖 LEGEND")
    
    st.subheader("🎯 ML Signal Tiers")
    st.markdown("""
    🟢 **STRONG BUY** → 8.0+ score  
    🔵 **BUY** → 6.5 - 7.9 score  
    🟡 **LEAN** → 5.5 - 6.4 score  
    ⚪ **TOSS-UP** → 4.5 - 5.4 score  
    🔴 **SKIP** → Below 4.5
    """)
    
    st.divider()
    
    st.subheader("📊 10-Factor ML System")
    st.markdown("""
    1. Rest Advantage  
    2. Net Rating Edge  
    3. Defense Ranking  
    4. Home Court  
    5. Injury Impact  
    6. Travel Fatigue  
    7. Home/Away Splits  
    8. Division Rivalry  
    9. Altitude (Denver)  
    10. Team Quality
    """)
    
    st.divider()
    
    st.subheader("🎯 Totals Signal Tiers")
    st.markdown("""
    🟢 **STRONG NO/YES** → 8.0+ score  
    🔵 **NO/YES** → 6.5 - 7.9 score  
    🟡 **LEAN NO/YES** → 5.5 - 6.4  
    ⚪ **TOSS-UP** → 4.5 - 5.4  
    🔴 **SKIP** → Below 4.5
    """)
    
    st.divider()
    
    st.subheader("⭐ Star Injury Weights")
    st.markdown("""
    ⭐⭐⭐ **Superstar** → 3x weight  
    ⭐⭐ **All-Star** → 2x weight  
    ⭐ **Rotation** → 1x weight  
    🔥 Offense | 🛡️ Defense | ⚔️ Both
    """)
    
    st.divider()
    
    st.subheader("🔥 Pace Labels")
    st.markdown("""
    🟢 **SLOW** → Under 4.5/min  
    🟡 **AVG** → 4.5 - 4.8/min  
    🟠 **FAST** → 4.8 - 5.2/min  
    🔴 **SHOOTOUT** → Over 5.2/min
    """)
    
    st.divider()
    st.caption("TEST v15.9")

# ========== TEAM DATA ==========
TEAM_ABBREVS = {
    "Atlanta Hawks": "Atlanta", "Boston Celtics": "Boston", "Brooklyn Nets": "Brooklyn",
    "Charlotte Hornets": "Charlotte", "Chicago Bulls": "Chicago", "Cleveland Cavaliers": "Cleveland",
    "Dallas Mavericks": "Dallas", "Denver Nuggets": "Denver", "Detroit Pistons": "Detroit",
    "Golden State Warriors": "Golden State", "Houston Rockets": "Houston", "Indiana Pacers": "Indiana",
    "LA Clippers": "LA Clippers", "Los Angeles Clippers": "LA Clippers", "LA Lakers": "LA Lakers",
    "Los Angeles Lakers": "LA Lakers", "Memphis Grizzlies": "Memphis", "Miami Heat": "Miami",
    "Milwaukee Bucks": "Milwaukee", "Minnesota Timberwolves": "Minnesota", "New Orleans Pelicans": "New Orleans",
    "New York Knicks": "New York", "Oklahoma City Thunder": "Oklahoma City", "Orlando Magic": "Orlando",
    "Philadelphia 76ers": "Philadelphia", "Phoenix Suns": "Phoenix", "Portland Trail Blazers": "Portland",
    "Sacramento Kings": "Sacramento", "San Antonio Spurs": "San Antonio", "Toronto Raptors": "Toronto",
    "Utah Jazz": "Utah", "Washington Wizards": "Washington"
}

TEAM_STATS = {
    "Atlanta": {"pace": 100.5, "def_rank": 26, "net_rating": -3.2, "ft_rate": 0.26, "reb_rate": 49.5, "three_pct": 36.2, "home_win_pct": 0.52, "away_win_pct": 0.35, "division": "Southeast"},
    "Boston": {"pace": 99.8, "def_rank": 2, "net_rating": 11.2, "ft_rate": 0.24, "reb_rate": 51.2, "three_pct": 38.5, "home_win_pct": 0.78, "away_win_pct": 0.65, "division": "Atlantic"},
    "Brooklyn": {"pace": 98.2, "def_rank": 22, "net_rating": -4.5, "ft_rate": 0.23, "reb_rate": 48.8, "three_pct": 35.8, "home_win_pct": 0.42, "away_win_pct": 0.28, "division": "Atlantic"},
    "Charlotte": {"pace": 99.5, "def_rank": 28, "net_rating": -6.8, "ft_rate": 0.25, "reb_rate": 48.2, "three_pct": 34.5, "home_win_pct": 0.38, "away_win_pct": 0.22, "division": "Southeast"},
    "Chicago": {"pace": 98.8, "def_rank": 20, "net_rating": -2.1, "ft_rate": 0.24, "reb_rate": 49.8, "three_pct": 35.2, "home_win_pct": 0.48, "away_win_pct": 0.32, "division": "Central"},
    "Cleveland": {"pace": 97.2, "def_rank": 3, "net_rating": 8.5, "ft_rate": 0.27, "reb_rate": 52.5, "three_pct": 36.8, "home_win_pct": 0.75, "away_win_pct": 0.58, "division": "Central"},
    "Dallas": {"pace": 99.0, "def_rank": 12, "net_rating": 4.2, "ft_rate": 0.26, "reb_rate": 50.2, "three_pct": 37.5, "home_win_pct": 0.62, "away_win_pct": 0.48, "division": "Southwest"},
    "Denver": {"pace": 98.5, "def_rank": 10, "net_rating": 5.8, "ft_rate": 0.25, "reb_rate": 51.8, "three_pct": 36.5, "home_win_pct": 0.72, "away_win_pct": 0.45, "division": "Northwest"},
    "Detroit": {"pace": 97.8, "def_rank": 29, "net_rating": -8.2, "ft_rate": 0.24, "reb_rate": 48.5, "three_pct": 34.2, "home_win_pct": 0.32, "away_win_pct": 0.18, "division": "Central"},
    "Golden State": {"pace": 100.2, "def_rank": 8, "net_rating": 3.5, "ft_rate": 0.23, "reb_rate": 50.5, "three_pct": 38.2, "home_win_pct": 0.65, "away_win_pct": 0.42, "division": "Pacific"},
    "Houston": {"pace": 101.5, "def_rank": 18, "net_rating": 1.2, "ft_rate": 0.28, "reb_rate": 50.8, "three_pct": 35.5, "home_win_pct": 0.55, "away_win_pct": 0.38, "division": "Southwest"},
    "Indiana": {"pace": 103.5, "def_rank": 24, "net_rating": 2.8, "ft_rate": 0.26, "reb_rate": 49.2, "three_pct": 37.8, "home_win_pct": 0.58, "away_win_pct": 0.42, "division": "Central"},
    "LA Clippers": {"pace": 98.0, "def_rank": 14, "net_rating": 1.5, "ft_rate": 0.25, "reb_rate": 50.0, "three_pct": 36.0, "home_win_pct": 0.55, "away_win_pct": 0.40, "division": "Pacific"},
    "LA Lakers": {"pace": 99.5, "def_rank": 15, "net_rating": 2.2, "ft_rate": 0.27, "reb_rate": 51.0, "three_pct": 35.8, "home_win_pct": 0.58, "away_win_pct": 0.42, "division": "Pacific"},
    "Memphis": {"pace": 100.8, "def_rank": 6, "net_rating": 4.5, "ft_rate": 0.26, "reb_rate": 52.2, "three_pct": 35.2, "home_win_pct": 0.68, "away_win_pct": 0.48, "division": "Southwest"},
    "Miami": {"pace": 97.5, "def_rank": 5, "net_rating": 3.8, "ft_rate": 0.24, "reb_rate": 50.8, "three_pct": 36.5, "home_win_pct": 0.65, "away_win_pct": 0.45, "division": "Southeast"},
    "Milwaukee": {"pace": 99.2, "def_rank": 9, "net_rating": 5.2, "ft_rate": 0.28, "reb_rate": 51.5, "three_pct": 37.2, "home_win_pct": 0.70, "away_win_pct": 0.52, "division": "Central"},
    "Minnesota": {"pace": 98.8, "def_rank": 4, "net_rating": 7.5, "ft_rate": 0.25, "reb_rate": 52.8, "three_pct": 36.2, "home_win_pct": 0.72, "away_win_pct": 0.55, "division": "Northwest"},
    "New Orleans": {"pace": 100.0, "def_rank": 16, "net_rating": 1.8, "ft_rate": 0.27, "reb_rate": 50.5, "three_pct": 36.8, "home_win_pct": 0.55, "away_win_pct": 0.38, "division": "Southwest"},
    "New York": {"pace": 98.5, "def_rank": 7, "net_rating": 6.2, "ft_rate": 0.25, "reb_rate": 51.2, "three_pct": 37.0, "home_win_pct": 0.68, "away_win_pct": 0.52, "division": "Atlantic"},
    "Oklahoma City": {"pace": 99.8, "def_rank": 1, "net_rating": 12.5, "ft_rate": 0.26, "reb_rate": 52.0, "three_pct": 37.5, "home_win_pct": 0.82, "away_win_pct": 0.68, "division": "Northwest"},
    "Orlando": {"pace": 97.0, "def_rank": 11, "net_rating": 3.2, "ft_rate": 0.26, "reb_rate": 51.5, "three_pct": 35.5, "home_win_pct": 0.62, "away_win_pct": 0.45, "division": "Southeast"},
    "Philadelphia": {"pace": 98.2, "def_rank": 13, "net_rating": 2.5, "ft_rate": 0.28, "reb_rate": 50.2, "three_pct": 36.2, "home_win_pct": 0.58, "away_win_pct": 0.42, "division": "Atlantic"},
    "Phoenix": {"pace": 99.0, "def_rank": 17, "net_rating": 2.0, "ft_rate": 0.25, "reb_rate": 49.8, "three_pct": 36.8, "home_win_pct": 0.60, "away_win_pct": 0.42, "division": "Pacific"},
    "Portland": {"pace": 99.5, "def_rank": 27, "net_rating": -5.5, "ft_rate": 0.24, "reb_rate": 48.5, "three_pct": 35.0, "home_win_pct": 0.40, "away_win_pct": 0.25, "division": "Northwest"},
    "Sacramento": {"pace": 101.2, "def_rank": 19, "net_rating": 0.8, "ft_rate": 0.25, "reb_rate": 49.5, "three_pct": 36.5, "home_win_pct": 0.55, "away_win_pct": 0.38, "division": "Pacific"},
    "San Antonio": {"pace": 100.5, "def_rank": 25, "net_rating": -4.8, "ft_rate": 0.26, "reb_rate": 49.0, "three_pct": 34.8, "home_win_pct": 0.42, "away_win_pct": 0.28, "division": "Southwest"},
    "Toronto": {"pace": 98.8, "def_rank": 21, "net_rating": -1.5, "ft_rate": 0.24, "reb_rate": 49.5, "three_pct": 35.5, "home_win_pct": 0.48, "away_win_pct": 0.32, "division": "Atlantic"},
    "Utah": {"pace": 100.2, "def_rank": 30, "net_rating": -7.5, "ft_rate": 0.25, "reb_rate": 48.0, "three_pct": 35.2, "home_win_pct": 0.35, "away_win_pct": 0.22, "division": "Northwest"},
    "Washington": {"pace": 101.0, "def_rank": 23, "net_rating": -6.2, "ft_rate": 0.27, "reb_rate": 48.8, "three_pct": 34.5, "home_win_pct": 0.38, "away_win_pct": 0.25, "division": "Southeast"}
}

TEAM_LOCATIONS = {
    "Atlanta": (33.757, -84.396), "Boston": (42.366, -71.062), "Brooklyn": (40.683, -73.976),
    "Charlotte": (35.225, -80.839), "Chicago": (41.881, -87.674), "Cleveland": (41.496, -81.688),
    "Dallas": (32.790, -96.810), "Denver": (39.749, -105.010), "Detroit": (42.341, -83.055),
    "Golden State": (37.768, -122.388), "Houston": (29.751, -95.362), "Indiana": (39.764, -86.156),
    "LA Clippers": (34.043, -118.267), "LA Lakers": (34.043, -118.267), "Memphis": (35.138, -90.051),
    "Miami": (25.781, -80.188), "Milwaukee": (43.045, -87.917), "Minnesota": (44.979, -93.276),
    "New Orleans": (29.949, -90.082), "New York": (40.751, -73.994), "Oklahoma City": (35.463, -97.515),
    "Orlando": (28.539, -81.384), "Philadelphia": (39.901, -75.172), "Phoenix": (33.446, -112.071),
    "Portland": (45.532, -122.667), "Sacramento": (38.580, -121.500), "San Antonio": (29.427, -98.438),
    "Toronto": (43.643, -79.379), "Utah": (40.768, -111.901), "Washington": (38.898, -77.021)
}

STAR_PLAYERS = {
    "Atlanta": ["Trae Young"], "Boston": ["Jayson Tatum", "Jaylen Brown"], "Brooklyn": ["Mikal Bridges"],
    "Charlotte": ["LaMelo Ball"], "Chicago": ["Zach LaVine", "DeMar DeRozan"],
    "Cleveland": ["Donovan Mitchell", "Darius Garland", "Evan Mobley"],
    "Dallas": ["Luka Doncic", "Kyrie Irving"], "Denver": ["Nikola Jokic", "Jamal Murray"],
    "Detroit": ["Cade Cunningham"], "Golden State": ["Stephen Curry", "Draymond Green"],
    "Houston": ["Jalen Green", "Alperen Sengun"], "Indiana": ["Tyrese Haliburton", "Pascal Siakam"],
    "LA Clippers": ["Kawhi Leonard", "Paul George"], "LA Lakers": ["LeBron James", "Anthony Davis"],
    "Memphis": ["Ja Morant", "Desmond Bane"], "Miami": ["Jimmy Butler", "Bam Adebayo"],
    "Milwaukee": ["Giannis Antetokounmpo", "Damian Lillard"],
    "Minnesota": ["Anthony Edwards", "Karl-Anthony Towns", "Rudy Gobert"],
    "New Orleans": ["Zion Williamson", "Brandon Ingram"], "New York": ["Jalen Brunson", "Julius Randle"],
    "Oklahoma City": ["Shai Gilgeous-Alexander", "Chet Holmgren", "Jalen Williams"],
    "Orlando": ["Paolo Banchero", "Franz Wagner"], "Philadelphia": ["Joel Embiid", "Tyrese Maxey"],
    "Phoenix": ["Kevin Durant", "Devin Booker", "Bradley Beal"], "Portland": ["Anfernee Simons"],
    "Sacramento": ["De'Aaron Fox", "Domantas Sabonis"], "San Antonio": ["Victor Wembanyama"],
    "Toronto": ["Scottie Barnes"], "Utah": ["Lauri Markkanen"], "Washington": ["Jordan Poole"]
}

def calc_distance(loc1, loc2):
    from math import radians, sin, cos, sqrt, atan2
    lat1, lon1 = radians(loc1[0]), radians(loc1[1])
    lat2, lon2 = radians(loc2[0]), radians(loc2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 3959 * 2 * atan2(sqrt(a), sqrt(1-a))

def fetch_espn_scores():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        games = {}
        for event in data.get("events", []):
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home_team, away_team, home_score, away_score = None, None, 0, 0
            for c in competitors:
                name = c.get("team", {}).get("displayName", "")
                team_name = TEAM_ABBREVS.get(name, name)
                score = int(c.get("score", 0) or 0)
                if c.get("homeAway") == "home":
                    home_team, home_score = team_name, score
                else:
                    away_team, away_score = team_name, score
            status_obj = event.get("status", {})
            status_type = status_obj.get("type", {}).get("name", "STATUS_SCHEDULED")
            clock = status_obj.get("displayClock", "")
            period = status_obj.get("period", 0)
            game_key = f"{away_team}@{home_team}"
            games[game_key] = {
                "away_team": away_team, "home_team": home_team,
                "away_score": away_score, "home_score": home_score,
                "total": away_score + home_score,
                "period": period, "clock": clock, "status_type": status_type
            }
        return games
    except:
        return {}

def fetch_yesterday_teams():
    yesterday = (datetime.now(pytz.timezone('US/Eastern')) - timedelta(days=1)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        teams_played = set()
        for event in data.get("events", []):
            comp = event.get("competitions", [{}])[0]
            for c in comp.get("competitors", []):
                full_name = c.get("team", {}).get("displayName", "")
                team_name = TEAM_ABBREVS.get(full_name, full_name)
                teams_played.add(team_name)
        return teams_played
    except:
        return set()

def fetch_espn_injuries():
    injuries = {}
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        injury_list = data.get("injuries", data.get("teams", []))
        for team_data in injury_list:
            team_name = team_data.get("team", {}).get("displayName", "")
            if not team_name:
                team_name = team_data.get("team", {}).get("name", "")
            if not team_name:
                team_name = team_data.get("displayName", "")
            team_key = TEAM_ABBREVS.get(team_name, team_name)
            if not team_key:
                continue
            injuries[team_key] = []
            player_list = team_data.get("injuries", team_data.get("athletes", []))
            for player in player_list:
                name = player.get("athlete", {}).get("displayName", "")
                if not name:
                    name = player.get("displayName", "")
                if not name:
                    name = player.get("name", "")
                status = player.get("status", "")
                if not status:
                    status = player.get("type", {}).get("description", "")
                if name:
                    injuries[team_key].append({"name": name, "status": status})
    except:
        pass
    return injuries

def fetch_rotowire_injuries():
    injuries = {}
    try:
        url = "https://www.rotowire.com/basketball/tables/injury-report.php?team=ALL&pos=ALL"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            team_map = {
                'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
                'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
                'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
                'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
                'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
                'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
                'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
                'UTA': 'Utah', 'WAS': 'Washington'
            }
            for player in data:
                team_abbr = player.get('team', '')
                team_key = team_map.get(team_abbr, team_abbr)
                if team_key not in injuries:
                    injuries[team_key] = []
                name = player.get('player', '')
                status = player.get('status', '').upper()
                if name:
                    injuries[team_key].append({"name": name, "status": status})
    except:
        pass
    return injuries

def merge_injuries(espn_inj, roto_inj):
    merged = {}
    all_teams = set(list(espn_inj.keys()) + list(roto_inj.keys()))
    for team in all_teams:
        merged[team] = []
        seen_players = set()
        for inj in espn_inj.get(team, []):
            name_lower = inj['name'].lower()
            if name_lower not in seen_players:
                merged[team].append(inj)
                seen_players.add(name_lower)
        for inj in roto_inj.get(team, []):
            name_lower = inj['name'].lower()
            if name_lower not in seen_players:
                merged[team].append(inj)
                seen_players.add(name_lower)
    return merged

def get_star_tier(player_name, team):
    team_stars = STAR_PLAYERS_DB.get(team, {})
    for star_name, (tier, player_type) in team_stars.items():
        if star_name.lower() in player_name.lower() or player_name.lower() in star_name.lower():
            return tier, player_type
    return 0, None

def format_star_rating(tier):
    if tier == 3: return "⭐⭐⭐"
    elif tier == 2: return "⭐⭐"
    elif tier == 1: return "⭐"
    return ""

def format_player_type(player_type):
    if player_type == "O": return "🔥"
    elif player_type == "D": return "🛡️"
    elif player_type == "B": return "⚔️"
    return ""

def get_injury_score(team, injuries):
    team_injuries = injuries.get(team, [])
    stars = STAR_PLAYERS.get(team, [])
    score = 0
    out_stars = []
    for inj in team_injuries:
        name = inj.get("name", "")
        status = inj.get("status", "").upper()
        is_star = any(star.lower() in name.lower() for star in stars)
        if "OUT" in status:
            score += 4.0 if is_star else 1.0
            if is_star: out_stars.append(name)
        elif "DAY-TO-DAY" in status or "GTD" in status or "QUESTIONABLE" in status:
            score += 2.5 if is_star else 0.5
    return score, out_stars

def get_detailed_injuries(team, injuries):
    team_injuries = injuries.get(team, [])
    detailed = []
    for inj in team_injuries:
        name = inj.get("name", "")
        status = inj.get("status", "").upper()
        tier, player_type = get_star_tier(name, team)
        stars = format_star_rating(tier)
        type_emoji = format_player_type(player_type)
        if "OUT" in status: simple_status = "OUT"
        elif "DAY-TO-DAY" in status or "DTD" in status: simple_status = "DTD"
        elif "QUESTIONABLE" in status or "GTD" in status: simple_status = "GTD"
        else: simple_status = status[:10]
        detailed.append({"name": name, "status": simple_status, "tier": tier, "stars": stars, "type_emoji": type_emoji})
    detailed.sort(key=lambda x: x['tier'], reverse=True)
    return detailed

def get_minutes_played(period, clock, status_type):
    if status_type == "STATUS_FINAL": return 48 if period <= 4 else 48 + (period - 4) * 5
    if status_type == "STATUS_HALFTIME": return 24
    if period == 0: return 0
    try:
        clock_str = str(clock)
        if ':' in clock_str:
            parts = clock_str.split(':')
            mins = int(parts[0])
            secs = int(float(parts[1])) if len(parts) > 1 else 0
        else:
            mins = 0
            secs = float(clock_str) if clock_str else 0
        time_left = mins + secs/60
        if period <= 4: return (period - 1) * 12 + (12 - time_left)
        else: return 48 + (period - 5) * 5 + (5 - time_left)
    except:
        return (period - 1) * 12 if period <= 4 else 48 + (period - 5) * 5

def calc_12_factor_edge(home_team, away_team, home_rest, away_rest, home_inj, away_inj, kalshi_price):
    home = TEAM_STATS.get(home_team, {"pace": 100, "def_rank": 15, "net_rating": 0, "ft_rate": 0.25, "reb_rate": 50, "three_pct": 36, "home_win_pct": 0.5, "away_win_pct": 0.5, "division": ""})
    away = TEAM_STATS.get(away_team, {"pace": 100, "def_rank": 15, "net_rating": 0, "ft_rate": 0.25, "reb_rate": 50, "three_pct": 36, "home_win_pct": 0.5, "away_win_pct": 0.5, "division": ""})
    home_loc = TEAM_LOCATIONS.get(home_team, (0, 0))
    away_loc = TEAM_LOCATIONS.get(away_team, (0, 0))
    travel_miles = calc_distance(away_loc, home_loc)
    rest_diff = home_rest - away_rest
    rest_score = max(-6, min(6, rest_diff * 2))
    def_score = (away['def_rank'] - home['def_rank']) * 0.15
    injury_score = (away_inj - home_inj) * 1.5
    pace_diff = home['pace'] - away['pace']
    pace_score = pace_diff * 0.1 if home['net_rating'] > away['net_rating'] else -pace_diff * 0.1
    net_score = (home['net_rating'] - away['net_rating']) * 0.8
    travel_score = 2.5 if travel_miles > 1500 else (1.5 if travel_miles > 1000 else (0.75 if travel_miles > 500 else 0))
    split_score = (home['home_win_pct'] - 0.5) * 10 + (0.5 - away['away_win_pct']) * 10
    h2h_score = 1.5 if home.get('division') == away.get('division') and home.get('division') else 0
    altitude_score = 2.0 if home_team == "Denver" else 0
    ft_score = (home.get('ft_rate', 0.25) - away.get('ft_rate', 0.25)) * 20
    reb_score = (home.get('reb_rate', 50) - away.get('reb_rate', 50)) * 0.3
    three_score = (home.get('three_pct', 36) - away.get('three_pct', 36)) * 0.5
    home_court = 3.0
    weighted_spread = home_court + rest_score + def_score + injury_score + pace_score + net_score + travel_score + split_score + h2h_score + altitude_score + ft_score + reb_score + three_score
    home_win_prob = max(5, min(95, 50 + weighted_spread * 2.5))
    edge = home_win_prob - kalshi_price
    return {'home_win_prob': round(home_win_prob, 1), 'kalshi_price': kalshi_price, 'edge': round(edge, 1), 'expected_spread': round(weighted_spread, 1)}

def calc_ml_score(home_team, away_team, yesterday_teams, injuries):
    home = TEAM_STATS.get(home_team, {})
    away = TEAM_STATS.get(away_team, {})
    home_loc = TEAM_LOCATIONS.get(home_team, (0, 0))
    away_loc = TEAM_LOCATIONS.get(away_team, (0, 0))
    score_home, score_away = 0, 0
    reasons_home, reasons_away = [], []
    home_b2b = home_team in yesterday_teams
    away_b2b = away_team in yesterday_teams
    if away_b2b and not home_b2b:
        score_home += 1.0
        reasons_home.append("🛏️ Opp B2B")
    elif home_b2b and not away_b2b:
        score_away += 1.0
        reasons_away.append("🛏️ Opp B2B")
    elif not home_b2b and not away_b2b:
        score_home += 0.5
        score_away += 0.5
    home_net = home.get('net_rating', 0)
    away_net = away.get('net_rating', 0)
    net_diff = home_net - away_net
    if net_diff > 5:
        score_home += 1.0
        reasons_home.append(f"📊 Net +{home_net:.1f}")
    elif net_diff > 2:
        score_home += 0.7
        reasons_home.append(f"📊 Net +{home_net:.1f}")
    elif net_diff > 0: score_home += 0.5
    elif net_diff > -2: score_away += 0.5
    elif net_diff > -5:
        score_away += 0.7
        reasons_away.append(f"📊 Net +{away_net:.1f}")
    else:
        score_away += 1.0
        reasons_away.append(f"📊 Net +{away_net:.1f}")
    home_def = home.get('def_rank', 15)
    away_def = away.get('def_rank', 15)
    if home_def <= 5:
        score_home += 1.0
        reasons_home.append(f"🛡️ #{home_def} DEF")
    elif home_def <= 10:
        score_home += 0.7
        reasons_home.append(f"🛡️ #{home_def} DEF")
    elif home_def <= 15: score_home += 0.4
    if away_def <= 5:
        score_away += 1.0
        reasons_away.append(f"🛡️ #{away_def} DEF")
    elif away_def <= 10:
        score_away += 0.7
        reasons_away.append(f"🛡️ #{away_def} DEF")
    elif away_def <= 15: score_away += 0.4
    score_home += 1.0
    home_inj, home_stars = get_injury_score(home_team, injuries)
    away_inj, away_stars = get_injury_score(away_team, injuries)
    inj_diff = away_inj - home_inj
    if inj_diff > 3:
        score_home += 1.0
        if away_stars: reasons_home.append(f"🏥 {away_stars[0][:10]} OUT")
    elif inj_diff > 1:
        score_home += 0.6
        if away_stars: reasons_home.append(f"🏥 {away_stars[0][:10]} OUT")
    elif inj_diff < -3:
        score_away += 1.0
        if home_stars: reasons_away.append(f"🏥 {home_stars[0][:10]} OUT")
    elif inj_diff < -1:
        score_away += 0.6
        if home_stars: reasons_away.append(f"🏥 {home_stars[0][:10]} OUT")
    else:
        score_home += 0.3
        score_away += 0.3
    travel_miles = calc_distance(away_loc, home_loc)
    if travel_miles > 2000:
        score_home += 1.0
        reasons_home.append(f"✈️ {int(travel_miles)}mi")
    elif travel_miles > 1500:
        score_home += 0.7
        reasons_home.append(f"✈️ {int(travel_miles)}mi")
    elif travel_miles > 1000: score_home += 0.5
    elif travel_miles > 500: score_home += 0.3
    home_hw = home.get('home_win_pct', 0.5)
    away_aw = away.get('away_win_pct', 0.5)
    reasons_home.append(f"🏠 {int(home_hw*100)}% home")
    if home_hw > 0.65: score_home += 0.8
    elif home_hw > 0.55: score_home += 0.5
    if away_aw < 0.35:
        score_home += 0.5
        reasons_home.append(f"📉 Opp {int(away_aw*100)}% road")
    elif away_aw < 0.45:
        score_home += 0.3
        reasons_home.append(f"📉 Opp {int(away_aw*100)}% road")
    if home.get('division') == away.get('division') and home.get('division'):
        score_home += 0.5
        reasons_home.append("⚔️ Division")
    if home_team == "Denver":
        score_home += 1.0
        reasons_home.append("🏔️ Altitude")
    if home_net > 5:
        score_home += 0.5
        if f"📊 Net +{home_net:.1f}" not in reasons_home: reasons_home.append("⭐ Elite")
    if away_net > 5:
        score_away += 0.5
        if f"📊 Net +{away_net:.1f}" not in reasons_away: reasons_away.append("⭐ Elite")
    total = score_home + score_away
    if total > 0:
        home_final = round((score_home / total) * 10, 1)
        away_final = round((score_away / total) * 10, 1)
    else:
        home_final, away_final = 5.0, 5.0
    if home_final >= away_final:
        return home_team, home_final, round((home_final - 5) * 4, 0), reasons_home[:4], home_stars, away_stars
    else:
        return away_team, away_final, round((away_final - 5) * 4, 0), reasons_away[:4], home_stars, away_stars

def get_signal_tier(score):
    if score >= 8.0: return "🟢 STRONG BUY", "#00ff00"
    elif score >= 6.5: return "🔵 BUY", "#00aaff"
    elif score >= 5.5: return "🟡 LEAN", "#ffff00"
    elif score >= 4.5: return "⚪ TOSS-UP", "#888888"
    else: return "🔴 SKIP", "#ff0000"

def calc_totals_score(home_team, away_team, yesterday_teams, injuries):
    home = TEAM_STATS.get(home_team, {})
    away = TEAM_STATS.get(away_team, {})
    score_under, score_over = 0, 0
    reasons_under, reasons_over = [], []
    home_pace = home.get('pace', 100)
    away_pace = away.get('pace', 100)
    avg_pace = (home_pace + away_pace) / 2
    if avg_pace < 98.5:
        score_under += 1.5
        reasons_under.append(f"🐢 Slow {avg_pace:.1f}")
    elif avg_pace < 99.5:
        score_under += 1.0
        reasons_under.append(f"🐢 Pace {avg_pace:.1f}")
    elif avg_pace > 101:
        score_over += 1.5
        reasons_over.append(f"🔥 Fast {avg_pace:.1f}")
    elif avg_pace > 100:
        score_over += 1.0
        reasons_over.append(f"🔥 Pace {avg_pace:.1f}")
    home_def = home.get('def_rank', 15)
    away_def = away.get('def_rank', 15)
    avg_def = (home_def + away_def) / 2
    if avg_def <= 8:
        score_under += 1.5
        reasons_under.append(f"🛡️ DEF #{int(avg_def)}")
    elif avg_def <= 12:
        score_under += 1.0
        reasons_under.append(f"🛡️ DEF #{int(avg_def)}")
    elif avg_def >= 22:
        score_over += 1.5
        reasons_over.append(f"💥 DEF #{int(avg_def)}")
    elif avg_def >= 18:
        score_over += 1.0
        reasons_over.append(f"💥 DEF #{int(avg_def)}")
    home_b2b = home_team in yesterday_teams
    away_b2b = away_team in yesterday_teams
    if home_b2b and away_b2b:
        score_under += 1.5
        reasons_under.append("🛏️ Both B2B")
    elif home_b2b or away_b2b:
        score_under += 0.75
        tired_team = home_team if home_b2b else away_team
        reasons_under.append(f"🛏️ {tired_team[:3]} B2B")
    home_3pt = home.get('three_pct', 36)
    away_3pt = away.get('three_pct', 36)
    avg_3pt = (home_3pt + away_3pt) / 2
    if avg_3pt < 35.5:
        score_under += 1.0
        reasons_under.append(f"🎯 Low 3PT {avg_3pt:.1f}%")
    elif avg_3pt > 37.5:
        score_over += 1.0
        reasons_over.append(f"🎯 High 3PT {avg_3pt:.1f}%")
    home_inj, home_stars = get_injury_score(home_team, injuries)
    away_inj, away_stars = get_injury_score(away_team, injuries)
    if home_stars or away_stars:
        score_under += 1.0
        out_names = (home_stars + away_stars)[:2]
        reasons_under.append(f"🏥 {', '.join([n[:8] for n in out_names])} OUT")
    home_net = home.get('net_rating', 0)
    away_net = away.get('net_rating', 0)
    net_diff = abs(home_net - away_net)
    if net_diff > 10:
        score_over += 0.75
        reasons_over.append("💥 Blowout risk")
    elif net_diff < 3:
        score_under += 0.5
        reasons_under.append("⚔️ Close game")
    if home_team == "Denver":
        score_under += 0.75
        reasons_under.append("🏔️ Denver altitude")
    home_ft = home.get('ft_rate', 0.25)
    away_ft = away.get('ft_rate', 0.25)
    avg_ft = (home_ft + away_ft) / 2
    if avg_ft > 0.27:
        score_under += 0.5
        reasons_under.append("🎁 High FT rate")
    elif avg_ft < 0.23:
        score_over += 0.5
        reasons_over.append("🏃 Low FT rate")
    home_reb = home.get('reb_rate', 50)
    away_reb = away.get('reb_rate', 50)
    avg_reb = (home_reb + away_reb) / 2
    if avg_reb > 51.5:
        score_under += 0.5
        reasons_under.append("🏀 Control boards")
    if home.get('home_win_pct', 0.5) > 0.65 and home_net > 5:
        score_over += 0.5
        reasons_over.append("🏠 Home scoring")
    total = score_under + score_over
    if total > 0:
        under_final = round((score_under / total) * 10, 1)
        over_final = round((score_over / total) * 10, 1)
    else:
        under_final, over_final = 5.0, 5.0
    if under_final >= over_final:
        return "NO", under_final, reasons_under[:4]
    else:
        return "YES", over_final, reasons_over[:4]

def get_totals_signal_tier(score, pick):
    if score >= 8.0: return f"🟢 STRONG {pick}", "#00ff00"
    elif score >= 6.5: return f"🔵 {pick}", "#00aaff"
    elif score >= 5.5: return f"🟡 LEAN {pick}", "#ffff00"
    elif score >= 4.5: return "⚪ TOSS-UP", "#888888"
    else: return "🔴 SKIP", "#ff0000"

# ========== FETCH DATA ==========
games = fetch_espn_scores()
game_list = sorted(list(games.keys()))
yesterday_teams_raw = fetch_yesterday_teams()
espn_injuries = fetch_espn_injuries()
roto_injuries = fetch_rotowire_injuries()
injuries = merge_injuries(espn_injuries, roto_injuries)
now = datetime.now(pytz.timezone('US/Eastern'))
injury_source_info = f"ESPN: {sum(len(v) for v in espn_injuries.values())} | RotoWire: {sum(len(v) for v in roto_injuries.values())} | Merged: {sum(len(v) for v in injuries.values())}"
today_teams = set()
for game_key in games.keys():
    parts = game_key.split("@")
    today_teams.add(parts[0])
    today_teams.add(parts[1])
yesterday_teams = yesterday_teams_raw.intersection(today_teams)

# ========== HEADER ==========
st.title("🎯 NBA EDGE FINDER (TEST)")
hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
hdr1.caption(f"{auto_status} | Last update: {now.strftime('%I:%M:%S %p ET')} | TEST v15.9")

if hdr2.button("🔄 Auto" if not st.session_state.auto_refresh else "⏹️ Stop", use_container_width=True):
    st.session_state.auto_refresh = not st.session_state.auto_refresh
    st.rerun()

if hdr3.button("🔄 Refresh", use_container_width=True):
    st.rerun()

# ========== 🏥 INJURY REPORT SECTION ==========
st.subheader("🏥 INJURY REPORT - TODAY'S GAMES")
st.caption(f"📡 Data Sources: {injury_source_info}")
total_injuries_loaded = sum(len(v) for v in injuries.values())

if game_list and total_injuries_loaded > 0:
    teams_playing = set()
    for game_key in game_list:
        parts = game_key.split("@")
        teams_playing.add(parts[0])
        teams_playing.add(parts[1])
    star_injuries, allstar_injuries, rotation_injuries = [], [], []
    for team in sorted(teams_playing):
        team_injuries = get_detailed_injuries(team, injuries)
        for inj in team_injuries:
            if inj['tier'] == 3: star_injuries.append((team, inj))
            elif inj['tier'] == 2: allstar_injuries.append((team, inj))
            elif inj['tier'] == 1: rotation_injuries.append((team, inj))
    if star_injuries:
        st.markdown("### ⭐⭐⭐ SUPERSTARS OUT/QUESTIONABLE")
        cols = st.columns(3)
        for idx, (team, inj) in enumerate(star_injuries):
            with cols[idx % 3]:
                status_color = "#ff0000" if inj['status'] == "OUT" else "#ffaa00"
                st.markdown(f"<div style='background:linear-gradient(135deg,#2a1a1a,#1a1a2e);padding:10px;border-radius:8px;border-left:4px solid {status_color};margin-bottom:8px'><span style='color:#fff;font-weight:bold'>{inj['stars']} {inj['name']}</span> {inj['type_emoji']}<br><span style='color:{status_color};font-size:0.9em'>{inj['status']}</span><span style='color:#888;font-size:0.85em'> • {team}</span></div>", unsafe_allow_html=True)
    if allstar_injuries:
        st.markdown("### ⭐⭐ ALL-STARS OUT/QUESTIONABLE")
        cols = st.columns(4)
        for idx, (team, inj) in enumerate(allstar_injuries):
            with cols[idx % 4]:
                status_color = "#ff0000" if inj['status'] == "OUT" else "#ffaa00"
                st.markdown(f"<div style='background:#1a1a2e;padding:8px;border-radius:6px;border-left:3px solid {status_color};margin-bottom:6px'><span style='color:#ddd;font-size:0.95em'>{inj['stars']} {inj['name']}</span> {inj['type_emoji']}<br><span style='color:{status_color};font-size:0.85em'>{inj['status']}</span><span style='color:#666;font-size:0.8em'> • {team}</span></div>", unsafe_allow_html=True)
    if rotation_injuries:
        with st.expander(f"⭐ ROTATION PLAYERS ({len(rotation_injuries)} injuries)", expanded=False):
            cols = st.columns(5)
            for idx, (team, inj) in enumerate(rotation_injuries):
                with cols[idx % 5]:
                    status_color = "#ff4444" if inj['status'] == "OUT" else "#ffaa00"
                    st.markdown(f"<span style='color:#aaa;font-size:0.85em'>{inj['name']}</span> <span style='color:{status_color};font-size:0.8em'>({inj['status']})</span> <span style='color:#666;font-size:0.75em'>• {team}</span>", unsafe_allow_html=True)
    with st.expander("📋 FULL INJURY REPORT BY TEAM", expanded=False):
        cols = st.columns(3)
        col_idx = 0
        for team in sorted(teams_playing):
            team_injuries = get_detailed_injuries(team, injuries)
            if team_injuries:
                with cols[col_idx % 3]:
                    st.markdown(f"**{team}**")
                    for inj in team_injuries:
                        status_color = "#ff0000" if inj['status'] == "OUT" else "#ffaa00" if inj['status'] in ["GTD", "DTD"] else "#888"
                        star_display = f"{inj['stars']} " if inj['stars'] else ""
                        type_display = f" {inj['type_emoji']}" if inj['type_emoji'] else ""
                        st.markdown(f"<span style='color:{status_color};font-size:0.9em'>{star_display}{inj['name']}{type_display} ({inj['status']})</span>", unsafe_allow_html=True)
                    st.markdown("---")
                col_idx += 1
    total_inj = len(star_injuries) + len(allstar_injuries) + len(rotation_injuries)
    st.caption(f"📊 {len(star_injuries)} Superstars | {len(allstar_injuries)} All-Stars | {len(rotation_injuries)} Rotation | {total_inj} Total | 🔥=Offense 🛡️=Defense ⚔️=Both")
else:
    if not game_list: st.info("No games scheduled today")
    elif total_injuries_loaded == 0: st.warning("⚠️ No injury data loaded from ESPN or RotoWire.")
    else: st.info("No injuries found for today's teams")

st.divider()

# ========== 🎯 BIG SNAPSHOT - ML PICKS ==========
st.subheader("🎯 BIG SNAPSHOT - TODAY'S ML PICKS")

if game_list:
    all_picks = []
    for game_key in game_list:
        parts = game_key.split("@")
        away_team, home_team = parts[0], parts[1]
        pick, score, edge, reasons, home_out, away_out = calc_ml_score(home_team, away_team, yesterday_teams, injuries)
        signal, color = get_signal_tier(score)
        all_picks.append({'game': game_key, 'home': home_team, 'away': away_team, 'pick': pick, 'score': score, 'edge': edge, 'signal': signal, 'color': color, 'reasons': reasons})
    all_picks.sort(key=lambda x: x['score'], reverse=True)
    strong_buys = [p for p in all_picks if p['score'] >= 8.0]
    buys = [p for p in all_picks if 6.5 <= p['score'] < 8.0]
    leans = [p for p in all_picks if 5.5 <= p['score'] < 6.5]
    tossups = [p for p in all_picks if 4.5 <= p['score'] < 5.5]
    skips = [p for p in all_picks if p['score'] < 4.5]
    
    if strong_buys:
        st.markdown("### 🟢 STRONG BUY")
        for p in strong_buys:
            reasons_str = " • ".join(p['reasons']) if p['reasons'] else "Multiple factors"
            is_home_pick = p['pick'] == p['home']
            opponent = p['away'] if is_home_pick else p['home']
            home_away_tag = "🏠" if is_home_pick else "✈️"
            col1, col2, col3, col4 = st.columns([3, 2, 4, 2])
            col1.markdown(f"**<span style='color:#00ff00'>{p['pick']}</span>** {home_away_tag} vs {opponent}", unsafe_allow_html=True)
            col2.markdown(f"<span style='color:{p['color']};font-weight:bold'>{p['score']}/10 | +{p['edge']:.0f}%</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#aaa;font-size:0.9em'>{reasons_str}</span>", unsafe_allow_html=True)
            kalshi_url = build_kalshi_ml_url(p['away'], p['home'])
            col4.link_button(f"🔗 VIEW", kalshi_url)
    if buys:
        st.markdown("### 🔵 BUY")
        for p in buys:
            reasons_str = " • ".join(p['reasons']) if p['reasons'] else "Multiple factors"
            is_home_pick = p['pick'] == p['home']
            opponent = p['away'] if is_home_pick else p['home']
            home_away_tag = "🏠" if is_home_pick else "✈️"
            col1, col2, col3, col4 = st.columns([3, 2, 4, 2])
            col1.markdown(f"**<span style='color:#00aaff'>{p['pick']}</span>** {home_away_tag} vs {opponent}", unsafe_allow_html=True)
            col2.markdown(f"<span style='color:{p['color']};font-weight:bold'>{p['score']}/10 | +{p['edge']:.0f}%</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#aaa;font-size:0.9em'>{reasons_str}</span>", unsafe_allow_html=True)
            kalshi_url = build_kalshi_ml_url(p['away'], p['home'])
            col4.link_button(f"🔗 VIEW", kalshi_url)
    if leans:
        st.markdown("### 🟡 LEAN")
        for p in leans:
            reasons_str = " • ".join(p['reasons'][:3]) if p['reasons'] else ""
            is_home_pick = p['pick'] == p['home']
            opponent = p['away'] if is_home_pick else p['home']
            home_away_tag = "🏠" if is_home_pick else "✈️"
            col1, col2, col3 = st.columns([3, 2, 5])
            col1.markdown(f"**<span style='color:#ffff00'>{p['pick']}</span>** {home_away_tag} vs {opponent}", unsafe_allow_html=True)
            col2.markdown(f"<span style='color:{p['color']}'>{p['score']}/10 | +{p['edge']:.0f}%</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#888;font-size:0.85em'>{reasons_str}</span>", unsafe_allow_html=True)
    if tossups:
        st.markdown("### ⚪ TOSS-UP")
        for p in tossups:
            st.markdown(f"<span style='color:#888'>{p['away']}</span> ✈️ @ <span style='color:#888'>{p['home']}</span> 🏠 — <span style='color:{p['color']}'>{p['score']}/10</span> — No clear edge", unsafe_allow_html=True)
    if skips:
        st.markdown("### 🔴 SKIP")
        for p in skips:
            st.markdown(f"~~{p['away']} @ {p['home']}~~ — <span style='color:{p['color']}'>{p['score']}/10</span>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption(f"📊 {len(strong_buys)} Strong Buys | {len(buys)} Buys | {len(leans)} Leans | {len(tossups)} Toss-ups | {len(skips)} Skips")
else:
    st.info("No games scheduled today")

st.divider()

# ========== 🎯 TOTALS BIG SNAPSHOT ==========
st.subheader("🎯 TOTALS BIG SNAPSHOT - TODAY'S OVER/UNDER PICKS")

if game_list:
    all_totals = []
    for game_key in game_list:
        parts = game_key.split("@")
        away_team, home_team = parts[0], parts[1]
        pick, score, reasons = calc_totals_score(home_team, away_team, yesterday_teams, injuries)
        signal, color = get_totals_signal_tier(score, pick)
        all_totals.append({'game': game_key, 'home': home_team, 'away': away_team, 'pick': pick, 'score': score, 'signal': signal, 'color': color, 'reasons': reasons})
    all_totals.sort(key=lambda x: x['score'], reverse=True)
    strong_no = [p for p in all_totals if p['score'] >= 8.0 and p['pick'] == "NO"]
    strong_yes = [p for p in all_totals if p['score'] >= 8.0 and p['pick'] == "YES"]
    reg_no = [p for p in all_totals if 6.5 <= p['score'] < 8.0 and p['pick'] == "NO"]
    reg_yes = [p for p in all_totals if 6.5 <= p['score'] < 8.0 and p['pick'] == "YES"]
    lean_no = [p for p in all_totals if 5.5 <= p['score'] < 6.5 and p['pick'] == "NO"]
    lean_yes = [p for p in all_totals if 5.5 <= p['score'] < 6.5 and p['pick'] == "YES"]
    tossups_t = [p for p in all_totals if 4.5 <= p['score'] < 5.5]
    skips_t = [p for p in all_totals if p['score'] < 4.5]
    
    if strong_no:
        st.markdown("### 🟢 STRONG NO (Under)")
        for p in strong_no:
            reasons_str = " • ".join(p['reasons']) if p['reasons'] else "Multiple factors"
            col1, col2, col3, col4 = st.columns([3, 2, 4, 2])
            col1.markdown(f"**{p['away']}** @ **{p['home']}**")
            col2.markdown(f"<span style='color:{p['color']};font-weight:bold'>{p['score']}/10</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#aaa;font-size:0.9em'>{reasons_str}</span>", unsafe_allow_html=True)
            kalshi_url = build_kalshi_totals_url(p['away'], p['home'])
            col4.link_button(f"🔗 VIEW", kalshi_url)
    if strong_yes:
        st.markdown("### 🟢 STRONG YES (Over)")
        for p in strong_yes:
            reasons_str = " • ".join(p['reasons']) if p['reasons'] else "Multiple factors"
            col1, col2, col3, col4 = st.columns([3, 2, 4, 2])
            col1.markdown(f"**{p['away']}** @ **{p['home']}**")
            col2.markdown(f"<span style='color:{p['color']};font-weight:bold'>{p['score']}/10</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#aaa;font-size:0.9em'>{reasons_str}</span>", unsafe_allow_html=True)
            kalshi_url = build_kalshi_totals_url(p['away'], p['home'])
            col4.link_button(f"🔗 VIEW", kalshi_url)
    if reg_no:
        st.markdown("### 🔵 NO (Under)")
        for p in reg_no:
            reasons_str = " • ".join(p['reasons']) if p['reasons'] else "Multiple factors"
            col1, col2, col3, col4 = st.columns([3, 2, 4, 2])
            col1.markdown(f"**{p['away']}** @ **{p['home']}**")
            col2.markdown(f"<span style='color:{p['color']};font-weight:bold'>{p['score']}/10</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#aaa;font-size:0.9em'>{reasons_str}</span>", unsafe_allow_html=True)
            kalshi_url = build_kalshi_totals_url(p['away'], p['home'])
            col4.link_button(f"🔗 VIEW", kalshi_url)
    if reg_yes:
        st.markdown("### 🔵 YES (Over)")
        for p in reg_yes:
            reasons_str = " • ".join(p['reasons']) if p['reasons'] else "Multiple factors"
            col1, col2, col3, col4 = st.columns([3, 2, 4, 2])
            col1.markdown(f"**{p['away']}** @ **{p['home']}**")
            col2.markdown(f"<span style='color:{p['color']};font-weight:bold'>{p['score']}/10</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#aaa;font-size:0.9em'>{reasons_str}</span>", unsafe_allow_html=True)
            kalshi_url = build_kalshi_totals_url(p['away'], p['home'])
            col4.link_button(f"🔗 VIEW", kalshi_url)
    if lean_no:
        st.markdown("### 🟡 LEAN NO (Under)")
        for p in lean_no:
            reasons_str = " • ".join(p['reasons'][:3]) if p['reasons'] else ""
            col1, col2, col3 = st.columns([3, 2, 5])
            col1.markdown(f"{p['away']} @ {p['home']}")
            col2.markdown(f"<span style='color:{p['color']}'>{p['score']}/10</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#888;font-size:0.85em'>{reasons_str}</span>", unsafe_allow_html=True)
    if lean_yes:
        st.markdown("### 🟡 LEAN YES (Over)")
        for p in lean_yes:
            reasons_str = " • ".join(p['reasons'][:3]) if p['reasons'] else ""
            col1, col2, col3 = st.columns([3, 2, 5])
            col1.markdown(f"{p['away']} @ {p['home']}")
            col2.markdown(f"<span style='color:{p['color']}'>{p['score']}/10</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color:#888;font-size:0.85em'>{reasons_str}</span>", unsafe_allow_html=True)
    if tossups_t:
        st.markdown("### ⚪ TOSS-UP")
        for p in tossups_t:
            st.markdown(f"{p['away']} @ {p['home']} — <span style='color:{p['color']}'>{p['score']}/10</span> — No clear edge", unsafe_allow_html=True)
    if skips_t:
        st.markdown("### 🔴 SKIP")
        for p in skips_t:
            st.markdown(f"~~{p['away']} @ {p['home']}~~ — <span style='color:{p['color']}'>{p['score']}/10</span>", unsafe_allow_html=True)
    st.markdown("---")
    total_no = len(strong_no) + len(reg_no) + len(lean_no)
    total_yes = len(strong_yes) + len(reg_yes) + len(lean_yes)
    st.caption(f"📊 {len(strong_no)+len(strong_yes)} Strong | {len(reg_no)+len(reg_yes)} Regular | {len(lean_no)+len(lean_yes)} Leans | NO: {total_no} | YES: {total_yes}")
else:
    st.info("No games scheduled today")

st.divider()

if yesterday_teams:
    st.info(f"📅 **TRUE B2B Teams Today** (played yesterday + playing today): {', '.join(sorted(yesterday_teams))}")
else:
    st.info("📅 **No B2B teams today** — all teams are rested")

# ========== 🔥 TOP PICKS - BLOWOUT RISK ==========
st.subheader("🔥 TOP PICKS - BLOWOUT RISK (Tired Away @ Fresh Home)")

if game_list:
    top_picks = []
    for game_key in game_list:
        parts = game_key.split("@")
        away_t, home_t = parts[0], parts[1]
        away_b2b = away_t in yesterday_teams
        home_b2b = home_t in yesterday_teams
        if away_b2b and not home_b2b:
            away_r, home_r = 0, 1
            home_i, _ = get_injury_score(home_t, injuries)
            away_i, _ = get_injury_score(away_t, injuries)
            res = calc_12_factor_edge(home_t, away_t, home_r, away_r, home_i, away_i, 50)
            top_picks.append({'game': game_key, 'home_team': home_t, 'away_team': away_t, 'home_win_prob': res['home_win_prob'], 'spread': res['expected_spread']})
    top_picks.sort(key=lambda x: x['home_win_prob'], reverse=True)
    if top_picks:
        for pick in top_picks:
            st.markdown(f"<div style='background:linear-gradient(135deg,#1a1a2e,#16213e);padding:15px;border-radius:10px;border:2px solid #00ff00;margin-bottom:10px'><span style='color:#00ff00;font-size:1.8em;font-weight:bold'>🎯 {pick['home_team']} ML</span><span style='color:#00ff00;font-size:1.1em;margin-left:15px'>HIGH CONFIDENCE</span><br><span style='color:#aaa;font-size:0.9em'>{pick['game'].replace('@', ' @ ')} | {pick['home_team']} {pick['home_win_prob']:.0f}% to win (home, fresh) | 🔴 {pick['away_team']} B2B (tired)</span></div>", unsafe_allow_html=True)
    else:
        st.info("⚪ No BLOWOUT RISK games today — no tired away team @ fresh home matchups")
else:
    st.info("No games today")

st.divider()

# ========== ADD NEW POSITION (PAPER TRACKING) ==========
st.subheader("➕ ADD NEW POSITION (Paper Tracking)")

game_options = ["Select a game..."] + [gk.replace("@", " @ ") for gk in game_list]
selected_game = st.selectbox("🏀 Game", game_options, key="game_select")

if selected_game != "Select a game...":
    parts = selected_game.replace(" @ ", "@").split("@")
    away_t, home_t = parts[0], parts[1]
    col_ml, col_tot = st.columns(2)
    col_ml.link_button(f"🔗 ML on Kalshi", build_kalshi_ml_url(away_t, home_t), use_container_width=True)
    col_tot.link_button(f"🔗 Totals on Kalshi", build_kalshi_totals_url(away_t, home_t), use_container_width=True)

with st.form("add_position_form"):
    market_type = st.radio("📈 Market Type", ["Moneyline (Winner)", "Totals (Over/Under)"], horizontal=True)
    p1, p2, p3 = st.columns(3)
    if selected_game != "Select a game...":
        parts = selected_game.replace(" @ ", "@").split("@")
        ml_options = [f"{parts[1]} (Home)", f"{parts[0]} (Away)"]
    else:
        ml_options = ["Select game first"]
    totals_options = ["NO (Under)", "YES (Over)"]
    if market_type == "Moneyline (Winner)":
        side = p1.selectbox("📊 Pick Winner", ml_options)
    else:
        side = p1.selectbox("📊 Side", totals_options)
    price_paid = p2.number_input("💵 Price (¢)", min_value=1, max_value=99, value=50, step=1)
    contracts = p3.number_input("📄 Contracts", min_value=1, value=1, step=1)
    threshold_select = st.number_input("🎯 Threshold (Totals only)", min_value=180.0, max_value=280.0, value=225.5, step=0.5)
    add_btn = st.form_submit_button("✅ ADD POSITION", use_container_width=True)
    if add_btn and selected_game != "Select a game..." and side != "Select game first":
        game_key = selected_game.replace(" @ ", "@")
        parts = game_key.split("@")
        if market_type == "Moneyline (Winner)":
            team_pick = parts[1] if "Home" in side else parts[0]
            st.session_state.positions.append({'game': game_key, 'type': 'ml', 'pick': team_pick, 'price': price_paid, 'contracts': contracts, 'cost': round(price_paid * contracts / 100, 2)})
        else:
            side_clean = "NO" if "NO" in side else "YES"
            st.session_state.positions.append({'game': game_key, 'type': 'totals', 'side': side_clean, 'threshold': threshold_select, 'price': price_paid, 'contracts': contracts, 'cost': round(price_paid * contracts / 100, 2)})
        st.rerun()

st.divider()

# ========== ACTIVE POSITIONS ==========
st.subheader("📈 ACTIVE POSITIONS (Paper Tracking)")

if st.session_state.positions:
    for idx, pos in enumerate(st.session_state.positions):
        game_key = pos['game']
        g = games.get(game_key)
        price = pos.get('price', 50)
        contracts = pos.get('contracts', 1)
        cost = pos.get('cost', round(price * contracts / 100, 2))
        pos_type = pos.get('type', 'totals')
        potential_win = round((100 - price) * contracts / 100, 2)
        potential_loss = cost
        if g:
            total = g['total']
            mins = get_minutes_played(g['period'], g['clock'], g['status_type'])
            is_final = g['status_type'] == "STATUS_FINAL"
            game_status = "FINAL" if is_final else f"Q{g['period']} {g['clock']}"
            if pos_type == 'ml':
                pick = pos.get('pick', '')
                parts = game_key.split("@")
                away_team, home_team = parts[0], parts[1]
                home_score, away_score = g['home_score'], g['away_score']
                pick_score = home_score if pick == home_team else away_score
                opp_score = away_score if pick == home_team else home_score
                lead = pick_score - opp_score
                if is_final:
                    won = pick_score > opp_score
                    if won:
                        status_label, status_color = "✅ WON!", "#00ff00"
                        pnl_display, pnl_color = f"+${potential_win:.2f}", "#00ff00"
                    else:
                        status_label, status_color = "❌ LOST", "#ff0000"
                        pnl_display, pnl_color = f"-${potential_loss:.2f}", "#ff0000"
                elif mins > 0:
                    if lead >= 15: status_label, status_color = "🟢 CRUISING", "#00ff00"
                    elif lead >= 8: status_label, status_color = "🟢 LEADING", "#00ff00"
                    elif lead >= 1: status_label, status_color = "🟡 AHEAD", "#ffff00"
                    elif lead >= -5: status_label, status_color = "🟠 CLOSE", "#ff8800"
                    else: status_label, status_color = "🔴 BEHIND", "#ff0000"
                    pnl_display, pnl_color = f"Win: +${potential_win:.2f}", "#888888"
                else:
                    status_label, status_color = "⏳ WAITING", "#888888"
                    lead = 0
                    pnl_display, pnl_color = f"Win: +${potential_win:.2f}", "#888888"
                st.markdown(f"<div style='background:linear-gradient(135deg,#1a1a2e,#16213e);padding:15px;border-radius:10px;border:2px solid {status_color};margin-bottom:10px'><div style='display:flex;justify-content:space-between;align-items:center'><div><span style='color:#fff;font-size:1.2em;font-weight:bold'>{game_key.replace('@', ' @ ')}</span><span style='color:#888;margin-left:10px'>{game_status}</span></div><span style='color:{status_color};font-size:1.3em;font-weight:bold'>{status_label}</span></div><div style='margin-top:10px;display:flex;gap:30px;flex-wrap:wrap'><span style='color:#aaa'>🎯 <b style=\"color:#fff\">ML: {pick}</b></span><span style='color:#aaa'>💵 <b style=\"color:#fff\">{contracts}x @ {price}¢</b> (${cost:.2f})</span><span style='color:#aaa'>📊 Score: <b style=\"color:#fff\">{pick_score}-{opp_score}</b></span><span style='color:#aaa'>📈 Lead: <b style=\"color:{status_color}\">{lead:+d}</b></span><span style='color:{pnl_color}'>{pnl_display}</span></div></div>", unsafe_allow_html=True)
            else:
                projected = round((total / mins) * 48) if mins > 0 else None
                cushion = (pos['threshold'] - projected) if pos.get('side') == "NO" and projected else ((projected - pos['threshold']) if projected else 0)
                if is_final:
                    won = (total < pos['threshold']) if pos.get('side') == "NO" else (total > pos['threshold'])
                    if won:
                        status_label, status_color = "✅ WON!", "#00ff00"
                        pnl_display, pnl_color = f"+${potential_win:.2f}", "#00ff00"
                    else:
                        status_label, status_color = "❌ LOST", "#ff0000"
                        pnl_display, pnl_color = f"-${potential_loss:.2f}", "#ff0000"
                elif projected:
                    if cushion >= 15: status_label, status_color = "🟢 VERY SAFE", "#00ff00"
                    elif cushion >= 8: status_label, status_color = "🟢 LOOKING GOOD", "#00ff00"
                    elif cushion >= 3: status_label, status_color = "🟡 ON TRACK", "#ffff00"
                    elif cushion >= -3: status_label, status_color = "🟠 WARNING", "#ff8800"
                    else: status_label, status_color = "🔴 AT RISK", "#ff0000"
                    pnl_display, pnl_color = f"Win: +${potential_win:.2f}", "#888888"
                else:
                    status_label, status_color = "⏳ WAITING", "#888888"
                    pnl_display, pnl_color = f"Win: +${potential_win:.2f}", "#888888"
                st.markdown(f"<div style='background:linear-gradient(135deg,#1a1a2e,#16213e);padding:15px;border-radius:10px;border:2px solid {status_color};margin-bottom:10px'><div style='display:flex;justify-content:space-between;align-items:center'><div><span style='color:#fff;font-size:1.2em;font-weight:bold'>{game_key.replace('@', ' @ ')}</span><span style='color:#888;margin-left:10px'>{game_status}</span></div><span style='color:{status_color};font-size:1.3em;font-weight:bold'>{status_label}</span></div><div style='margin-top:10px;display:flex;gap:30px;flex-wrap:wrap'><span style='color:#aaa'>📊 <b style=\"color:#fff\">{pos.get('side', 'NO')} {pos.get('threshold', 0)}</b></span><span style='color:#aaa'>💵 <b style=\"color:#fff\">{contracts}x @ {price}¢</b> (${cost:.2f})</span><span style='color:#aaa'>📈 Proj: <b style=\"color:#fff\">{projected if projected else '—'}</b></span><span style='color:#aaa'>🎯 Cushion: <b style=\"color:{status_color}\">{cushion:+.0f}</b></span><span style='color:{pnl_color}'>{pnl_display}</span></div></div>", unsafe_allow_html=True)
            btn1, btn2 = st.columns([3, 1])
            parts = game_key.split("@")
            if pos_type == 'ml': kalshi_url = build_kalshi_ml_url(parts[0], parts[1])
            else: kalshi_url = build_kalshi_totals_url(parts[0], parts[1])
            btn1.link_button(f"🔗 View on Kalshi", kalshi_url, use_container_width=True)
            if btn2.button("🗑️ Remove", key=f"del_{idx}"):
                st.session_state.positions.pop(idx)
                st.rerun()
        else:
            if pos_type == 'ml': display_text = f"ML: {pos.get('pick', '?')}"
            else: display_text = f"{pos.get('side', 'NO')} {pos.get('threshold', 0)}"
            st.markdown(f"<div style='background:#1a1a2e;padding:15px;border-radius:10px;border:1px solid #444;margin-bottom:10px'><span style='color:#888'>{game_key.replace('@', ' @ ')} — {display_text} — {contracts}x @ {price}¢</span><span style='color:#666;margin-left:15px'>⏳ Game not started</span></div>", unsafe_allow_html=True)
            if st.button("🗑️ Remove", key=f"del_{idx}"):
                st.session_state.positions.pop(idx)
                st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear All Positions", use_container_width=True):
        st.session_state.positions = []
        st.rerun()
else:
    st.info("No positions tracked — use the form above to add your first paper position")

st.divider()

# ========== CUSHION SCANNER ==========
st.subheader("🎯 CUSHION SCANNER")

THRESHOLDS = [210.5, 215.5, 220.5, 225.5, 230.5, 235.5, 240.5, 245.5, 250.5, 255.5]

cs1, cs2 = st.columns([1, 1])
cush_side = cs1.selectbox("Side", ["NO", "YES"], key="cush_side")
auto_toggle = cs2.toggle("🔄 Auto-Refresh (30s)", value=st.session_state.auto_refresh, key="cush_auto")
if auto_toggle != st.session_state.auto_refresh:
    st.session_state.auto_refresh = auto_toggle
    st.rerun()

live_count = sum(1 for g in games.values() if g['status_type'] not in ["STATUS_FINAL", "STATUS_SCHEDULED"])
st.caption(f"📊 {len(games)} games | {live_count} live | Auto-shows all games with 6+ minutes")

cush_results = []

for gk, g in games.items():
    mins = get_minutes_played(g['period'], g['clock'], g['status_type'])
    total = g['total']
    if g['status_type'] == "STATUS_FINAL": continue
    if mins < 6: continue
    if mins <= 0: continue
    pace = total / mins
    remaining_min = max(48 - mins, 1)
    projected_final = round(total + pace * remaining_min)
    if cush_side == "NO":
        tight_line, safe_line = None, None
        for i, t in enumerate(THRESHOLDS):
            if t > projected_final:
                tight_line = t
                if i + 1 < len(THRESHOLDS): safe_line = THRESHOLDS[i + 1]
                else: safe_line = tight_line
                break
        if not tight_line:
            tight_line = THRESHOLDS[-1]
            safe_line = tight_line
        cushion = safe_line - projected_final
    else:
        tight_line, safe_line = None, None
        for i in range(len(THRESHOLDS) - 1, -1, -1):
            if THRESHOLDS[i] < projected_final:
                tight_line = THRESHOLDS[i]
                if i - 1 >= 0: safe_line = THRESHOLDS[i - 1]
                else: safe_line = tight_line
                break
        if not tight_line:
            tight_line = THRESHOLDS[0]
            safe_line = tight_line
        cushion = projected_final - safe_line
    if cushion < 6: continue
    if cush_side == "NO":
        if pace < 4.6: pace_status, pace_color = "✅ SLOW", "#00ff00"
        elif pace < 4.9: pace_status, pace_color = "⚠️ AVG", "#ffff00"
        else: pace_status, pace_color = "❌ FAST", "#ff0000"
    else:
        if pace > 5.1: pace_status, pace_color = "✅ FAST", "#00ff00"
        elif pace > 4.8: pace_status, pace_color = "⚠️ AVG", "#ffff00"
        else: pace_status, pace_color = "❌ SLOW", "#ff0000"
    cush_results.append({'game': gk, 'total': total, 'mins': mins, 'pace': pace, 'pace_status': pace_status, 'pace_color': pace_color, 'projected': projected_final, 'cushion': cushion, 'tight_line': tight_line, 'safe_line': safe_line, 'period': g['period'], 'clock': g['clock']})

cush_results.sort(key=lambda x: x['cushion'], reverse=True)

if cush_results:
    hcols = st.columns([2.5, 1, 1, 1, 1.5, 1.5, 1.5])
    hcols[0].markdown("**Game**")
    hcols[1].markdown("**Status**")
    hcols[2].markdown("**Total**")
    hcols[3].markdown("**Proj**")
    hcols[4].markdown("**🎯 BET LINE**")
    hcols[5].markdown("**Cushion**")
    hcols[6].markdown("**Pace**")
    for r in cush_results:
        rcols = st.columns([2.5, 1, 1, 1, 1.5, 1.5, 1.5])
        rcols[0].write(r['game'].replace("@", " @ "))
        rcols[1].write(f"Q{r['period']} {r['clock']} ({r['mins']:.0f}m)")
        rcols[2].write(f"{r['total']} pts")
        rcols[3].write(f"{r['projected']}")
        rcols[4].markdown(f"<span style='background:#ff8800;color:#000;padding:4px 8px;border-radius:4px;font-weight:bold'>{cush_side} {r['safe_line']}</span>", unsafe_allow_html=True)
        c = r['cushion']
        if c >= 20: rcols[5].markdown(f"<span style='color:#00ff00;font-weight:bold'>+{c:.0f} 🟢</span>", unsafe_allow_html=True)
        elif c >= 12: rcols[5].markdown(f"<span style='color:#88ff00;font-weight:bold'>+{c:.0f} 🟢</span>", unsafe_allow_html=True)
        elif c >= 6: rcols[5].markdown(f"<span style='color:#ffff00;font-weight:bold'>+{c:.0f} 🟡</span>", unsafe_allow_html=True)
        rcols[6].markdown(f"<span style='color:{r['pace_color']}'>{r['pace_status']}<br>{r['pace']:.2f}/m</span>", unsafe_allow_html=True)
    if cush_side == "NO": st.caption(f"📊 {len(cush_results)} NO opportunities | Safe line = tight line + 5 pts (higher = safer for under)")
    else: st.caption(f"📊 {len(cush_results)} YES opportunities | Safe line = tight line - 5 pts (lower = safer for over)")
else:
    st.info(f"⚪ No {cush_side} opportunities with +6 cushion yet — games appear automatically at 6+ minutes")

st.divider()

# ========== PACE SCANNER ==========
st.subheader("🔥 PACE SCANNER")

pace_data = []
for gk, g in games.items():
    mins = get_minutes_played(g['period'], g['clock'], g['status_type'])
    if mins >= 6:
        pace = round(g['total'] / mins, 2)
        proj = round(pace * 48)
        pace_data.append({"game": gk, "pace": pace, "proj": proj, "total": g['total'], "mins": mins, "period": g['period'], "clock": g['clock'], "final": g['status_type'] == "STATUS_FINAL"})

pace_data.sort(key=lambda x: x['pace'])

if pace_data:
    for p in pace_data:
        if p['pace'] < 4.5: lbl, clr = "🟢 SLOW", "#00ff00"
        elif p['pace'] < 4.8: lbl, clr = "🟡 AVG", "#ffff00"
        elif p['pace'] < 5.2: lbl, clr = "🟠 FAST", "#ff8800"
        else: lbl, clr = "🔴 SHOOTOUT", "#ff0000"
        status = "FINAL" if p['final'] else f"Q{p['period']} {p['clock']}"
        st.markdown(f"**{p['game'].replace('@', ' @ ')}** — {p['total']} pts in {p['mins']:.0f} min — **{p['pace']}/min** <span style='color:{clr}'>**{lbl}**</span> — Proj: **{p['proj']}** — {status}", unsafe_allow_html=True)
else:
    st.info("No games with 6+ minutes played yet")

st.divider()

# ========== ALL GAMES ==========
st.subheader("📺 ALL GAMES")
if games:
    cols = st.columns(4)
    for i, (k, g) in enumerate(games.items()):
        with cols[i % 4]:
            st.write(f"**{g['away_team']}** {g['away_score']}")
            st.write(f"**{g['home_team']}** {g['home_score']}")
            status = "FINAL" if g['status_type'] == "STATUS_FINAL" else f"Q{g['period']} {g['clock']}"
            st.caption(f"{status} | {g['total']} pts")
else:
    st.info("No games today")

st.divider()

# ========== HOW TO USE THIS APP ==========
st.subheader("📖 HOW TO USE THIS APP")
st.markdown("""
**🏥 Injury Report**
- Shows all injured players for today's games, sorted by star tier (⭐⭐⭐ Superstars → ⭐⭐ All-Stars → ⭐ Rotation)
- 🔥 = Offensive player, 🛡️ = Defensive player, ⚔️ = Two-way player
- OUT = Definitely not playing, GTD/DTD = Game-time decision

**🎯 ML Picks Big Snapshot**
- Ranks all games by moneyline edge using a 10-factor model
- 🟢 STRONG BUY (8+) → 🔵 BUY (6.5-7.9) → 🟡 LEAN (5.5-6.4) → ⚪ TOSS-UP → 🔴 SKIP
- Click "VIEW" to see the market on Kalshi

**🎯 Totals Big Snapshot**
- Ranks all games for over/under bets using pace, defense, B2B, injuries
- NO = Under the total, YES = Over the total
- Same tier system as ML picks

**🔥 Blowout Risk**
- Highlights games where a tired away team (B2B) faces a rested home team
- These situations often produce the highest-edge ML bets

**➕ Position Tracker (Paper Trading)**
- Track hypothetical positions without real money
- See live P&L projections as games progress
- Great for testing strategies before going live

**🎯 Cushion Scanner**
- For live games only (6+ minutes played)
- Shows NO/YES opportunities with safe cushion above projected totals
- Pace labels: 🟢 SLOW (<4.5/min) → 🟡 AVG → 🟠 FAST → 🔴 SHOOTOUT (>5.2/min)

**🔥 Pace Scanner**
- Quick view of all live game paces sorted slowest to fastest
- Use this to spot under/over opportunities in real-time

**📺 All Games**
- Simple scoreboard showing all today's games with live scores
""")

st.divider()
st.caption("⚠️ For entertainment only. Not financial advice. This is a READ-ONLY analysis tool.")
st.caption("TEST v15.9")
