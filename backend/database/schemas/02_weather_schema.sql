-- ============================================================================
-- WEATHER AGENT DATABASE SCHEMA
-- ============================================================================

-- Create weather schema
CREATE SCHEMA IF NOT EXISTS weather;

-- Add comment
COMMENT ON SCHEMA weather IS 'Weather and atmospheric conditions data for observation planning';

-- Set search path
SET search_path TO weather;

-- ============================================================================
-- TABLE 1: CURRENT CONDITIONS
-- ============================================================================

CREATE TABLE current_conditions (
    id SERIAL PRIMARY KEY,
    
    -- Location reference
    location_id VARCHAR(100) NOT NULL,
    
    -- Timestamp
    observed_at TIMESTAMPTZ NOT NULL,
    
    -- Temperature
    temperature_celsius FLOAT,
    feels_like_celsius FLOAT,
    
    -- Humidity & Pressure
    humidity_percent FLOAT,
    pressure_hpa FLOAT,
    dew_point_celsius FLOAT,
    
    -- Cloud & Visibility (CRITICAL for astronomy)
    cloud_cover_percent FLOAT NOT NULL,  -- 0-100, most important!
    visibility_km FLOAT,                  -- How far you can see
    
    -- Precipitation
    precipitation_mm FLOAT,               -- Current rain/snow
    precipitation_probability FLOAT,      -- Chance of rain (0-100)
    
    -- Wind
    wind_speed_kmh FLOAT,
    wind_gust_kmh FLOAT,
    wind_direction_deg FLOAT,             -- 0-360 degrees
    
    -- Sky condition
    weather_code INTEGER,                 -- WMO weather code
    weather_description TEXT,             -- "Clear sky", "Partly cloudy", etc.
    is_day BOOLEAN,                       -- Day or night
    
    -- Sun times (for viewing windows)
    sunrise_time TIMESTAMPTZ,
    sunset_time TIMESTAMPTZ,
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'Open-Meteo',
    api_response_code INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_location FOREIGN KEY (location_id) 
        REFERENCES shared.locations(location_id) ON DELETE CASCADE,
    CONSTRAINT valid_cloud_cover CHECK (cloud_cover_percent BETWEEN 0 AND 100),
    CONSTRAINT valid_humidity CHECK (humidity_percent IS NULL OR humidity_percent BETWEEN 0 AND 100),
    CONSTRAINT valid_wind_dir CHECK (wind_direction_deg IS NULL OR wind_direction_deg BETWEEN 0 AND 360)
);

-- Indexes
CREATE INDEX idx_current_location ON current_conditions(location_id);
CREATE INDEX idx_current_time ON current_conditions(observed_at DESC);
CREATE INDEX idx_current_location_time ON current_conditions(location_id, observed_at DESC);

-- Comment
COMMENT ON TABLE current_conditions IS 
'Real-time weather conditions updated hourly. Cloud cover and visibility are critical for astronomy observations.';

-- ============================================================================
-- TABLE 2: HOURLY FORECAST
-- ============================================================================

CREATE TABLE hourly_forecast (
    id SERIAL PRIMARY KEY,
    
    -- Location & Time
    location_id VARCHAR(100) NOT NULL,
    forecast_time TIMESTAMPTZ NOT NULL,
    
    -- Temperature
    temperature_celsius FLOAT,
    apparent_temperature_celsius FLOAT,  -- Feels like
    
    -- Cloud & Visibility
    cloud_cover_percent FLOAT NOT NULL,
    visibility_km FLOAT,
    
    -- Precipitation
    precipitation_mm FLOAT,
    precipitation_probability FLOAT,     -- 0-100%
    rain_mm FLOAT,
    snow_mm FLOAT,
    
    -- Wind
    wind_speed_kmh FLOAT,
    wind_gusts_kmh FLOAT,
    wind_direction_deg FLOAT,
    
    -- Atmospheric
    humidity_percent FLOAT,
    pressure_hpa FLOAT,
    
    -- Sky condition
    weather_code INTEGER,
    is_day BOOLEAN,
    
    -- Forecast metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),  -- When this forecast was created
    data_source VARCHAR(50) DEFAULT 'Open-Meteo',
    
    -- Constraints
    CONSTRAINT fk_hourly_location FOREIGN KEY (location_id) 
        REFERENCES shared.locations(location_id) ON DELETE CASCADE,
    CONSTRAINT valid_hourly_clouds CHECK (cloud_cover_percent BETWEEN 0 AND 100),
    CONSTRAINT unique_hourly_forecast UNIQUE (location_id, forecast_time, generated_at)
);

