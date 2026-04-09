# 09_graphrag_seed.py
# Creates the first cross-domain knowledge graph connections
# Run once after Neo4j Aura instance is ready

from neo4j import GraphDatabase
import psycopg2
import pandas as pd
import os

# ── Connect to Neo4j ─────────────────────────────────────────
driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(
        os.getenv('NEO4J_USER', 'neo4j'),
        os.getenv('NEO4J_PASSWORD')
    )
)

# ── Connect to PostgreSQL ────────────────────────────────────
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 'astrogeo'),
    user=os.getenv('DB_USER'),
)


def create_constraints(session):
    """Create uniqueness constraints — run once."""
    session.run("CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (z:Zone) REQUIRE z.name IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (l:Location) REQUIRE l.region IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (a:Asteroid) REQUIRE a.designation IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (c:LandCoverChange) REQUIRE c.id IS UNIQUE")
    print("Constraints created.")


def seed_location_nodes(session):
    """
    Create Location nodes — the shared anchor
    that connects all three agents.
    """
    locations = [
        # Major regions that appear in both geospatial
        # and asteroid approach data
        {"region": "Maharashtra",    "country": "India",
         "lat": 19.7, "lon": 75.7},
        {"region": "Rajasthan",      "country": "India",
         "lat": 27.0, "lon": 74.2},
        {"region": "Andhra Pradesh", "country": "India",
         "lat": 15.9, "lon": 79.7},
        {"region": "Punjab",         "country": "India",
         "lat": 31.1, "lon": 75.3},
        {"region": "Tamil Nadu",     "country": "India",
         "lat": 11.1, "lon": 78.7},
        {"region": "West Bengal",    "country": "India",
         "lat": 22.9, "lon": 87.8},
        {"region": "Karnataka",      "country": "India",
         "lat": 15.3, "lon": 75.7},
        {"region": "Gujarat",        "country": "India",
         "lat": 22.3, "lon": 72.6},
        # ISRO launch site — critical for ISRO agent link
        {"region": "Sriharikota",    "country": "India",
         "lat": 13.7, "lon": 80.2,
         "is_launch_site": True},
        {"region": "Indian Ocean",   "country": None,
         "lat": 10.0, "lon": 75.0},
        {"region": "India",          "country": "India",
         "lat": 20.6, "lon": 78.9},
    ]

    for loc in locations:
        session.run("""
            MERGE (l:Location {region: $region})
            SET l.country = $country,
                l.latitude = $lat,
                l.longitude = $lon,
                l.is_launch_site = $is_launch_site
        """, {
            'region':         loc['region'],
            'country':        loc.get('country'),
            'lat':            loc['lat'],
            'lon':            loc['lon'],
            'is_launch_site': loc.get('is_launch_site', False),
        })

    print(f"Created {len(locations)} Location nodes.")


def seed_zone_nodes(session):
    """
    Create Zone nodes from ndvi_results PostgreSQL table.
    One node per zone per year with NDVI statistics.
    """
    df = pd.read_sql("""
        SELECT
            n.zone_name,
            n.year,
            n.ndvi_mean,
            n.ndvi_min,
            n.ndvi_max,
            n.delta_total_mean,
            n.delta_recent_mean,
            n.change_class,
            n.change_class_label,
            n.confidence,
            n.verification_hash,
            a.states
        FROM ndvi_results n
        JOIN aoi_metadata a ON n.aoi_id = a.id
        ORDER BY zone_name, year
    """, conn)

    for _, row in df.iterrows():
        session.run("""
            MERGE (z:Zone {name: $zone_name})
            SET z.states = $states

            MERGE (o:NDVIObservation {
                id: $obs_id
            })
            SET o.year         = $year,
                o.ndvi_mean    = $ndvi_mean,
                o.ndvi_min     = $ndvi_min,
                o.ndvi_max     = $ndvi_max,
                o.delta_total  = $delta_total,
                o.delta_recent = $delta_recent,
                o.change_class = $change_class,
                o.change_label = $change_label,
                o.confidence   = $confidence,
                o.verified_hash= $hash

            MERGE (z)-[:HAS_OBSERVATION]->(o)
        """, {
            'zone_name':    row['zone_name'],
            'states':       row['states'],
            'obs_id':       f"{row['zone_name']}_{row['year']}",
            'year':         int(row['year']),
            'ndvi_mean':    float(row['ndvi_mean']),
            'ndvi_min':     float(row['ndvi_min']),
            'ndvi_max':     float(row['ndvi_max']),
            'delta_total':  float(row['delta_total_mean']),
            'delta_recent': float(row['delta_recent_mean']),
            'change_class': int(row['change_class']),
            'change_label': row['change_class_label'],
            'confidence':   float(row['confidence']),
            'hash':         row['verification_hash'],
        })

    print(f"Created Zone and NDVIObservation nodes — {len(df)} observations.")


