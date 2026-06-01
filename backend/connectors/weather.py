from __future__ import annotations
import httpx
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

WMO_CODES = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
             61: "Light rain", 63: "Rain", 65: "Heavy rain", 80: "Showers",
             95: "Thunderstorm", 96: "Thunderstorm + hail"}


class WeatherConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._lat = cfg.connectors.weather.latitude
        self._lon = cfg.connectors.weather.longitude
        self._name = cfg.connectors.weather.location_name

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        try:
            await self.current()
            return HealthResult("weather", True)
        except Exception as e:
            return HealthResult("weather", False, str(e))

    async def current(self) -> dict:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={self._lat}&longitude={self._lon}"
               f"&current_weather=true&hourly=relative_humidity_2m&timezone=Asia%2FBangkok")
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
        cw = data["current_weather"]
        code = cw.get("weathercode", 0)
        desc = WMO_CODES.get(code, f"Code {code}")
        return {
            "location": self._name,
            "temp_c": cw["temperature"],
            "wind_kmh": cw["windspeed"],
            "description": desc,
        }