-- Indexes
CREATE INDEX idx_hourly_location ON hourly_forecast(location_id);
CREATE INDEX idx_hourly_time ON hourly_forecast(forecast_time);
CREATE INDEX idx_hourly_location_time ON hourly_forecast(location_id, forecast_time);
CREATE INDEX idx_hourly_clouds ON hourly_forecast(cloud_cover_percent) WHERE cloud_cover_percent < 30;

-- Comment
COMMENT ON TABLE hourly_forecast IS 
'Hourly weather forecasts for next 7 days. Updated every 6 hours. Essential for planning observations.';

-- ============================================================================
-- TABLE 3: DAILY FORECAST
-- ============================================================================

CREATE TABLE daily_forecast (
    id SERIAL PRIMARY KEY,
    
    -- Location & Date
    location_id VARCHAR(100) NOT NULL,
    forecast_date DATE NOT NULL,
    
    -- Temperature
    temperature_max_celsius FLOAT,
    temperature_min_celsius FLOAT,
    apparent_temperature_max_celsius FLOAT,
    apparent_temperature_min_celsius FLOAT,
    
    -- Cloud cover (daily average/max)
    cloud_cover_avg_percent FLOAT,
    cloud_cover_max_percent FLOAT,
    
    -- Precipitation
    precipitation_sum_mm FLOAT,
    precipitation_hours FLOAT,           -- Hours of precipitation
    precipitation_probability_max FLOAT,
    rain_sum_mm FLOAT,
    snow_sum_mm FLOAT,
    
    -- Wind
    wind_speed_max_kmh FLOAT,
    wind_gusts_max_kmh FLOAT,
    wind_direction_dominant_deg FLOAT,
    
    -- Sun & Moon times (for viewing windows)
    sunrise_time TIMESTAMPTZ,
    sunset_time TIMESTAMPTZ,
    daylight_duration_seconds INTEGER,
    
    -- UV & Solar
    uv_index_max FLOAT,
    
    -- Summary
    weather_code INTEGER,
    weather_description TEXT,
    
    -- Forecast metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    data_source VARCHAR(50) DEFAULT 'Open-Meteo',
    
    -- Constraints
    CONSTRAINT fk_daily_location FOREIGN KEY (location_id) 
        REFERENCES shared.locations(location_id) ON DELETE CASCADE,
    CONSTRAINT unique_daily_forecast UNIQUE (location_id, forecast_date, generated_at)
);

-- Indexes
CREATE INDEX idx_daily_location ON daily_forecast(location_id);
CREATE INDEX idx_daily_date ON daily_forecast(forecast_date);
CREATE INDEX idx_daily_location_date ON daily_forecast(location_id, forecast_date);

-- Comment
COMMENT ON TABLE daily_forecast IS 
'Daily weather forecasts for next 16 days. Includes sunrise/sunset for observation window planning.';

-- ============================================================================
-- TABLE 4: HISTORICAL WEATHER
-- ============================================================================

CREATE TABLE historical_weather (
    id SERIAL PRIMARY KEY,
    
    -- Location & Date
    location_id VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    
    -- Temperature (daily values)
    temperature_max_celsius FLOAT,
    temperature_min_celsius FLOAT,
    temperature_mean_celsius FLOAT,
    
    -- Cloud cover (if available)
    cloud_cover_mean_percent FLOAT,
    
    -- Precipitation
    precipitation_sum_mm FLOAT,
    rain_sum_mm FLOAT,
    snow_sum_mm FLOAT,
    
    -- Wind
    wind_speed_max_kmh FLOAT,
    wind_speed_mean_kmh FLOAT,
    
    -- Atmospheric
    pressure_mean_hpa FLOAT,
    humidity_mean_percent FLOAT,
    
    -- Sun
    sunshine_duration_seconds INTEGER,
    daylight_duration_seconds INTEGER,
    
    -- Source
    data_source VARCHAR(50),  -- 'Open-Meteo', 'NASA_POWER', etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_historical_location FOREIGN KEY (location_id) 
        REFERENCES shared.locations(location_id) ON DELETE CASCADE,
    CONSTRAINT unique_historical_record UNIQUE (location_id, date, data_source)
);