def seed_change_edges(session):
    """
    Create LandCoverChange nodes and connect them to Zones.
    These represent detected changes with evidence.
    """
    df = pd.read_sql("""
        SELECT DISTINCT
            n.zone_name,
            n.change_class,
            n.change_class_label,
            n.delta_total_mean,
            n.confidence,
            n.verification_hash
        FROM ndvi_results n
        JOIN aoi_metadata a ON n.aoi_id = a.id
        WHERE n.year = 2024
        ORDER BY zone_name
    """, conn)

    for _, row in df.iterrows():
        session.run("""
            MERGE (z:Zone {name: $zone_name})
            MERGE (c:LandCoverChange {
                id: $change_id
            })
            SET c.type       = $change_type,
                c.magnitude  = $magnitude,
                c.confidence = $confidence,
                c.year       = 2024,
                c.hash       = $hash

            MERGE (z)-[:SHOWS_CHANGE {
                magnitude:  $magnitude,
                confidence: $confidence,
                year:       2024
            }]->(c)
        """, {
            'zone_name':   row['zone_name'],
            'change_id':   f"change_{row['zone_name']}_2024",
            'change_type': row['change_class_label'],
            'magnitude':   float(row['delta_total_mean']),
            'confidence':  float(row['confidence']),
            'hash':        row['verification_hash'],
        })

    print(f"Created {len(df)} LandCoverChange nodes with SHOWS_CHANGE edges.")


def seed_zone_location_edges(session):
    """
    Connect Zone nodes to Location nodes.
    This is what enables cross-domain queries.
    """
    zone_to_location = {
        'maharashtra_marathwada':   'Maharashtra',
        'maharashtra_vidarbha':     'Maharashtra',
        'rajasthan':                'Rajasthan',
        'andhra_telangana_coast':   'Andhra Pradesh',
        'punjab_haryana_delhi':     'Punjab',
        'tamil_nadu_puducherry':    'Tamil Nadu',
        'west_bengal_sikkim':       'West Bengal',
        'karnataka_goa':            'Karnataka',
        'gujarat_dadra_dd':         'Gujarat',
        'andhra_telangana_coast':   'Sriharikota',
    }

    for zone, location in zone_to_location.items():
        session.run("""
            MATCH (z:Zone {name: $zone})
            MATCH (l:Location {region: $location})
            MERGE (z)-[:LOCATED_IN]->(l)
        """, {'zone': zone, 'location': location})

    print(f"Created LOCATED_IN edges for {len(zone_to_location)} zones.")


def seed_asteroid_nodes(session):
    """
    Create Asteroid nodes from PostgreSQL asteroid ML table.
    Connect high-risk and anomalous asteroids to Location nodes
    via PASSED_OVER edges — the first cross-agent connection.
    """
    # Load high-risk asteroids with approach data
    try:
        asteroids = pd.read_sql("""
            SELECT
                asteroid_id AS des,
                risk_category,
                improved_risk_score,
                is_anomaly,
                anomaly_score,
                cluster,
                adaptive_risk_category,
                verification_hash
            FROM astronomy.asteroid_ml_predictions
            WHERE risk_category IN ('High', 'Medium')
            OR is_anomaly = true
            LIMIT 500
        """, conn)
    except Exception as e:
        print(f"Skipping seed_asteroid_nodes due to error: {e}")
        return

    for _, row in asteroids.iterrows():
        session.run("""
            MERGE (a:Asteroid {designation: $des})
            SET a.risk_category    = $risk_cat,
                a.risk_score       = $risk_score,
                a.is_anomaly       = $is_anomaly,
                a.anomaly_score    = $anomaly_score,
                a.cluster          = $cluster,
                a.adaptive_category= $adaptive_cat,
                a.verified_hash    = $hash
        """, {
            'des':         row['des'],
            'risk_cat':    row['risk_category'],
            'risk_score':  float(row['improved_risk_score']),
            'is_anomaly':  bool(row['is_anomaly']),
            'anomaly_score':float(row['anomaly_score']),
            'cluster':     int(row['cluster']),
            'adaptive_cat':row['adaptive_risk_category'],
            'hash':        row['verification_hash'],
        })

    print(f"Created {len(asteroids)} Asteroid nodes.")


