import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv('backend/.env')

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def check_solar_paths():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        # Path: SolarEvent -> Region -> Zone -> LandCoverChange
        path_query = """
        MATCH (s:SolarEvent)-[:DISRUPTS]->(r:Region)<-[:PART_OF]-(z:Zone)-[:SHOWS_CHANGE]->(c:LandCoverChange)
        RETURN count(DISTINCT s) AS count
        """
        res = session.run(path_query).single()
        print(f"SolarEvents with full path to LandCoverChange: {res['count']}")
        
        # Check if any such path exists at all
        exists = session.run("MATCH p=(s:SolarEvent)-[:DISRUPTS]->(r:Region)<-[:PART_OF]-(z:Zone)-[:SHOWS_CHANGE]->(c:LandCoverChange) RETURN p LIMIT 1").data()
        print(f"Sample path exists: {len(exists) > 0}")

    driver.close()

if __name__ == "__main__":
    try:
        check_solar_paths()
    except Exception as e:
        print(f"Error: {e}")
