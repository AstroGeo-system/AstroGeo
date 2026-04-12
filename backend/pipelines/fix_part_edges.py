# fix_part_of_edges.py
# Run once — creates PART_OF edges between your existing Zone nodes
# and the Region nodes seeded by 09b_seed_solar_flares.py

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Explicitly load backend/.env since we run from project root
# Script is in backend/pipelines/, .env is in backend/
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# Maps region → keywords to match against your Zone node names
# Adjust these to match how your zones are actually named in Neo4j
REGION_ZONE_KEYWORDS = {
    'West India': [
        'maharashtra', 'gujarat', 'rajasthan', 'dadra',
        'pune', 'mumbai', 'nashik', 'nagpur',
        'konkan', 'vidarbha', 'marathwada',
    ],
    'North India': [
        'punjab', 'haryana', 'uttar_pradesh', 'delhi',
        'himachal', 'uttarakhand', 'jammu', 'kashmir', 'ladakh',
    ],
    'South India': [
        'tamil_nadu', 'karnataka', 'andhra', 'telangana', 'kerala',
        'puducherry', 'lakshadweep', 'chennai', 'bangalore', 'hyderabad',
    ],
    'East India': [
        'west_bengal', 'odisha', 'bihar', 'jharkhand', 'sikkim',
        'kolkata', 'bhubaneswar',
    ],
    'Central India': [
        'madhya_pradesh', 'chhattisgarh',
        'bhopal', 'indore', 'raipur',
    ],
    'Northeast India': [
        'assam', 'manipur', 'meghalaya', 'nagaland',
        'mizoram', 'tripura', 'arunachal', 'northeast',
    ],
    'Islands': [
        'andaman', 'nicobar',
    ]
}

def fix_part_of_edges():
    driver = GraphDatabase.driver(
        os.getenv('NEO4J_URI'),
        auth=(
            os.getenv('NEO4J_USERNAME', os.getenv('NEO4J_USER', 'neo4j')),
            os.getenv('NEO4J_PASSWORD')
        )
    )

    with driver.session() as session:

        # First — see what Zone nodes actually exist
        print("Checking existing Zone nodes...")
        zones = session.run("""
            MATCH (z:Zone)
            RETURN z.name AS name
            LIMIT 30
        """).data()

        print(f"Found {len(zones)} Zone nodes:")
        for z in zones:
            print(f"  → {z['name']}")

        # Create PART_OF edges based on keyword matching
        print("\nCreating PART_OF edges...")
        total_created = 0

        for region_name, keywords in REGION_ZONE_KEYWORDS.items():
            for keyword in keywords:
                result = session.run("""
                    MATCH (z:Zone)
                    WHERE z.name CONTAINS $keyword
                       OR z.state CONTAINS $keyword
                       OR z.zone_name CONTAINS $keyword
                    MATCH (r:Region {name: $region_name})
                    MERGE (z)-[:PART_OF]->(r)
                    RETURN count(*) AS created
                """, {
                    'keyword':     keyword,
                    'region_name': region_name,
                }).single()

                if result and result['created'] > 0:
                    print(f"  ✅ {keyword} → {region_name} "
                          f"({result['created']} edges)")
                    total_created += result['created']

        print(f"\nTotal PART_OF edges created: {total_created}")

        # Verify the full cross-domain path now works
        print("\nTesting cross-domain path...")
        test = session.run("""
            MATCH (e:SolarEvent)-[:DISRUPTS]->(r:Region)
                  <-[:PART_OF]-(z:Zone)
                  -[:SHOWS_CHANGE]->(c:LandCoverChange)
            WHERE e.disruption_risk > 0.4
            RETURN e.date       AS event_date,
                   e.intensity  AS intensity,
                   r.name       AS region,
                   z.name       AS zone,
                   c.type       AS land_change
            LIMIT 3
        """).data()

        if test:
            print(f"✅ Cross-domain path working! {len(test)} results:")
            for row in test:
                print(f"   {row['event_date']} | {row['intensity']} | "
                      f"{row['region']} | {row['zone']} | {row['land_change']}")
        else:
            print("⚠️  Still no results — check zone names above and")
            print("   adjust REGION_ZONE_KEYWORDS to match your actual zone names")

    driver.close()

if __name__ == '__main__':
    fix_part_of_edges()