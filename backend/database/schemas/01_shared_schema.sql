-- ============================================================================
-- SHARED SCHEMA SETUP
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS shared;

COMMENT ON SCHEMA shared IS 'Shared resources and reference data used across modules';

SET search_path TO shared;

-- ============================================================================
-- LOCATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    elevation_meters FLOAT DEFAULT 0,
    timezone VARCHAR(50) DEFAULT 'UTC',
    country VARCHAR(100),
    region VARCHAR(100),
    population BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_lat CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT valid_lon CHECK (longitude BETWEEN -180 AND 180)
);

COMMENT ON TABLE locations IS 'Geographic locations for astronomical observation';

-- Insert default location (e.g., Mumbai as used in tests)
INSERT INTO locations (location_id, name, latitude, longitude, timezone)
VALUES ('mumbai_001', 'Mumbai, India', 19.0760, 72.8777, 'Asia/Kolkata')
ON CONFLICT (location_id) DO NOTHING;

-- ============================================================================
-- END OF SHARED SCHEMA SETUP
-- ============================================================================
