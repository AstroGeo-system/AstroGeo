-- ============================================================================
-- SATELLITE TRACKING AGENT DATABASE SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS satellite;

COMMENT ON SCHEMA satellite IS 
'Satellite tracking data: ISS, Starlink, Tiangong, and other visible satellites';

SET search_path TO satellite;

-- ============================================================================
-- TABLE 1: TRACKED SATELLITES (Catalog)
-- ============================================================================

CREATE TABLE satellites (
    satellite_id VARCHAR(50) PRIMARY KEY,  -- NORAD ID or custom ID
    
    -- Identification
    name VARCHAR(200) NOT NULL,
    common_name VARCHAR(200),              -- "ISS" vs "International Space Station"
    norad_id INTEGER UNIQUE,               -- Official NORAD catalog number
    cospar_id VARCHAR(20),                 -- International designator (e.g., 1998-067A)
    
    -- Classification
    category VARCHAR(50) NOT NULL,         -- 'Space Station', 'Communication', 'Navigation', 'Starlink', etc.
    priority_level INTEGER DEFAULT 5,     -- 1=Highest (ISS), 5=Lowest
    
    -- Visibility
    is_visible BOOLEAN DEFAULT true,       -- Can be seen with naked eye/binoculars
    average_magnitude FLOAT,               -- Brightness (-6 to +6, lower = brighter)
    max_magnitude FLOAT,                   -- Brightest it can get
    
    -- Orbital characteristics
    orbit_type VARCHAR(50),                -- 'LEO', 'MEO', 'GEO', etc.
    orbital_period_minutes FLOAT,          -- Time for one orbit
    apogee_km FLOAT,                       -- Highest point
    perigee_km FLOAT,                      -- Lowest point
    inclination_deg FLOAT,                 -- Orbital tilt
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    launch_date DATE,
    decay_date DATE,                       -- Expected re-entry date (if known)
    
    -- Metadata
    data_source VARCHAR(100),              -- 'N2YO', 'Space-Track', 'Celestrak', etc.
    last_tle_update TIMESTAMPTZ,           -- When orbital elements were last updated
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_priority CHECK (priority_level BETWEEN 1 AND 10),
    CONSTRAINT valid_magnitude CHECK (average_magnitude IS NULL OR average_magnitude BETWEEN -10 AND 10)
);

-- Indexes
CREATE INDEX idx_satellites_category ON satellites(category);
CREATE INDEX idx_satellites_priority ON satellites(priority_level);
CREATE INDEX idx_satellites_visible ON satellites(is_visible) WHERE is_visible = true;
CREATE INDEX idx_satellites_norad ON satellites(norad_id);

COMMENT ON TABLE satellites IS 
'Catalog of tracked satellites. Priority 1-2 = always track (ISS, Tiangong), 3-5 = track on demand.';

-- ============================================================================
-- TABLE 2: SATELLITE PASSES (Predictions)
-- ============================================================================

CREATE TABLE satellite_passes (
    id SERIAL PRIMARY KEY,
    
    -- Satellite & Location
    satellite_id VARCHAR(50) NOT NULL,
    location_id VARCHAR(100) NOT NULL,
    
    -- Pass timing
    rise_time TIMESTAMPTZ NOT NULL,
    set_time TIMESTAMPTZ NOT NULL,
    max_elevation_time TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER NOT NULL,
    
    -- Visibility details
    max_elevation_deg FLOAT NOT NULL,      -- How high in sky (0-90°)
    azimuth_rise_deg FLOAT,                -- Direction of rise (0-360°)
    azimuth_set_deg FLOAT,                 -- Direction of set
    azimuth_max_elevation_deg FLOAT,       -- Direction at peak
    
    -- Brightness
    magnitude FLOAT,                       -- How bright (-6 to +6)
    visibility_quality VARCHAR(20),        -- 'Excellent', 'Good', 'Fair', 'Poor'
    
    -- Sun position (affects visibility)
    is_illuminated BOOLEAN DEFAULT true,   -- Satellite lit by sun
    sun_elevation_deg FLOAT,               -- Sun position during pass
    
    -- Prediction metadata
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    prediction_source VARCHAR(50),         -- API used for prediction
    confidence_score FLOAT,                -- How reliable (0-1)
    
    -- Pass classification
    pass_type VARCHAR(20),                 -- 'visible', 'radar_only', 'daylight'
    is_prime_viewing BOOLEAN,              -- Best possible viewing conditions
    
    -- Constraints
    CONSTRAINT fk_pass_satellite FOREIGN KEY (satellite_id) 
        REFERENCES satellites(satellite_id) ON DELETE CASCADE,
    CONSTRAINT fk_pass_location FOREIGN KEY (location_id) 
        REFERENCES shared.locations(location_id) ON DELETE CASCADE,
    CONSTRAINT valid_elevation CHECK (max_elevation_deg BETWEEN 0 AND 90),
    CONSTRAINT valid_duration CHECK (duration_seconds > 0),
    CONSTRAINT unique_pass UNIQUE (satellite_id, location_id, rise_time)
);