def create_cross_agent_edges(session):
    """
    THE KEY STEP — connect asteroids to locations.
    This is the first real multi-hop GraphRAG connection
    between the Astronomy Agent and Geospatial Agent.

    High-risk asteroids that approach Earth are connected
    to Indian Ocean / India location nodes.
    These same location nodes connect to Zone nodes
    which connect to NDVIObservation nodes.

    This enables the query:
    "Were any anomalous asteroids approaching during
     periods of vegetation stress in Maharashtra?"
    """
    # Connect high-risk asteroids to India region
    session.run("""
        MATCH (a:Asteroid)
        WHERE a.risk_category = 'High'
        MATCH (l:Location {region: 'India'})
        MERGE (a)-[:APPROACH_RISK {
            note: 'Planetary close approach — India region'
        }]->(l)
    """)

    # Connect anomalous asteroids to Indian Ocean
    # (relevant for ISRO tracking)
    session.run("""
        MATCH (a:Asteroid)
        WHERE a.is_anomaly = true
        MATCH (l:Location {region: 'Indian Ocean'})
        MERGE (a)-[:ANOMALOUS_PASS_NEAR]->(l)
    """)

    # Connect Sriharikota launch site to
    # nearby Andhra/Telangana zone
    session.run("""
        MATCH (l:Location {region: 'Sriharikota'})
        MATCH (z:Zone {name: 'andhra_telangana_coast'})
        MERGE (l)-[:WITHIN_ZONE]->(z)
    """)

    print("Cross-agent edges created — Astronomy ↔ Geospatial connected.")


def verify_graph(session):
    """Print graph summary to confirm everything loaded."""
    counts = session.run("""
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
    """).data()

    edges = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(r) AS count
        ORDER BY count DESC
    """).data()

    print("\n" + "=" * 50)
    print("GRAPH SUMMARY")
    print("=" * 50)
    print("Nodes:")
    for row in counts:
        print(f"  {row['label']:<25}: {row['count']}")
    print("\nEdges:")
    for row in edges:
        print(f"  {row['rel_type']:<30}: {row['count']}")

    # Test the key cross-domain query
    result = session.run("""
        MATCH (a:Asteroid)-[:APPROACH_RISK]->(l:Location)
              <-[:LOCATED_IN]-(z:Zone)
              -[:SHOWS_CHANGE]->(c:LandCoverChange)
        WHERE c.type = 'vegetation_loss'
        RETURN a.designation AS asteroid,
               l.region      AS location,
               z.name        AS zone,
               c.confidence  AS confidence
        LIMIT 5
    """).data()

    print("\nFirst cross-domain query result:")
    print("(High-risk asteroids → India → zones with vegetation loss)")
    if result:
        for row in result:
            print(f"  {row['asteroid']} → {row['location']}"
                  f" → {row['zone']} "
                  f"(confidence: {row['confidence']:.2f})")
    else:
        print("  No results yet — add more data to see connections")

    print("=" * 50)


# ── Run everything ───────────────────────────────────────────
if __name__ == '__main__':
    print("Seeding AstroGeo knowledge graph...\n")

    with driver.session() as session:
        create_constraints(session)
        seed_location_nodes(session)
        seed_zone_nodes(session)
        seed_change_edges(session)
        seed_zone_location_edges(session)
        seed_asteroid_nodes(session)
        create_cross_agent_edges(session)
        verify_graph(session)

    driver.close()
    conn.close()
    print("\nDone. GraphRAG foundation is live.")
    print("Next: build LangGraph orchestration skeleton")