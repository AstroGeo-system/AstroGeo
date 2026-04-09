import requests
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import os
from dotenv import load_dotenv
import warnings

# Suppress urllib3 OpenSSL warning
warnings.filterwarnings("ignore", module="urllib3")
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://khushikhanna@localhost:5432/astrogeo_db')
engine = create_engine(DATABASE_URL)

print("="*70)
print("WEATHER AGENT: FETCHING DATA FROM OPEN-METEO")
print("="*70)

# ============================================================================
# STEP 1: GET LOCATIONS FROM DATABASE
# ============================================================================

print("\n[1/5] Loading locations from database...")

with engine.connect() as conn:
    conn.execute(text("SET search_path TO shared"))
    
    result = conn.execute(text("""
        SELECT location_id, name, latitude, longitude
        FROM locations
        ORDER BY name
    """))
    
    locations = [dict(row._mapping) for row in result]

print(f"✅ Found {len(locations)} locations:")
for loc in locations:
    print(f"  • {loc['name']}: {loc['latitude']:.4f}°N, {loc['longitude']:.4f}°E")

# ============================================================================
# STEP 2: FETCH WEATHER FROM OPEN-METEO API
# ============================================================================

print("\n[2/5] Fetching weather data from Open-Meteo API...")

def fetch_weather_for_location(location):
    """
    Fetch current weather and forecasts from Open-Meteo
    
    API Documentation: https://open-meteo.com/en/docs
    """
    
    lat = location['latitude']
    lon = location['longitude']
    location_id = location['location_id']
    location_name = location['name']
    
    # Open-Meteo API endpoint
    url = "https://api.open-meteo.com/v1/forecast"
    
    # Parameters
    params = {
        'latitude': lat,
        'longitude': lon,
        'current': [
            'temperature_2m',
            'relative_humidity_2m',
            'apparent_temperature',
            'is_day',
            'precipitation',
            'weather_code',
            'cloud_cover',
            'pressure_msl',
            'wind_speed_10m',
            'wind_direction_10m',
            'wind_gusts_10m'
        ],
        'hourly': [
            'temperature_2m',
            'relative_humidity_2m',
            'apparent_temperature',
            'precipitation_probability',
            'precipitation',
            'weather_code',
            'cloud_cover',
            'visibility',
            'wind_speed_10m',
            'wind_direction_10m',
            'wind_gusts_10m',
            'is_day'
        ],
        'daily': [
            'weather_code',
            'temperature_2m_max',
            'temperature_2m_min',
            'apparent_temperature_max',
            'apparent_temperature_min',
            'sunrise',
            'sunset',
            'daylight_duration',
            'precipitation_sum',
            'precipitation_hours',
            'precipitation_probability_max',
            'wind_speed_10m_max',
            'wind_gusts_10m_max',
            'wind_direction_10m_dominant'
        ],
        'timezone': 'Asia/Kolkata',
        'forecast_days': 7
    }
    
    try:
        print(f"\n  Fetching: {location_name}...", end=" ")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print("✅")
        
        return {
            'location_id': location_id,
            'location_name': location_name,
            'data': data,
            'success': True,
            'error': None
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return {
            'location_id': location_id,
            'location_name': location_name,
            'data': None,
            'success': False,
            'error': str(e)
        }

# Fetch weather for all locations
weather_data = []
for location in locations:
    result = fetch_weather_for_location(location)
    weather_data.append(result)

successful = sum(1 for w in weather_data if w['success'])
print(f"\n✅ Successfully fetched: {successful}/{len(locations)} locations")

# ============================================================================
# STEP 3: PARSE AND STORE CURRENT CONDITIONS
# ============================================================================

print("\n[3/5] Storing current conditions...")

with engine.connect() as conn:
    conn.execute(text("SET search_path TO weather"))
    
    for weather in weather_data:
        if not weather['success']:
            continue
        
        data = weather['data']
        current = data.get('current', {})
        
        # Parse current conditions
        observed_at = current.get('time')
        temperature = current.get('temperature_2m')
        feels_like = current.get('apparent_temperature')
        humidity = current.get('relative_humidity_2m')
        pressure = current.get('pressure_msl')
        cloud_cover = current.get('cloud_cover', 0)
        precipitation = current.get('precipitation', 0)
        wind_speed = current.get('wind_speed_10m')
        wind_direction = current.get('wind_direction_10m')
        wind_gust = current.get('wind_gusts_10m')
        weather_code = current.get('weather_code')
        is_day = current.get('is_day', 0) == 1
        
        # Get sunrise/sunset from daily data
        daily = data.get('daily', {})
        sunrise = daily.get('sunrise', [None])[0] if daily.get('sunrise') else None
        sunset = daily.get('sunset', [None])[0] if daily.get('sunset') else None
        
        # Weather description from code
        weather_descriptions = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail"
        }
        weather_desc = weather_descriptions.get(weather_code, "Unknown")
        
        # Insert current conditions
        conn.execute(text("""
            INSERT INTO current_conditions (
                location_id, observed_at, temperature_celsius, feels_like_celsius,
                humidity_percent, pressure_hpa, cloud_cover_percent, precipitation_mm,
                wind_speed_kmh, wind_direction_deg, wind_gust_kmh,
                weather_code, weather_description, is_day,
                sunrise_time, sunset_time, data_source
            ) VALUES (
                :location_id, :observed_at, :temp, :feels_like,
                :humidity, :pressure, :cloud_cover, :precip,
                :wind_speed, :wind_dir, :wind_gust,
                :weather_code, :weather_desc, :is_day,
                :sunrise, :sunset, 'Open-Meteo'
            )
        """), {
            'location_id': weather['location_id'],
            'observed_at': observed_at,
            'temp': temperature,
            'feels_like': feels_like,
            'humidity': humidity,
            'pressure': pressure,
            'cloud_cover': cloud_cover,
            'precip': precipitation,
            'wind_speed': wind_speed,
            'wind_dir': wind_direction,
            'wind_gust': wind_gust,
            'weather_code': weather_code,
            'weather_desc': weather_desc,
            'is_day': is_day,
            'sunrise': sunrise,
            'sunset': sunset
        })
        
        print(f"  ✅ {weather['location_name']}: {temperature}°C, {cloud_cover}% clouds, {weather_desc}")
    
    conn.commit()

