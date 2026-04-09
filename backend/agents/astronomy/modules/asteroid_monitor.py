from sqlalchemy import text
from typing import Dict, List, Any, Optional
from backend.services.external.nasa_service import nasa_service
import asyncio

class AsteroidMonitor:
    """
    Handles all asteroid-related queries and analysis.
    Uses 'astronomy.asteroid_ml_predictions' for profile/risk data.
    Uses 'nasa_service' for live approach data.
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.cluster_names = {
            0: "Frequent Close Approachers",
            1: "Moderate Regulars",
            2: "Distant Visitors"
        }
    
    def get_profile(self, asteroid_id: str) -> Optional[Dict[str, Any]]:
        """
        Query astronomy.asteroid_ml_predictions
        """
        query = text("""
            SELECT *
            FROM astronomy.asteroid_ml_predictions
            WHERE asteroid_id = :id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'id': asteroid_id}).fetchone()
            
            if not result:
                return None
            
            profile = dict(result._mapping)
            profile['cluster_name'] = self.cluster_names.get(profile.get('cluster'), "Unknown")
            # Map columns to expected output format if needed
            profile['risk_score'] = profile.get('improved_risk_score')
            profile['risk_category'] = profile.get('adaptive_risk_category')
            return profile

    def get_upcoming_approaches(self, days_ahead=30, min_distance=None, risk_level=None) -> List[Dict[str, Any]]:
        """
        Fetch from NASA Service and enrich with DB ML data
        """
        # Note: This method effectively becomes async because nasa_service is async
        # But we are in a synchronous class method for now. 
        # Ideally the Agent should be async.
        # For now, we'll return a promise or need to be run in async context.
        # Since I cannot easily change the whole agent to async in one go without breaking interfaces,
        # I will assume the caller handles async or I'll implementation a sync wrapper if strictly needed.
        # However, looking at the codebase, services ARE async.
        # The user requested 'def get_upcoming_approaches', implying sync?
        # But backend is FastAPI (Async). 
        # I'll implement this returning a coroutine (async def) or similar.
        # Wait, the previous implementation was sync (using db).
        # To use nasa_service, I must be async.
        
        raise NotImplementedError("This method requires async context. Use 'get_upcoming_approaches_async' instead.")

    async def get_upcoming_approaches_async(self, days_ahead=30, min_distance=None, risk_level=None) -> List[Dict[str, Any]]:
        import datetime
        start_date = datetime.date.today().strftime("%Y-%m-%d")
        end_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d") # NASA limits to 7 days
        
        # 1. Get Approaches from NASA
        try:
            approaches = await nasa_service.get_close_approaches(start_date, end_date)
        except Exception:
            return []

        # 2. Filter and Enrich
        enriched_approaches = []
        
        # Collect IDs to batch query
        asteroid_ids = [a['id'] for a in approaches]
        
        if not asteroid_ids:
             return []

        # Query DB for ML data
        # Clean IDs (remove parens if any)
        clean_ids = [aid.replace('(', '').replace(')', '') for aid in asteroid_ids]
        
        query = text("""
            SELECT asteroid_id, improved_risk_score, adaptive_risk_category, cluster, is_pha_candidate
            FROM astronomy.asteroid_ml_predictions
            WHERE asteroid_id IN :ids
        """)
        
        ml_data_map = {}
        with self.engine.connect() as conn:
            # SQLAlchemy handles list IN clause safely usually, but let's be careful
            # If empty list, skip
            if clean_ids:
                result = conn.execute(query, {'ids': tuple(clean_ids)})
                for row in result:
                    ml_data_map[str(row.asteroid_id)] = dict(row._mapping)
        
        for app in approaches:
            aid = str(app['id'])
            ml_info = ml_data_map.get(aid, {})
            
            # Enrich
            app.update(ml_info)
            app['risk_score'] = ml_info.get('improved_risk_score')
            
            # Filter
            if min_distance and app['distance_au'] > min_distance:
                continue
            if risk_level and ml_info.get('adaptive_risk_category') != risk_level:
                continue
                
            enriched_approaches.append(app)
            
        return enriched_approaches[:50]

    def get_cluster_members(self, cluster_id: int, limit: int = 10) -> Dict[str, Any]:
        """
        Query asteroids in same cluster
        """
        query = text("""
            SELECT asteroid_id, improved_risk_score as max_risk_score, estimated_diameter_km  
            FROM astronomy.asteroid_ml_predictions
            WHERE cluster = :cluster_id
            ORDER BY improved_risk_score DESC
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'cluster_id': cluster_id, 'limit': limit})
            members = [dict(row._mapping) for row in result]
            
            return {
                "cluster_id": cluster_id,
                "cluster_name": self.cluster_names.get(cluster_id, "Unknown"),
                "member_count": len(members),
                "members": members
            }
            
    def get_high_risk_asteroids(self, min_risk_score=60) -> List[Dict[str, Any]]:
        """Get high risk asteroids"""
        query = text("""
            SELECT asteroid_id, improved_risk_score, is_pha_candidate, next_predicted_approach as next_approach
            FROM astronomy.asteroid_ml_predictions
            WHERE improved_risk_score >= :min_score
            ORDER BY improved_risk_score DESC
            LIMIT 20
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {'min_score': min_risk_score})
            return [dict(row._mapping) for row in result]

    def search_asteroids(self, search_term: str) -> List[Dict[str, Any]]:
        """Search by ID"""
        query = text("""
            SELECT asteroid_id, improved_risk_score
            FROM astronomy.asteroid_ml_predictions
            WHERE asteroid_id ILIKE :term
            LIMIT 20
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {'term': f"%{search_term}%"})
            return [dict(row._mapping) for row in result]
    
    def get_temporal_pattern(self, asteroid_id: str) -> List[Dict[str, Any]]:
        # Not available in ML table, would need approach_events table or NASA lookup
        return []

    def get_next_approaches_from_db(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get upcoming approaches purely from the database (sync).
        """
        query = text("""
            SELECT 
                asteroid_id,
                improved_risk_score,
                is_pha_candidate,
                next_predicted_approach,
                adaptive_risk_category,
                estimated_diameter_km
            FROM astronomy.asteroid_ml_predictions
            WHERE next_predicted_approach > NOW()
            ORDER BY next_predicted_approach ASC
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'limit': limit})
            return [dict(row._mapping) for row in result]
    
    def compare_asteroids(self, id1: str, id2: str) -> Dict[str, Any]:
        """Compare two asteroids"""
        p1 = self.get_profile(id1)
        p2 = self.get_profile(id2)
        return {"asteroid_1": p1, "asteroid_2": p2}
