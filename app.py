import { useState, useEffect } from 'react';

const CITIES = {
  NYC: { lat: 40.7829, lon: -73.9654, name: "NYC (Central Park)", tz: "America/New_York" },
  Chicago: { lat: 41.8781, lon: -87.6298, name: "Chicago (O'Hare)", tz: "America/Chicago" },
  LA: { lat: 34.0522, lon: -118.2437, name: "Los Angeles", tz: "America/Los_Angeles" },
  Miami: { lat: 25.7617, lon: -80.1918, name: "Miami", tz: "America/New_York" },
  Denver: { lat: 39.7392, lon: -104.9903, name: "Denver", tz: "America/Denver" },
};

const getWindDirection = (deg) => {
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round(deg / 45) % 8];
};

export default function TempEdgeFinder() {
  const [city, setCity] = useState("NYC");
  const [weather, setWeather] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [morningLow, setMorningLow] = useState(null);
  const [showLegend, setShowLegend] = useState(false);

  const fetchWeather = async (cityKey) => {
    setLoading(true);
    const c = CITIES[cityKey];
    try {
      // Fetch current + today's forecast
      const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${c.lat}&longitude=${c.lon}&current=temperature_2m,cloud_cover,wind_speed_10m,wind_direction_10m&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=${c.tz}&forecast_days=1`);
      const data = await res.json();
      const cur = data.current || {};
      const daily = data.daily || {};
      
      setWeather({
        temp: cur.temperature_2m || 0,
        cloud: cur.cloud_cover || 0,
        wind: cur.wind_speed_10m || 0,
        windDir: cur.wind_direction_10m || 0,
      });
      
      setForecast({
        high: daily.temperature_2m_max?.[0] || 0,
        low: daily.temperature_2m_min?.[0] || 0,
      });
      
      setMorningLow(daily.temperature_2m_min?.[0] || 32);
    } catch (e) {
      setWeather(null);
      setForecast(null);
    }
    setLoading(false);
  };

  useEffect(() => { fetchWeather(city); }, [city]);

  // Calculate projected high
  const calculateProjection = () => {
    if (!weather || !forecast) return null;
    
    const now = new Date();
    const hour = now.getHours();
    const min = now.getMinutes();
    const currentTime = hour + min / 60;
    
    // Peak time based on cloud cover
    let peakHour = 16; // 4 PM default (clear)
    if (weather.cloud >= 70) peakHour = 14; // 2 PM (overcast)
    else if (weather.cloud >= 40) peakHour = 15; // 3 PM (partly cloudy)
    
    // If past peak, current temp IS near the high
    if (currentTime >= peakHour) {
      return {
        projected: weather.temp,
        method: "POST-PEAK",
        confidence: "HIGH",
        peakHour,
      };
    }
    
    // Hours since warming started (assume 7 AM)
    const warmingStart = 7;
    const hoursElapsed = Math.max(currentTime - warmingStart, 0.5);
    const hoursRemaining = peakHour - currentTime;
    
    // Current warming pace
    const tempRise = weather.temp - (morningLow || forecast.low);
    const pace = tempRise / hoursElapsed;
    
    // Project forward
    let projectedHigh = weather.temp + (pace * hoursRemaining);
    
    // Cloud cover dampening (clouds cap the high)
    if (weather.cloud >= 70) {
      projectedHigh = Math.min(projectedHigh, weather.temp + 3);
    } else if (weather.cloud >= 50) {
      projectedHigh = Math.min(projectedHigh, weather.temp + 5);
    }
    
    // Wind advection adjustment
    const windDir = getWindDirection(weather.windDir);
    if (["SW", "S"].includes(windDir) && weather.wind >= 8) {
      projectedHigh += 2; // Warm air advection
    } else if (["NW", "N", "NE"].includes(windDir) && weather.wind >= 8) {
      projectedHigh -= 2; // Cold air advection
    }
    
    // Confidence based on time
    let confidence = "LOW";
    if (currentTime >= 12) confidence = "HIGH";
    else if (currentTime >= 10.5) confidence = "MEDIUM";
    
    return {
      projected: Math.round(projectedHigh * 10) / 10,
      pace: Math.round(pace * 100) / 100,
      method: "PACE-FORWARD",
      confidence,
      peakHour,
      hoursRemaining: Math.round(hoursRemaining * 10) / 10,
    };
  };

  const projection = calculateProjection();
  
  // Generate bracket analysis
  const generateBrackets = () => {
    if (!projection || !forecast) return [];
    
    const proj = Math.round(projection.projected);
    const fcst = Math.round(forecast.high);
    const brackets = [];
    
    // Generate brackets around both projection and forecast
    const center = Math.round((proj + fcst) / 2);
    
    for (let i = -5; i <= 5; i++) {
      const low = center + i;
      const high = low + 1;
      const bracketMid = low + 0.5;
      
      // Distance from projection
      const distFromProj = Math.abs(bracketMid - projection.projected);
      const distFromFcst = Math.abs(bracketMid - forecast.high);
      
      // Edge exists when projection differs from forecast
      let edge = null;
      let side = null;
      
      if (projection.projected < low && forecast.high >= low) {
        // Projection below bracket, forecast in/above = NO edge
        edge = distFromProj;
        side = "NO";
      } else if (projection.projected > high && forecast.high <= high) {
        // Projection above bracket, forecast in/below = NO edge
        edge = distFromProj;
        side = "NO";
      } else if (Math.abs(projection.projected - bracketMid) < 1 && Math.abs(forecast.high - bracketMid) < 1) {
        // Both near bracket = YES possibility
        edge = 0;
        side = "YES";
      }
      
      brackets.push({
        low,
        high,
        distFromProj,
        distFromFcst,
        edge,
        side,
        isProjection: proj === low || proj === low + 1,
        isForecast: fcst === low || fcst === low + 1,
      });
    }
    
    return brackets;
  };

  const brackets = generateBrackets();

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold">🌡️ TEMP EDGE FINDER</h1>
          <button onClick={() => setShowLegend(!showLegend)} className="text-sm bg-gray-700 px-3 py-1 rounded">
            {showLegend ? "Hide" : "📖 How It Works"}
          </button>
        </div>
        
        {showLegend && (
          <div className="bg-gray-800 p-4 rounded mb-4 text-sm">
            <p className="font-bold mb-2">How Edge Finding Works:</p>
            <p className="mb-2">1. <strong>Open-Meteo Forecast</strong> = What the market is pricing</p>
            <p className="mb-2">2. <strong>Our Projection</strong> = Pace-based calculation from current conditions</p>
            <p className="mb-2">3. <strong>Edge</strong> = When they differ significantly</p>
            <p className="mt-3 text-yellow-400">If our projection is 42°F but forecast says 45°F, the 44-45 bracket is overpriced → NO edge</p>
          </div>
        )}

        <div className="mb-4">
          <select value={city} onChange={(e) => setCity(e.target.value)} className="bg-gray-700 rounded px-3 py-2 text-lg">
            {Object.keys(CITIES).map(c => <option key={c} value={c}>{CITIES[c].name}</option>)}
          </select>
        </div>

        {loading ? (
          <p>Loading weather data...</p>
        ) : weather && forecast ? (
          <>
            {/* Current Conditions */}
            <div className="bg-gray-800 p-4 rounded mb-4">
              <h2 className="font-bold mb-3 text-gray-400">CURRENT CONDITIONS</h2>
              <div className="grid grid-cols-4 gap-4">
                <div className="text-center">
                  <p className="text-3xl font-bold">{weather.temp.toFixed(1)}°F</p>
                  <p className="text-xs text-gray-400">Now</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold">{weather.cloud}%</p>
                  <p className="text-xs text-gray-400">Clouds</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold">{weather.wind.toFixed(0)} mph</p>
                  <p className="text-xs text-gray-400">Wind</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold">{getWindDirection(weather.windDir)}</p>
                  <p className="text-xs text-gray-400">Direction</p>
                </div>
              </div>
            </div>

            {/* Projection vs Forecast */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-blue-900/50 border border-blue-500 p-4 rounded">
                <p className="text-xs text-blue-300 mb-1">MARKET FORECAST (Open-Meteo)</p>
                <p className="text-4xl font-bold">{forecast.high.toFixed(0)}°F</p>
                <p className="text-xs text-gray-400 mt-1">What Kalshi is likely pricing</p>
              </div>
              <div className="bg-green-900/50 border border-green-500 p-4 rounded">
                <p className="text-xs text-green-300 mb-1">OUR PROJECTION</p>
                <p className="text-4xl font-bold">{projection?.projected.toFixed(1)}°F</p>
                <p className="text-xs text-gray-400 mt-1">{projection?.confidence} confidence • {projection?.method}</p>
              </div>
            </div>

            {/* Edge Alert */}
            {projection && Math.abs(projection.projected - forecast.high) >= 2 && (
              <div className="bg-yellow-900/50 border border-yellow-500 p-4 rounded mb-4">
                <p className="text-xl font-bold text-yellow-400">
                  ⚡ {Math.abs(projection.projected - forecast.high).toFixed(1)}°F GAP DETECTED
                </p>
                <p className="text-sm mt-1">
                  {projection.projected < forecast.high 
                    ? `Projection BELOW forecast → Look for NO on ${Math.round(forecast.high)-1}-${Math.round(forecast.high)}°F brackets`
                    : `Projection ABOVE forecast → Look for NO on ${Math.round(forecast.high)}-${Math.round(forecast.high)+1}°F brackets`
                  }
                </p>
              </div>
            )}

            {/* Projection Details */}
            {projection && (
              <div className="bg-gray-800 p-4 rounded mb-4">
                <h2 className="font-bold mb-3 text-gray-400">PROJECTION DETAILS</h2>
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-lg font-bold">{projection.pace?.toFixed(2) || "—"}°F/hr</p>
                    <p className="text-xs text-gray-400">Warming Pace</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold">{projection.hoursRemaining || "—"}h</p>
                    <p className="text-xs text-gray-400">Until Peak</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold">{projection.peakHour}:00</p>
                    <p className="text-xs text-gray-400">Est. Peak Time</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold">{morningLow?.toFixed(0)}°F</p>
                    <p className="text-xs text-gray-400">Morning Low</p>
                  </div>
                </div>
              </div>
            )}

            {/* Bracket Scanner */}
            <div className="bg-gray-800 p-4 rounded">
              <h2 className="font-bold mb-3 text-gray-400">BRACKET SCANNER</h2>
              <div className="overflow-x-auto">
                <div className="flex gap-2 min-w-max">
                  {brackets.map((b, i) => {
                    let bgColor = "bg-gray-700";
                    let borderColor = "border-gray-600";
                    
                    if (b.isProjection) {
                      bgColor = "bg-green-900/50";
                      borderColor = "border-green-500";
                    } else if (b.isForecast) {
                      bgColor = "bg-blue-900/50";
                      borderColor = "border-blue-500";
                    }
                    
                    if (b.edge && b.edge >= 2) {
                      bgColor = "bg-yellow-900/50";
                      borderColor = "border-yellow-500";
                    }
                    
                    return (
                      <div key={i} className={`${bgColor} border ${borderColor} p-3 rounded min-w-[80px] text-center`}>
                        <p className="font-bold">{b.low}-{b.high}°F</p>
                        {b.isProjection && <p className="text-xs text-green-400">📍 PROJ</p>}
                        {b.isForecast && <p className="text-xs text-blue-400">📊 FCST</p>}
                        {b.edge >= 2 && b.side && (
                          <p className="text-xs text-yellow-400 font-bold mt-1">⚡ {b.side}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="flex gap-4 mt-3 text-xs text-gray-400">
                <span>📍 Green = Our projection</span>
                <span>📊 Blue = Market forecast</span>
                <span>⚡ Yellow = Edge opportunity</span>
              </div>
            </div>
          </>
        ) : (
          <p className="text-red-500">Failed to fetch weather data</p>
        )}
      </div>
    </div>
  );
}
