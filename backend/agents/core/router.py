from typing import Dict, Any, Optional
from ..astronomy.astronomy_agent import AstronomyAgent

class AgentRouter:
    """
    Routes natural language queries to the appropriate agent and method.
    Currently supports: AstronomyAgent.
    """
    
    def __init__(self):
        self.astronomy_agent = AstronomyAgent()
        
    def route_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze query and route to appropriate agent method.
        Simple keyword-based routing for now.
        """
        query_lower = query.lower()
        context = context or {}
        location = context.get('location', 'Mumbai') # Default if not provided
        
        # SATELLITE QUERIES
        if 'iss' in query_lower or 'space station' in query_lower:
            if 'where' in query_lower or 'position' in query_lower:
                return self.astronomy_agent.get_satellite_position('ISS')
            if 'pass' in query_lower or 'visible' in query_lower:
                return self.astronomy_agent.get_next_iss_pass(location)
            if 'best' in query_lower and 'view' in query_lower:
                return self.astronomy_agent.find_best_viewing_location('ISS')
                
        # WEATHER QUERIES
        if 'weather' in query_lower or 'cloud' in query_lower or 'condition' in query_lower:
            if 'forecast' in query_lower or 'predict' in query_lower:
                return self.astronomy_agent.compare_forecast_vs_current(location)
            return self.astronomy_agent.get_observation_conditions(location)
            
        # ASTEROID QUERIES
        if 'asteroid' in query_lower:
            if 'risk' in query_lower or 'dangerous' in query_lower:
                return self.astronomy_agent.get_high_risk_asteroids()
            if 'close' in query_lower or 'approach' in query_lower:
                return self.astronomy_agent.get_upcoming_asteroid_approaches()
            # If ID is present (heuristic: numbers)
            words = query_lower.split()
            for word in words:
                if word.isdigit() or (word.startswith('20') and len(word) >= 4):
                     return self.astronomy_agent.get_asteroid_profile(word)
        
        # GENERAL / INTEGRATED
        if 'tonight' in query_lower:
            if 'observe' in query_lower or 'see' in query_lower:
                return self.astronomy_agent.can_i_observe_tonight(location)
            return self.astronomy_agent.whats_happening_tonight(location)

        return {"error": "Could not understand query or route to agent."}