-- Indexes
CREATE INDEX idx_passes_satellite ON satellite_passes(satellite_id);
CREATE INDEX idx_passes_location ON satellite_passes(location_id);
CREATE INDEX idx_passes_rise_time ON satellite_passes(rise_time);
CREATE INDEX idx_passes_location_time ON satellite_passes(location_id, rise_time);
CREATE INDEX idx_passes_prime ON satellite_passes(is_prime_viewing) WHERE is_prime_viewing = true;
CREATE INDEX idx_passes_upcoming ON satellite_passes(rise_time) 
    WHERE rise_time > NOW() AND rise_time < NOW() + INTERVAL '7 days';

COMMENT ON TABLE satellite_passes IS 
'Predicted satellite passes for each location. Updated daily for next 7-10 days.';

-- ============================================================================
-- TABLE 3: CURRENT SATELLITE POSITIONS (Real-time)
-- ============================================================================

CREATE TABLE satellite_positions (
    id SERIAL PRIMARY KEY,
    
    -- Satellite
    satellite_id VARCHAR(50) NOT NULL,
    
    -- Position (lat/lon/altitude)
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    altitude_km FLOAT NOT NULL,
    
    -- Velocity
    velocity_km_s FLOAT,
    
    -- Sun illumination
    is_in_sunlight BOOLEAN,
    is_in_eclipse BOOLEAN,
    
    -- Timestamp
    position_time TIMESTAMPTZ NOT NULL,
    
    -- Metadata
    data_source VARCHAR(50),
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_position_satellite FOREIGN KEY (satellite_id) 
        REFERENCES satellites(satellite_id) ON DELETE CASCADE,
    CONSTRAINT valid_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT valid_altitude CHECK (altitude_km > 0)
);

-- Indexes
CREATE INDEX idx_position_satellite ON satellite_positions(satellite_id);
CREATE INDEX idx_position_time ON satellite_positions(position_time DESC);
CREATE INDEX idx_position_satellite_time ON satellite_positions(satellite_id, position_time DESC);

COMMENT ON TABLE satellite_positions IS 
'Real-time satellite positions. Updated every 1-5 minutes for high-priority satellites (ISS, Tiangong).';

-- ============================================================================
-- TABLE 4: OBSERVATION RECOMMENDATIONS (Integrated View)
-- ============================================================================

CREATE TABLE observation_recommendations (
    id SERIAL PRIMARY KEY,
    
    -- What & Where
    satellite_id VARCHAR(50) NOT NULL,
    location_id VARCHAR(100) NOT NULL,
    pass_id INTEGER,                       -- Links to satellite_passes
    
    -- When
    recommended_time TIMESTAMPTZ NOT NULL,
    observation_window_start TIMESTAMPTZ,
    observation_window_end TIMESTAMPTZ,
    
    -- Satellite factors
    satellite_magnitude FLOAT,
    satellite_elevation_deg FLOAT,
    satellite_visibility_score INTEGER,    -- 0-100
    
    -- Weather factors (from weather schema)
    cloud_cover_percent FLOAT,
    visibility_km FLOAT,
    weather_quality_score INTEGER,         -- 0-100
    weather_suitable BOOLEAN,
    
    -- Combined recommendation
    overall_score INTEGER NOT NULL,        -- 0-100 (satellite + weather)
    recommendation_category VARCHAR(20),   -- 'Excellent', 'Good', 'Fair', 'Poor', 'Unsuitable'
    
    -- Reasoning
    recommendation_text TEXT,              -- "Excellent: ISS at 78° elevation, clear skies"
    limitations TEXT,                      -- "Light pollution may reduce visibility"
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    is_forecast BOOLEAN DEFAULT true,
    confidence_score FLOAT,
    
    -- Constraints
    CONSTRAINT fk_rec_satellite FOREIGN KEY (satellite_id) 
        REFERENCES satellites(satellite_id) ON DELETE CASCADE,
    CONSTRAINT fk_rec_location FOREIGN KEY (location_id) 
        REFERENCES shared.locations(location_id) ON DELETE CASCADE,
    CONSTRAINT fk_rec_pass FOREIGN KEY (pass_id) 
        REFERENCES satellite_passes(id) ON DELETE CASCADE,
    CONSTRAINT valid_overall_score CHECK (overall_score BETWEEN 0 AND 100),
    CONSTRAINT unique_recommendation UNIQUE (satellite_id, location_id, recommended_time)
);

