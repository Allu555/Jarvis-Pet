import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Optional, Callable, List


class WeatherInfo:
    def __init__(
        self,
        temp_c: int = 24,
        condition: str = "Clear Sky",
        city: str = "Kochi, Kerala, India",
        humidity: str = "60%",
        wind_speed: str = "10 km/h",
        feels_like: int = 24,
        icon_type: str = "sun"
    ):
        self.temp_c = temp_c
        self.temp_f = int(temp_c * 9 / 5 + 32)
        self.condition = condition
        self.city = city
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.feels_like = feels_like
        self.icon_type = icon_type

    @property
    def display_temp(self) -> str:
        return f"{self.temp_c}°C"

    @property
    def display_summary(self) -> str:
        return f"{self.temp_c}°C • {self.condition}"

    def __repr__(self) -> str:
        return f"<WeatherInfo {self.city}: {self.temp_c}°C {self.condition}>"


def _map_condition_to_icon(condition: str, is_night: bool = False, temp_c: int = 24, wind_kmph: int = 10) -> str:
    c_lower = condition.lower()
    if any(k in c_lower for k in ["thunder", "lightning", "storm", "cyclone", "tornado"]):
        return "thunder"
    # Only active actual rain triggers rain animation (exclude 'nearby' / 'possible' / 'patchy')
    elif any(k in c_lower for k in ["heavy rain", "moderate rain", "light rain", "torrential", "pouring", "downpour", "shower", "drizzle", "raining"]):
        return "rain"
    elif "rain" in c_lower and not any(k in c_lower for k in ["nearby", "possible", "chance", "patchy"]):
        return "rain"
    elif any(k in c_lower for k in ["snow", "sleet", "ice", "blizzard", "frost", "freezing"]):
        return "snow"
    elif wind_kmph >= 25 or any(k in c_lower for k in ["wind", "gale", "breezy", "gust"]):
        return "wind"
    elif any(k in c_lower for k in ["cloud", "overcast", "fog", "mist", "haze", "patchy", "smoke", "nearby", "possible", "chance"]):
        return "cloud"
    elif not is_night and (temp_c >= 32 or any(k in c_lower for k in ["hot", "heat", "scorching", "very warm"])):
        return "hot"
    elif is_night:
        return "night"
    else:
        return "sun"


class WeatherService:
    """
    Singleton background service fetching real-time global weather via IP geolocation or custom city.
    Updates every 15 minutes automatically without blocking the UI.
    """
    _instance: Optional['WeatherService'] = None

    @classmethod
    def get_instance(cls) -> 'WeatherService':
        if cls._instance is None:
            cls._instance = WeatherService()
        return cls._instance

    def __init__(self, location: str = "Kochi, Kerala, India"):
        self._location: str = location
        self._current_weather: WeatherInfo = WeatherInfo(city=location)
        self._lock = threading.Lock()
        self._running = True
        self._listeners: List[Callable[[WeatherInfo], None]] = []
        
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="WeatherServiceWorker")
        self._thread.start()

    def set_location(self, location: str):
        if not location:
            return
        with self._lock:
            if self._location == location:
                return
            self._location = location
        # Trigger immediate refresh in background
        threading.Thread(target=self._fetch_weather, daemon=True).start()

    def get_location(self) -> str:
        with self._lock:
            return self._location

    def add_listener(self, callback: Callable[[WeatherInfo], None]):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[WeatherInfo], None]):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def get_weather(self) -> WeatherInfo:
        with self._lock:
            return self._current_weather

    @property
    def current_weather(self) -> WeatherInfo:
        with self._lock:
            return self._current_weather

    def _notify(self, info: WeatherInfo):
        for cb in list(self._listeners):
            try:
                cb(info)
            except Exception:
                pass

    def _worker_loop(self):
        # Initial fetch immediately
        self._fetch_weather()
        
        # Periodic refresh every 15 minutes
        while self._running:
            time.sleep(900)
            self._fetch_weather()

    def _fetch_weather(self):
        try:
            with self._lock:
                loc = self._location

            if loc and loc.strip():
                # Extract primary city for wttr.in query (e.g. "Kochi" from "Kochi, Kerala, India")
                query_loc = loc.split(",")[0].strip()
                url = f"https://wttr.in/{urllib.parse.quote(query_loc)}?format=j1"
            else:
                url = "https://wttr.in/?format=j1"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "curl/7.68.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                if response.status == 200:
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw)
                    
                    cur = data.get("current_condition", [{}])[0]
                    nearest = data.get("nearest_area", [{}])[0]
                    
                    temp_c = int(cur.get("temp_C", 26))
                    feels_c = int(cur.get("FeelsLikeC", temp_c))
                    condition = cur.get("weatherDesc", [{}])[0].get("value", "Partly Cloudy").strip()
                    humidity = f"{cur.get('humidity', '75')}%"
                    wind_kmph = int(cur.get("windspeedKmph", 12))
                    wind = f"{wind_kmph} km/h"

                    if loc and loc.strip():
                        city = loc
                    else:
                        area_name = nearest.get("areaName", [{}])[0].get("value", "")
                        country = nearest.get("country", [{}])[0].get("value", "")
                        city = f"{area_name}, {country}" if (area_name and country) else (area_name or "Local")

                    # Check current hour for day/night
                    cur_hour = time.localtime().tm_hour
                    is_night = cur_hour < 6 or cur_hour >= 19
                    icon_type = _map_condition_to_icon(condition, is_night, temp_c=temp_c, wind_kmph=wind_kmph)

                    new_info = WeatherInfo(
                        temp_c=temp_c,
                        condition=condition,
                        city=city,
                        humidity=humidity,
                        wind_speed=wind,
                        feels_like=feels_c,
                        icon_type=icon_type
                    )

                    with self._lock:
                        self._current_weather = new_info

                    self._notify(new_info)
        except Exception:
            pass

