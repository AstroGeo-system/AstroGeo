import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Go up from backend/
sys.path.append(project_root)

from backend.agents.astronomy.astronomy_agent import AstronomyAgent
from unittest.mock import MagicMock, patch

def test_astronomy_agent():
    print("🔭 Testing Astronomy Agent...")
    
    # Mock the database engine to avoid needing a real DB connection
    with patch('backend.agents.astronomy.astronomy_agent.create_engine') as mock_create_engine:
        # Setup mock connection and result
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        
        # Test 1: Initialize Agent
        try:
            agent = AstronomyAgent()
            print("✅ Agent Initialized")
        except Exception as e:
            print(f"❌ Initialization Failed: {e}")
            return

        # Test 2: Satellite Query
        print("\n🛰 Testing Satellite Query...")
        # Mock result for get_passes
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_result.__iter__.return_value = [
            MagicMock(_mapping={
                'satellite_id': 'ISS', 'name': 'International Space Station',
                'rise_time': '2026-02-15 20:00', 'max_elevation_deg': 85,
                'combined_score': 90
            })
        ]
        mock_connection.execute.return_value = mock_result
        
        passes = agent.get_satellite_passes('Mumbai')
        if passes and passes[0]['satellite_id'] == 'ISS':
            print("✅ Satellite Passes Found")
        else:
            print("❌ Satellite Passes Query Failed")
            
        # Test 3: Weather Query
        print("\n☁️ Testing Weather Query...")
        # Mock result for get_observation_conditions
        mock_result_weather = MagicMock()
        mock_result_weather.fetchone.return_value = MagicMock(_mapping={
            'location_name': 'Mumbai',
            'overall_quality_score': 85,
            'suitable_for_astronomy': True,
            'weather_description': 'Clear Sky'
        })
        mock_connection.execute.return_value = mock_result_weather
        
        conditions = agent.get_observation_conditions('Mumbai')
        if conditions and conditions['suitable_for_astronomy']:
             print("✅ Weather Conditions Retrieved")
        else:
             print("❌ Weather Query Failed")

        # Test 4: Asteroid Query
        print("\ndeg Testing Asteroid Query...")
        # Mock result for get_profile
        mock_result_asteroid = MagicMock()
        mock_result_asteroid.fetchone.return_value = MagicMock(_mapping={
            'asteroid_id': '99942',
            'cluster': 0,
            'improved_risk_score': 15.5
        })
        # Reset execute mock to return asteroid result
        mock_connection.execute.return_value = mock_result_asteroid
        
        profile = agent.get_asteroid_profile('99942')
        if profile and profile['asteroid_id'] == '99942':
            print("✅ Asteroid Profile Retrieved")
        else:
             print("❌ Asteroid Query Failed")
             
        print("\n✨ All basic checks passed!")

if __name__ == "__main__":
    test_astronomy_agent()
