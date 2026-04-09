-- ============================================================================
-- ADD 30 MAJOR INDIAN CITIES TO ASTROGEO DATABASE
-- ============================================================================

SET search_path TO shared;

-- Clear existing test data (optional - only if you want fresh start)
-- DELETE FROM locations WHERE location_id LIKE '%_001';

-- Insert 30 major Indian cities
INSERT INTO locations (location_id, name, latitude, longitude, timezone, country, region, population) VALUES

-- Tier 1 Metro Cities (Population > 5 million)
('mumbai_001', 'Mumbai', 19.0760, 72.8777, 'Asia/Kolkata', 'India', 'Maharashtra', 20411000),
('delhi_001', 'Delhi', 28.7041, 77.1025, 'Asia/Kolkata', 'India', 'Delhi', 16787000),
('bangalore_001', 'Bangalore', 12.9716, 77.5946, 'Asia/Kolkata', 'India', 'Karnataka', 12765000),
('hyderabad_001', 'Hyderabad', 17.3850, 78.4867, 'Asia/Kolkata', 'India', 'Telangana', 10494000),
('chennai_001', 'Chennai', 13.0827, 80.2707, 'Asia/Kolkata', 'India', 'Tamil Nadu', 10971000),
('kolkata_001', 'Kolkata', 22.5726, 88.3639, 'Asia/Kolkata', 'India', 'West Bengal', 14850000),

-- Tier 2 Major Cities (Population 2-5 million)
('ahmedabad_001', 'Ahmedabad', 23.0225, 72.5714, 'Asia/Kolkata', 'India', 'Gujarat', 8450000),
('pune_001', 'Pune', 18.5204, 73.8567, 'Asia/Kolkata', 'India', 'Maharashtra', 7400000),
('surat_001', 'Surat', 21.1702, 72.8311, 'Asia/Kolkata', 'India', 'Gujarat', 6081000),
('jaipur_001', 'Jaipur', 26.9124, 75.7873, 'Asia/Kolkata', 'India', 'Rajasthan', 3460000),
('lucknow_001', 'Lucknow', 26.8467, 80.9462, 'Asia/Kolkata', 'India', 'Uttar Pradesh', 3382000),
('kanpur_001', 'Kanpur', 26.4499, 80.3319, 'Asia/Kolkata', 'India', 'Uttar Pradesh', 3067000),
('nagpur_001', 'Nagpur', 21.1458, 79.0882, 'Asia/Kolkata', 'India', 'Maharashtra', 2497000),
('indore_001', 'Indore', 22.7196, 75.8577, 'Asia/Kolkata', 'India', 'Madhya Pradesh', 2201000),

-- Tier 3 Important Cities (Population 1-2 million)
('thane_001', 'Thane', 19.2183, 72.9781, 'Asia/Kolkata', 'India', 'Maharashtra', 1841000),
('bhopal_001', 'Bhopal', 23.2599, 77.4126, 'Asia/Kolkata', 'India', 'Madhya Pradesh', 1883000),
('visakhapatnam_001', 'Visakhapatnam', 17.6868, 83.2185, 'Asia/Kolkata', 'India', 'Andhra Pradesh', 2035000),
('patna_001', 'Patna', 25.5941, 85.1376, 'Asia/Kolkata', 'India', 'Bihar', 2049000),
('vadodara_001', 'Vadodara', 22.3072, 73.1812, 'Asia/Kolkata', 'India', 'Gujarat', 1817000),
('ghaziabad_001', 'Ghaziabad', 28.6692, 77.4538, 'Asia/Kolkata', 'India', 'Uttar Pradesh', 1729000),
('ludhiana_001', 'Ludhiana', 30.9010, 75.8573, 'Asia/Kolkata', 'India', 'Punjab', 1618000),
('agra_001', 'Agra', 27.1767, 78.0081, 'Asia/Kolkata', 'India', 'Uttar Pradesh', 1585000),
('nashik_001', 'Nashik', 19.9975, 73.7898, 'Asia/Kolkata', 'India', 'Maharashtra', 1486000),
('faridabad_001', 'Faridabad', 28.4089, 77.3178, 'Asia/Kolkata', 'India', 'Haryana', 1414000),
('meerut_001', 'Meerut', 28.9845, 77.7064, 'Asia/Kolkata', 'India', 'Uttar Pradesh', 1305000),

-- Tourist & Hill Stations (Important for astronomy)
('goa_001', 'Goa (Panaji)', 15.4909, 73.8278, 'Asia/Kolkata', 'India', 'Goa', 114000),
('shimla_001', 'Shimla', 31.1048, 77.1734, 'Asia/Kolkata', 'India', 'Himachal Pradesh', 170000),
('manali_001', 'Manali', 32.2396, 77.1887, 'Asia/Kolkata', 'India', 'Himachal Pradesh', 8000),
('leh_001', 'Leh', 34.1526, 77.5771, 'Asia/Kolkata', 'India', 'Ladakh', 30000),
('ooty_001', 'Ooty', 11.4102, 76.6950, 'Asia/Kolkata', 'India', 'Tamil Nadu', 88000)

ON CONFLICT (location_id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    timezone = EXCLUDED.timezone,
    country = EXCLUDED.country,
    region = EXCLUDED.region,
    population = EXCLUDED.population,
    updated_at = NOW();

-- Verify insertion
SELECT COUNT(*) as total_cities FROM locations;

-- Show all cities
SELECT 
    location_id,
    name,
    region,
    ROUND(latitude::numeric, 4) as lat,
    ROUND(longitude::numeric, 4) as lon,
    population
FROM locations
ORDER BY population DESC NULLS LAST;

-- ============================================================================
-- END OF SCRIPT
-- ============================================================================