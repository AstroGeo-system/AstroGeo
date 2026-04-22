import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv('backend/.env')

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def debug_locations():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        # Locations connected to Asteroids
        ast_locs = session.run("MATCH (a:Asteroid)-[:APPROACH_RISK]->(l:Location) RETURN DISTINCT l.name AS name").data()
        print(f"Locations connected to Asteroids: {[r['name'] for r in ast_locs]}")
        
        # Locations connected to Zones
        zone_locs = session.run("MATCH (z:Zone)-[:LOCATED_IN]->(l:Location) RETURN DISTINCT l.name AS name").data()
        print(f"Locations connected to Zones: {[r['name'] for r in zone_locs]}")
        
        # Anomalies
        anom_locs = session.run("MATCH (a:Asteroid)-[:ANOMALOUS_PASS_NEAR]->(l:Location) RETURN DISTINCT l.name AS name").data()
        print(f"Locations connected to Anomalous Asteroids: {[r['name'] for r in anom_locs]}")

    driver.close()

if __name__ == "__main__":
    try:
        debug_locations()
    except Exception as e:
        print(f"Error: {e}")