-- Indexes
CREATE INDEX idx_rec_location ON observation_recommendations(location_id);
CREATE INDEX idx_rec_time ON observation_recommendations(recommended_time);
CREATE INDEX idx_rec_score ON observation_recommendations(overall_score DESC);
CREATE INDEX idx_rec_location_time ON observation_recommendations(location_id, recommended_time);
CREATE INDEX idx_rec_excellent ON observation_recommendations(recommendation_category) 
    WHERE recommendation_category IN ('Excellent', 'Good');

COMMENT ON TABLE observation_recommendations IS 
'Pre-calculated recommendations combining satellite passes + weather forecasts. 
Updated every 6 hours for next 7 days.';

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Tonight's visible satellites
CREATE OR REPLACE VIEW tonights_visible_satellites AS
SELECT 
    s.satellite_id,
    s.name,
    s.common_name,
    s.category,
    s.priority_level,
    sp.location_id,
    l.name as location_name,
    sp.rise_time,
    sp.set_time,
    sp.max_elevation_deg,
    sp.magnitude,
    sp.visibility_quality,
    sp.is_prime_viewing,
    
    -- Weather integration
    w.cloud_cover_percent,
    w.weather_description,
    oq.overall_quality_score as weather_quality,
    oq.suitable_for_astronomy,
    
    -- Combined score
    CASE 
        WHEN oq.suitable_for_astronomy = false THEN 0
        ELSE (
            (90 - sp.max_elevation_deg) * 0.3 +       -- Higher elevation = better (30%)
            (6 + sp.magnitude) * 10 * 0.2 +           -- Brighter = better (20%)
            oq.overall_quality_score * 0.5            -- Weather quality (50%)
        )
    END as combined_score,
    
    -- Time until pass
    EXTRACT(EPOCH FROM (sp.rise_time - NOW())) / 3600 as hours_until_rise
    
FROM satellite_passes sp
JOIN satellites s ON sp.satellite_id = s.satellite_id
JOIN shared.locations l ON sp.location_id = l.location_id
LEFT JOIN LATERAL (
    SELECT * FROM weather.current_conditions
    WHERE location_id = sp.location_id
    ORDER BY observed_at DESC
    LIMIT 1
) w ON true
LEFT JOIN LATERAL (
    SELECT * FROM weather.observation_quality
    WHERE location_id = sp.location_id
    AND is_forecast = false
    ORDER BY datetime DESC
    LIMIT 1
) oq ON true

WHERE sp.rise_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
  AND s.is_visible = true
  AND s.is_active = true
ORDER BY combined_score DESC;

COMMENT ON VIEW tonights_visible_satellites IS 
'All satellites visible in next 24 hours, ranked by viewing quality (elevation + brightness + weather).';

-- ============================================================================
-- SEED DATA: High-Priority Satellites
-- ============================================================================

INSERT INTO satellites (
    satellite_id, name, common_name, norad_id, category, priority_level,
    is_visible, average_magnitude, orbit_type, orbital_period_minutes,
    data_source, is_active
) VALUES
    ('ISS', 'International Space Station', 'ISS', 25544, 'Space Station', 1, 
     true, -4.0, 'LEO', 92.9, 'N2YO', true),
    
    ('TIANGONG', 'Tiangong Space Station', 'Tiangong', 48274, 'Space Station', 1,
     true, -2.0, 'LEO', 90.6, 'N2YO', true),
    
    ('HUBBLE', 'Hubble Space Telescope', 'Hubble', 20580, 'Scientific', 2,
     true, 2.0, 'LEO', 96.7, 'N2YO', true)

ON CONFLICT (satellite_id) DO NOTHING;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Calculate combined observation score
CREATE OR REPLACE FUNCTION calculate_satellite_observation_score(
    p_elevation FLOAT,
    p_magnitude FLOAT,
    p_weather_score FLOAT,
    p_weather_suitable BOOLEAN
) RETURNS INTEGER AS $$
DECLARE
    v_elevation_score INTEGER;
    v_brightness_score INTEGER;
    v_total_score INTEGER;
BEGIN
    -- If weather unsuitable, return 0
    IF p_weather_suitable = false THEN
        RETURN 0;
    END IF;
    
    -- Elevation score (0-40 points)
    -- Higher elevation = less atmosphere = better viewing
    v_elevation_score := LEAST(40, p_elevation * 0.44);  -- 90° = 40 points
    
    -- Brightness score (0-30 points)
    -- Brighter (more negative) = better
    -- ISS (-4) = 30 points, dim satellite (+4) = 0 points
    v_brightness_score := GREATEST(0, LEAST(30, (6 - p_magnitude) * 5));
    
    -- Weather score (0-30 points)
    v_total_score := v_elevation_score + v_brightness_score + (p_weather_score * 0.3);
    
    RETURN GREATEST(0, LEAST(100, v_total_score));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_satellite_observation_score IS 
'Calculate observation quality score (0-100) combining satellite visibility + weather.
Elevation: 40%, Brightness: 30%, Weather: 30%';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================