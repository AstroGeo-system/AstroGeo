import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv('backend/.env')

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def check_paths():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        # Path: Asteroid -> Location -> Zone -> LandCoverChange
        path_query = """
        MATCH (a:Asteroid)-[:APPROACH_RISK]->(l:Location)<-[:LOCATED_IN]-(z:Zone)-[:SHOWS_CHANGE]->(c:LandCoverChange)
        RETURN count(DISTINCT a) AS count
        """
        res = session.run(path_query).single()
        print(f"Asteroids with full path to LandCoverChange: {res['count']}")
        
        # Check intermediate steps
        step1 = session.run("MATCH (a:Asteroid)-[:APPROACH_RISK]->(l:Location) RETURN count(DISTINCT a) AS count").single()
        print(f"Asteroids connected to Location: {step1['count']}")
        
        step2 = session.run("MATCH (l:Location)<-[:LOCATED_IN]-(z:Zone) RETURN count(DISTINCT z) AS count").single()
        print(f"Zones connected to Location: {step2['count']}")
        
        step3 = session.run("MATCH (z:Zone)-[:SHOWS_CHANGE]->(c:LandCoverChange) RETURN count(DISTINCT z) AS count").single()
        print(f"Zones connected to LandCoverChange: {step3['count']}")

    driver.close()

if __name__ == "__main__":
    try:
        check_paths()
    except Exception as e:
        print(f"Error: {e}")
