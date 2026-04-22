import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv('backend/.env')

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def count_categories():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session(database=NEO4J_DATABASE) as session:
        # High Risk
        high = session.run("MATCH (a:Asteroid) WHERE a.risk_category = 'High' RETURN count(a) AS count").single()
        print(f"High risk asteroids: {high['count']}")
        
        # Medium Risk
        medium = session.run("MATCH (a:Asteroid) WHERE a.risk_category = 'Medium' RETURN count(a) AS count").single()
        print(f"Medium risk asteroids: {medium['count']}")
        
        # Anomalous
        anomaly = session.run("MATCH (a:Asteroid) WHERE a.is_anomaly = true RETURN count(a) AS count").single()
        print(f"Anomalous asteroids: {anomaly['count']}")

        # Distribution of risk_category
        dist = session.run("MATCH (a:Asteroid) RETURN a.risk_category as cat, count(a) as count").data()
        print(f"Risk category distribution: {dist}")

        # Check connections again specifically for High risk
        high_conn = session.run("MATCH (a:Asteroid {risk_category: 'High'})--() RETURN count(DISTINCT a) AS count").single()
        print(f"Connected High risk asteroids: {high_conn['count']}")

    driver.close()

if __name__ == "__main__":
    try:
        count_categories()
    except Exception as e:
        print(f"Error: {e}")
