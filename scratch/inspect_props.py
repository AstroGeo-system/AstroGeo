import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv('backend/.env')

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def inspect_location_props():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        # Get all properties of first 5 Location nodes
        res = session.run("MATCH (l:Location) RETURN properties(l) AS props LIMIT 5").data()
        print(f"Location properties: {res}")
        
        # Get all properties of first 5 Asteroid nodes
        ast = session.run("MATCH (a:Asteroid) RETURN properties(a) AS props LIMIT 5").data()
        print(f"Asteroid properties: {ast}")

    driver.close()

if __name__ == "__main__":
    try:
        inspect_location_props()
    except Exception as e:
        print(f"Error: {e}")