print(f"\n✅ Current conditions stored for {successful} locations")

# ============================================================================
# STEP 4: STORE HOURLY FORECAST
# ============================================================================

print("\n[4/5] Storing hourly forecasts (next 24 hours)...")

with engine.connect() as conn:
    conn.execute(text("SET search_path TO weather"))
    
    hourly_count = 0
    
    for weather in weather_data:
        if not weather['success']:
            continue
        
        data = weather['data']
        hourly = data.get('hourly', {})
        
        times = hourly.get('time', [])
        
        # Store next 24 hours only (first 24 entries)
        for i in range(min(24, len(times))):
            forecast_time = times[i]
            
            conn.execute(text("""
                INSERT INTO hourly_forecast (
                    location_id, forecast_time,
                    temperature_celsius, apparent_temperature_celsius,
                    cloud_cover_percent, visibility_km,
                    precipitation_mm, precipitation_probability,
                    humidity_percent, pressure_hpa,
                    wind_speed_kmh, wind_direction_deg, wind_gusts_kmh,
                    weather_code, is_day,
                    generated_at, data_source
                ) VALUES (
                    :location_id, :forecast_time,
                    :temp, :apparent_temp,
                    :cloud_cover, :visibility,
                    :precip, :precip_prob,
                    :humidity, :pressure,
                    :wind_speed, :wind_dir, :wind_gust,
                    :weather_code, :is_day,
                    NOW(), 'Open-Meteo'
                )
                ON CONFLICT (location_id, forecast_time, generated_at) DO NOTHING
            """), {
                'location_id': weather['location_id'],
                'forecast_time': forecast_time,
                'temp': hourly['temperature_2m'][i],
                'apparent_temp': hourly['apparent_temperature'][i],
                'cloud_cover': hourly['cloud_cover'][i],
                'visibility': hourly.get('visibility', [None])[i],
                'precip': hourly['precipitation'][i],
                'precip_prob': hourly.get('precipitation_probability', [None])[i],
                'humidity': hourly['relative_humidity_2m'][i],
                'pressure': None,  # Not in hourly
                'wind_speed': hourly['wind_speed_10m'][i],
                'wind_dir': hourly['wind_direction_10m'][i],
                'wind_gust': hourly['wind_gusts_10m'][i],
                'weather_code': hourly['weather_code'][i],
                'is_day': hourly['is_day'][i] == 1
            })
            
            hourly_count += 1
    
    conn.commit()

print(f"✅ Stored {hourly_count} hourly forecasts")

# ============================================================================
# STEP 5: CALCULATE OBSERVATION QUALITY SCORES
# ============================================================================

print("\n[5/5] Calculating observation quality scores...")

