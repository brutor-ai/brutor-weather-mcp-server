#!/usr/bin/env python3
"""
Weather Assistant using Model Context Protocol (MCP) with HTTP Transport
Runs as a remote MCP server listening on port 3012 using FastMCP

This implementation creates an MCP server that provides a weather tool.
"""
from dataclasses import dataclass
import httpx
import logging
import os

# Configure logging to reduce verbosity
logging.basicConfig(level=logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# FastMCP Imports (high-level)
from mcp.server.fastmcp import FastMCP

# Weather data structure (keeping your existing dataclass)
@dataclass
class WeatherData:
    temperature: float
    weather_code: int
    wind_speed: float
    latitude: float
    longitude: float
    location_name: str

# Get host and port from environment variables with defaults.
# Default port 3012 — part of the demo MCP server block
# (3010 mcp-app-map, 3011 fake-mcp, 3012 weather).
HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "3012"))

# Create FastMCP server instance
mcp = FastMCP(name="weather-assistant", host=HOST, port=PORT)

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """
    Gets the current weather in a given location by using external service. 
    Finds longitude and latitude for given city and fetches current temperature using Open-Meteo API.
    
    Args:
        city: Location of interest (city name)
        
    Returns:
        Weather information including temperature, conditions, and wind speed
    """
    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Geocoding - Find longitude and latitude for given city
            geocoding_url = "https://nominatim.openstreetmap.org/search"
            geocoding_params = {
                "q": city,
                "format": "json",
                "limit": 1
            }
            
            geocoding_response = await client.get(
                geocoding_url,
                params=geocoding_params,
                headers={"User-Agent": "MCP Weather Assistant"}
            )
            geocoding_response.raise_for_status()
            geocoding_data = geocoding_response.json()
            
            if not geocoding_data:
                return f"Could not find location data for '{city}'. Please check the city name and try again."
            
            # Extract coordinates
            latitude = float(geocoding_data[0]["lat"])
            longitude = float(geocoding_data[0]["lon"])
            display_name = geocoding_data[0]["display_name"]
            
            # Step 2: Fetch current temperature using Open-Meteo API
            # Using exact API call format from GPTScript example
            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current_weather": True,
                "hourly": "temperature_2m"
            }
            
            weather_response = await client.get(weather_url, params=weather_params)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            # Extract weather information
            current_weather = weather_data.get("current_weather", {})
            current_temp = current_weather.get("temperature", "N/A")
            weather_code = current_weather.get("weathercode", 0)
            wind_speed = current_weather.get("windspeed", "N/A")
            
            # Weather code descriptions
            weather_descriptions = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
                95: "Thunderstorm", 96: "Thunderstorm with hail"
            }
            
            weather_desc = weather_descriptions.get(weather_code, "Unknown conditions")
            
            # Format response
            result = f"""🌤️ Weather information for {display_name}:

🌡️ Current Temperature: {current_temp}°C
☁️ Weather Conditions: {weather_desc}
💨 Wind Speed: {wind_speed} km/h
📍 Coordinates: {latitude}, {longitude}"""
            
            return result
        
    except Exception as e:
        return f"Error fetching weather data: {str(e)}"

if __name__ == "__main__":
    """FastMCP handles all the server setup automatically"""

    try:
        print("🚀 Starting MCP Weather Server on streamable HTTP...")
        print("✅ Server instance created")
        print("🔧 Setting up FastMCP server...")
        print(f"📡 Server ready, starting MCP server on {HOST}:{PORT}...")
        print(f"🌐 MCP server will be available at: http://{HOST}:{PORT}")
        print()
        print("🔗 To connect from an MCP client, use:")
        print(f"   Transport: streamable-http")
        print(f"   URL: http://{HOST}:{PORT}")
        print()
        print("💡 Configure with environment variables:")
        print("   MCP_HOST (default: 0.0.0.0)")
        print("   MCP_PORT (default: 3012)")
        print()
        print("Press Ctrl+C to stop the server")
        
        # FastMCP handles asyncio and all protocol details automatically.
        # Use streamable HTTP transport on specified host:port
        mcp.run(transport="streamable-http")
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()