-- Indexes
CREATE INDEX idx_historical_location ON historical_weather(location_id);
CREATE INDEX idx_historical_date ON historical_weather(date);
CREATE INDEX idx_historical_location_date ON historical_weather(location_id, date DESC);

-- Comment
COMMENT ON TABLE historical_weather IS 
'Historical weather data for pattern analysis. Used to identify typical conditions by season/month.';

-- ============================================================================
-- TABLE 5: OBSERVATION QUALITY SCORES
-- ============================================================================

CREATE TABLE observation_quality (
    id SERIAL PRIMARY KEY,
    
    -- Location & Time
    location_id VARCHAR(100) NOT NULL,
    datetime TIMESTAMPTZ NOT NULL,
    
    -- Quality Scores (0-100, higher = better)
    overall_quality_score INTEGER NOT NULL,      -- Combined score
    cloud_score INTEGER NOT NULL,                -- Based on cloud cover
    visibility_score INTEGER,                     -- Based on visibility
    stability_score INTEGER,                      -- Based on wind (for telescopes)
    darkness_score INTEGER,                       -- Moon phase + light pollution
    
    -- Classification
    quality_category VARCHAR(20) NOT NULL,        -- Excellent/Good/Fair/Poor/Unsuitable
    suitable_for_astronomy BOOLEAN NOT NULL,      -- Quick yes/no
    suitable_for_photography BOOLEAN,             -- Longer exposures need stability
    
    -- Contributing Factors
    cloud_cover_percent FLOAT,
    visibility_km FLOAT,
    wind_speed_kmh FLOAT,
    precipitation_mm FLOAT,
    moon_illumination_percent FLOAT,
    
    -- Reasoning (for users)
    quality_description TEXT,                     -- "Excellent: Clear skies, low wind"
    limitations TEXT,                             -- "Moderate wind may affect telescopes"
    
    -- Metadata
    is_forecast BOOLEAN DEFAULT false,            -- true = future prediction, false = current/past
    confidence_score FLOAT,                       -- How confident in this assessment (0-1)
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_quality_location FOREIGN KEY (location_id) 
        REFERENCES shared.locations(location_id) ON DELETE CASCADE,
    CONSTRAINT valid_overall_score CHECK (overall_quality_score BETWEEN 0 AND 100),
    CONSTRAINT valid_category CHECK (quality_category IN 
        ('Excellent', 'Good', 'Fair', 'Poor', 'Unsuitable')),
    CONSTRAINT unique_quality_record UNIQUE (location_id, datetime)
);

-- Indexes
CREATE INDEX idx_quality_location ON observation_quality(location_id);
CREATE INDEX idx_quality_time ON observation_quality(datetime DESC);
CREATE INDEX idx_quality_location_time ON observation_quality(location_id, datetime DESC);
CREATE INDEX idx_quality_score ON observation_quality(overall_quality_score DESC);
CREATE INDEX idx_quality_suitable ON observation_quality(suitable_for_astronomy) 
    WHERE suitable_for_astronomy = true;

-- Comment
COMMENT ON TABLE observation_quality IS 
'Pre-calculated observation suitability scores combining weather factors. 
Updated hourly for current + next 24 hours.';

-- ============================================================================
-- VIEW: CURRENT OBSERVATION CONDITIONS
-- ============================================================================

CREATE OR REPLACE VIEW current_observation_conditions AS
SELECT 
    l.location_id,
    l.name as location_name,
    l.latitude,
    l.longitude,
    cc.observed_at,
    cc.temperature_celsius,
    cc.cloud_cover_percent,
    cc.visibility_km,
    cc.wind_speed_kmh,
    cc.weather_description,
    oq.overall_quality_score,
    oq.quality_category,
    oq.suitable_for_astronomy,
    oq.quality_description,
    cc.sunset_time,
    cc.sunrise_time,
    CASE 
        WHEN NOW() BETWEEN cc.sunset_time AND cc.sunrise_time THEN true
        ELSE false
    END as is_currently_night
