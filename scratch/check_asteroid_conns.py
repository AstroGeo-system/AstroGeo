import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv('backend/.env')

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def check_asteroid_connections():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        # What are asteroids connected to?
        query = """
        MATCH (a:Asteroid)-[r]->(n)
        RETURN type(r) AS rel_type, labels(n) AS labels, count(*) AS count
        """
        res = session.run(query).data()
        print(f"Asteroid connection types: {res}")
        
        # Check specific location names
        loc_names = session.run("MATCH (a:Asteroid)-[:APPROACH_RISK]->(l:Location) RETURN DISTINCT properties(l) AS props").data()
        print(f"Properties of Locations connected to Asteroids: {loc_names}")

    driver.close()

if __name__ == "__main__":
    try:
        check_asteroid_connections()
    except Exception as e:
        print(f"Error: {e}")