with engine.connect() as conn:
    conn.execute(text("SET search_path TO weather"))
    
    # Calculate for current conditions
    result = conn.execute(text("""
        INSERT INTO observation_quality (
            location_id,
            datetime,
            overall_quality_score,
            cloud_score,
            visibility_score,
            stability_score,
            quality_category,
            suitable_for_astronomy,
            cloud_cover_percent,
            visibility_km,
            wind_speed_kmh,
            precipitation_mm,
            quality_description,
            is_forecast,
            confidence_score
        )
        SELECT 
            location_id,
            observed_at as datetime,
            calculate_observation_score(
                cloud_cover_percent, 
                10.0,  -- Default visibility
                wind_speed_kmh, 
                precipitation_mm
            ) as overall_quality_score,
            GREATEST(0, 100 - cloud_cover_percent) as cloud_score,
            50 as visibility_score,  -- Default
            CASE 
                WHEN wind_speed_kmh < 10 THEN 100
                WHEN wind_speed_kmh < 20 THEN 70
                WHEN wind_speed_kmh < 30 THEN 40
                ELSE 10
            END as stability_score,
            CASE 
                WHEN calculate_observation_score(cloud_cover_percent, 10.0, wind_speed_kmh, precipitation_mm) >= 80 THEN 'Excellent'
                WHEN calculate_observation_score(cloud_cover_percent, 10.0, wind_speed_kmh, precipitation_mm) >= 60 THEN 'Good'
                WHEN calculate_observation_score(cloud_cover_percent, 10.0, wind_speed_kmh, precipitation_mm) >= 40 THEN 'Fair'
                WHEN calculate_observation_score(cloud_cover_percent, 10.0, wind_speed_kmh, precipitation_mm) >= 20 THEN 'Poor'
                ELSE 'Unsuitable'
            END as quality_category,
            CASE 
                WHEN cloud_cover_percent < 40 AND precipitation_mm = 0 THEN true
                ELSE false
            END as suitable_for_astronomy,
            cloud_cover_percent,
            NULL as visibility_km,
            wind_speed_kmh,
            precipitation_mm,
            CASE 
                WHEN cloud_cover_percent < 20 AND precipitation_mm = 0 THEN 'Excellent: Clear skies, perfect for observation'
                WHEN cloud_cover_percent < 40 AND precipitation_mm = 0 THEN 'Good: Mostly clear, good viewing conditions'
                WHEN cloud_cover_percent < 60 THEN 'Fair: Partly cloudy, some viewing possible'
                WHEN precipitation_mm > 0 THEN 'Unsuitable: Precipitation blocking view'
                ELSE 'Poor: Heavy cloud cover'
            END as quality_description,
            false as is_forecast,
            0.9 as confidence_score
        FROM current_conditions
        WHERE observed_at >= NOW() - INTERVAL '1 hour'
        ON CONFLICT (location_id, datetime) 
        DO UPDATE SET
            overall_quality_score = EXCLUDED.overall_quality_score,
            quality_category = EXCLUDED.quality_category,
            suitable_for_astronomy = EXCLUDED.suitable_for_astronomy,
            quality_description = EXCLUDED.quality_description
    """))
    
    conn.commit()

print("✅ Observation quality scores calculated")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*70)
print("VERIFICATION: CURRENT OBSERVATION CONDITIONS")
print("="*70)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            location_name,
            ROUND(temperature_celsius::numeric, 1) as temp_c,
            ROUND(cloud_cover_percent::numeric, 0) as clouds,
            weather_description,
            quality_category,
            suitable_for_astronomy,
            is_currently_night
        FROM weather.current_observation_conditions
        ORDER BY location_name
    """))
    
    print("\n")
    for row in result:
        night_indicator = "🌙" if row.is_currently_night else "☀️"
        suitable = "✅" if row.suitable_for_astronomy else "❌"
        
        print(f"{night_indicator} {row.location_name}:")
        print(f"   Temp: {row.temp_c}°C | Clouds: {row.clouds}% | {row.weather_description}")
        print(f"   Quality: {row.quality_category} {suitable} {'(Good for viewing!)' if row.suitable_for_astronomy else '(Not suitable)'}")
        print()

print("="*70)
print("✅ WEATHER DATA SUCCESSFULLY FETCHED AND STORED!")
print("="*70)
print("\nNext steps:")
print("1. Set up automated updates (hourly)")
print("2. Add daily forecast storage")
print("3. Integrate with Astronomy Agent")
print("="*70)