FROM shared.locations l
LEFT JOIN LATERAL (
    SELECT * FROM weather.current_conditions
    WHERE location_id = l.location_id
    ORDER BY observed_at DESC
    LIMIT 1
) cc ON true
LEFT JOIN LATERAL (
    SELECT * FROM weather.observation_quality
    WHERE location_id = l.location_id
    AND is_forecast = false
    ORDER BY datetime DESC
    LIMIT 1
) oq ON true;

COMMENT ON VIEW current_observation_conditions IS 
'Quick view of current observation conditions for all locations. 
Combines latest weather + quality scores.';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to calculate observation quality score
CREATE OR REPLACE FUNCTION calculate_observation_score(
    p_cloud_cover FLOAT,
    p_visibility FLOAT DEFAULT NULL,
    p_wind_speed FLOAT DEFAULT NULL,
    p_precipitation FLOAT DEFAULT 0
) RETURNS INTEGER AS $$
DECLARE
    v_cloud_score INTEGER;
    v_visibility_score INTEGER;
    v_wind_score INTEGER;
    v_precip_penalty INTEGER;
    v_total_score INTEGER;
BEGIN
    -- Cloud score (60% weight) - most important
    v_cloud_score := GREATEST(0, LEAST(100, (100 - p_cloud_cover) * 0.6));
    
    -- Visibility score (25% weight)
    IF p_visibility IS NOT NULL THEN
        v_visibility_score := GREATEST(0, LEAST(25, (p_visibility / 20) * 25));
    ELSE
        v_visibility_score := 15;  -- Assume moderate if unknown
    END IF;
    
    -- Wind score (10% weight) - affects telescope stability
    IF p_wind_speed IS NOT NULL THEN
        v_wind_score := CASE 
            WHEN p_wind_speed < 10 THEN 10
            WHEN p_wind_speed < 20 THEN 7
            WHEN p_wind_speed < 30 THEN 4
            ELSE 0
        END;
    ELSE
        v_wind_score := 5;  -- Assume moderate
    END IF;
    
    -- Precipitation penalty
    IF p_precipitation > 0 THEN
        v_precip_penalty := LEAST(50, p_precipitation * 10);  -- Heavy penalty for rain
    ELSE
        v_precip_penalty := 0;
    END IF;
    
    -- Calculate total
    v_total_score := v_cloud_score + v_visibility_score + v_wind_score - v_precip_penalty;
    
    RETURN GREATEST(0, LEAST(100, v_total_score));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_observation_score IS 
'Calculate observation quality score (0-100) from weather parameters.
Cloud cover has 60% weight, visibility 25%, wind 10%, with precipitation penalty.';

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Insert test current conditions for Mumbai
INSERT INTO weather.current_conditions (
    location_id,
    observed_at,
    temperature_celsius,
    humidity_percent,
    cloud_cover_percent,
    visibility_km,
    precipitation_mm,
    wind_speed_kmh,
    wind_direction_deg,
    weather_description,
    is_day,
    data_source
) VALUES (
    'mumbai_001',
    NOW(),
    28.5,
    65,
    25,
    10,
    0,
    15,
    180,
    'Partly cloudy',
    true,
    'Open-Meteo'
) ON CONFLICT DO NOTHING;

-- Calculate and insert observation quality
INSERT INTO weather.observation_quality (
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
    quality_description,
    is_forecast
) VALUES (
    'mumbai_001',
    NOW(),
    calculate_observation_score(25, 10, 15, 0),
    75,
    50,
    70,
    'Good',
    true,
    25,
    10,
    15,
    'Good conditions: Partly cloudy with good visibility',
    false
) ON CONFLICT (location_id, datetime) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Show schema tables
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'weather'
ORDER BY tablename;

-- Show current conditions
SELECT * FROM weather.current_observation_conditions;

-- Show sample quality score calculation
SELECT 
    'Clear Night' as condition,
    calculate_observation_score(10, 15, 8, 0) as score
UNION ALL
SELECT 
    'Partly Cloudy',
    calculate_observation_score(40, 12, 12, 0)
UNION ALL
SELECT 
    'Overcast',
    calculate_observation_score(95, 8, 20, 0)
UNION ALL
SELECT 
    'Rainy',
    calculate_observation_score(100, 3, 25, 5);

-- ============================================================================
-- END OF SCHEMA SETUP
-- ============================================================================