# orchestrator/langgraph_agent.py

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional
from psycopg2 import pool as pg_pool
import pandas as pd
import os
from dotenv import load_dotenv

from backend.db.pools import get_neo4j_driver


# Explicitly load backend/.env since we run from project root
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# ── PostgreSQL pool (one pool per API worker; avoids connect-per-query) ──
_pg_pool: Optional[pg_pool.ThreadedConnectionPool] = None


def _get_pg_pool() -> pg_pool.ThreadedConnectionPool:
    global _pg_pool
    if _pg_pool is None:
        max_conn = int(os.getenv("LANGGRAPH_PG_POOL_MAX", "12"))
        _pg_pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=max(2, max_conn),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD", ""),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
        )
    return _pg_pool


def close_langgraph_pg_pool() -> None:
    global _pg_pool
    if _pg_pool is not None:
        _pg_pool.closeall()
        _pg_pool = None


# ── Shared state ──────────────────────────────────────────────
class AstroGeoState(TypedDict):
    query:              str
    query_domain:       str
    simplify:           bool          # ← NEW: plain English mode
    asteroid_context:   Optional[dict]
    geospatial_context: Optional[dict]
    agro_context:       Optional[dict]       # ← NEW: agro explicit context
    solar_context:      Optional[dict]
    graph_context:      Optional[list]
    final_answer:       Optional[str]
    evidence_chain:     list

# ── LLM ──────────────────────────────────────────────────────
llm = ChatOpenAI(
    model='gpt-4o-mini',
    api_key=os.getenv('OPENAI_API_KEY')
)

# ── Node 1: Router ────────────────────────────────────────────
def router_node(state: AstroGeoState) -> AstroGeoState:
    prompt = f"""
    Classify this scientific query into exactly one domain:
    - astronomy  (asteroids, orbits, ISS, space events)
    - geospatial (vegetation, land cover, NDVI, urban growth)
    - agro       (crops, drought, rainfall, food prices)
    - solar      (solar flares, geomagnetic storms, space weather, GPS disruption, irrigation)
    - cross      (requires multiple domains)

    Query: {state['query']}

    Respond with just the domain word. Nothing else.
    """
    response = llm.invoke(prompt)
    domain = response.content.strip().lower()

    # Sanitise — fallback to cross if unexpected output
    if domain not in ('astronomy', 'geospatial', 'agro', 'solar', 'cross'):
        domain = 'cross'

    state['query_domain'] = domain
    state['evidence_chain'].append({
        'step':   'router',
        'domain': domain,
    })
    print(f"[Router] Domain classified as: {domain}")
    return state

# ── Node 2: Astronomy Agent ───────────────────────────────────
def astronomy_node(state: AstroGeoState) -> AstroGeoState:
    if state['query_domain'] not in ('astronomy', 'cross'):
        print("[Astronomy] Skipped — not relevant domain")
        return state

    conn = None
    try:
        p = _get_pg_pool()
        conn = p.getconn()
        df = pd.read_sql("""
            SELECT asteroid_id AS des, risk_category, improved_risk_score,
                   is_anomaly, anomaly_score, cluster
            FROM astronomy.asteroid_ml_predictions
            WHERE risk_category = 'High' OR is_anomaly = true
            ORDER BY improved_risk_score DESC
            LIMIT 10
        """, conn)

        state['asteroid_context'] = {
            'high_risk_count': int(len(df[df['risk_category'] == 'High'])),
            'anomaly_count':   int(len(df[df['is_anomaly'] == True])),
            'top_risks':       df.head(3).to_dict('records'),
        }
        state['evidence_chain'].append({
            'step':   'astronomy_agent',
            'source': 'PostgreSQL asteroid_ml_predictions',
            'rows':   len(df),
        })
        print(f"[Astronomy] Loaded {len(df)} high-risk asteroids")

    except Exception as e:
        print(f"[Astronomy] DB error: {e}")
        state['asteroid_context'] = {'error': str(e)}
    finally:
        if conn is not None:
            try:
                _get_pg_pool().putconn(conn)
            except Exception:
                pass

    return state

# ── Node 3: Geospatial Agent ──────────────────────────────────
def geospatial_node(state: AstroGeoState) -> AstroGeoState:
    if state['query_domain'] not in ('geospatial', 'cross', 'solar'):
        print("[Geospatial] Skipped — not relevant domain")
        return state

    conn = None
    try:
        p = _get_pg_pool()
        conn = p.getconn()
        df = pd.read_sql("""
            SELECT zone_name, year, ndvi_mean,
                   change_class_label, confidence,
                   delta_total_mean
            FROM ndvi_results
            WHERE year = 2024
            AND change_class IN (1, 2)
            ORDER BY delta_total_mean ASC
            LIMIT 10
        """, conn)

        state['geospatial_context'] = {
            'vegetation_loss_zones': df[
                df['change_class_label'] == 'vegetation_loss'
            ]['zone_name'].tolist(),
            'urban_growth_zones': df[
                df['change_class_label'] == 'urban_growth'
            ]['zone_name'].tolist(),
            'worst_decline': df.head(3).to_dict('records'),
        }
        state['evidence_chain'].append({
            'step':   'geospatial_agent',
            'source': 'PostgreSQL ndvi_results',
            'rows':   len(df),
        })
        print(f"[Geospatial] Loaded {len(df)} zone records")

    except Exception as e:
        print(f"[Geospatial] DB error: {e}")
        state['geospatial_context'] = {'error': str(e)}
    finally:
        if conn is not None:
            try:
                _get_pg_pool().putconn(conn)
            except Exception:
                pass

    return state

# ── Node 3.5: Agro Agent ──────────────────────────────────────
def agro_node(state: AstroGeoState) -> AstroGeoState:
    if state['query_domain'] not in ('agro', 'cross'):
        print("[Agro] Skipped — not relevant domain")
        return state

    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
        )
        
        # Pull high risk / drought zones
        df = pd.read_sql("""
            SELECT zone_name, ndvi_mean, delta_total_mean as ndvi_drop, change_class_label
            FROM ndvi_results
            WHERE year = 2024
            ORDER BY ndvi_mean ASC
            LIMIT 5
        """, conn)

        # Check for specific districts in query
        district_query = state['query'].lower()
        specific_zone = next((z for z in ['marathwada', 'vidarbha', 'maharashtra', 'punjab', 'rajasthan'] if z in district_query), None)

        if specific_zone:
            specific_df = pd.read_sql(f"""
                SELECT zone_name, ndvi_mean, delta_total_mean as ndvi_drop, change_class_label
                FROM ndvi_results
                WHERE year = 2024 AND LOWER(zone_name) LIKE '%%{specific_zone}%%'
                LIMIT 1
            """, conn)
            if not specific_df.empty:
                df = pd.concat([df, specific_df]).drop_duplicates(subset=['zone_name'])

        conn.close()

        drought_scores = []
        for _, row in df.iterrows():
            drought_score = min(1.0, max(0.0, 0.5 + (-row['ndvi_drop'] * 2)))
            drought_scores.append({
                'zone': row['zone_name'],
                'drought_score': float(round(drought_score, 2)),
                'risk_level': 'Severe' if drought_score > 0.7 else 'Moderate' if drought_score > 0.4 else 'Mild',
            })

        state['agro_context'] = {
            'monitored_zones': len(drought_scores),
            'drought_data': drought_scores,
            'advice': "If drought risk is Severe or Moderate, delaying irrigation might stress crops further unless water reserves are critical, in which case precision GPS irrigation is advised. Note: Solar events may disrupt GPS precision irrigation."
        }
        state['evidence_chain'].append({
            'step':   'agro_agent',
            'source': 'PostgreSQL ndvi_results (Drought metrics)',
            'rows':   len(drought_scores),
        })
        print(f"[Agro] Loaded {len(drought_scores)} drought records")

    except Exception as e:
        print(f"[Agro] DB error: {e}")
        state['agro_context'] = {'error': str(e)}

    return state

# ── Node 4: Solar Flare Agent ─────────────────────────────────
def solar_node(state: AstroGeoState) -> AstroGeoState:
    """
    Queries Neo4j for solar events and their disruption risk
    to Indian agricultural zones. Runs for 'solar' and 'cross'
    domains. This is the cross-domain bridge:
    Space Weather → GPS Disruption → Smart Irrigation Failure
    → Crop Stress in already drought-vulnerable zones.
    """
    if state['query_domain'] not in ('solar', 'cross'):
        print("[Solar] Skipped — not relevant domain")
        return state

    try:
        driver = get_neo4j_driver()
        db_name = os.getenv("NEO4J_DATABASE")

        with driver.session(database=db_name) as session:

            # 1. Recent high-impact solar events
            recent_events = session.run("""
                MATCH (e:SolarEvent)
                WHERE e.disruption_risk > 0.3
                RETURN e.date         AS date,
                       e.event_type   AS type,
                       e.intensity    AS intensity,
                       e.kp_index     AS kp_index,
                       e.disruption_risk AS risk,
                       e.description  AS description
                ORDER BY e.disruption_risk DESC
                LIMIT 5
            """).data()

            # 2. Cross-domain: solar event → disrupted region
            #    → vulnerable zone → land cover change
            cross_domain = session.run("""
                MATCH (e:SolarEvent)-[:DISRUPTS]->(r:Region)
                      <-[:PART_OF]-(z:Zone)
                      -[:SHOWS_CHANGE]->(c:LandCoverChange)
                WHERE e.disruption_risk > 0.4
                RETURN e.date           AS event_date,
                       e.intensity      AS intensity,
                       e.disruption_risk AS risk,
                       r.name           AS region,
                       z.name           AS zone,
                       c.type           AS land_change,
                       c.confidence     AS confidence
                ORDER BY e.disruption_risk DESC, c.confidence DESC
                LIMIT 5
            """).data()

            # 3. Storm frequency per region — which regions hit most
            region_exposure = session.run("""
                MATCH (e:SolarEvent)-[d:DISRUPTS]->(r:Region)
                WHERE e.disruption_risk > 0.3
                RETURN r.name          AS region,
                       count(e)        AS storm_count,
                       avg(d.risk_score) AS avg_risk
                ORDER BY storm_count DESC
            """).data()

        state['solar_context'] = {
            'recent_high_risk_events': recent_events,
            'cross_domain_impacts':    cross_domain,
            'most_exposed_regions':    region_exposure[:3],
            'total_events_found':      len(recent_events),
        }
        state['evidence_chain'].append({
            'step':          'solar_agent',
            'source':        'Neo4j — SolarEvent nodes (NASA DONKI)',
            'events_found':  len(recent_events),
            'cross_impacts': len(cross_domain),
        })
        print(f"[Solar] {len(recent_events)} high-risk events, "
              f"{len(cross_domain)} cross-domain impacts found")

    except Exception as e:
        print(f"[Solar] Neo4j error: {e}")
        state['solar_context'] = {'error': str(e)}

    return state

# ── Node 5: GraphRAG Node ─────────────────────────────────────
def graphrag_node(state: AstroGeoState) -> AstroGeoState:
    try:
        driver = get_neo4j_driver()
        db_name = os.getenv("NEO4J_DATABASE")

        with driver.session(database=db_name) as session:
            if state['query_domain'] == 'solar':
                # Solar-specific multi-hop already handled in solar_node
                # GraphRAG adds the agriculture connection on top
                results = session.run("""
                    MATCH (e:SolarEvent)-[:DISRUPTS]->(r:Region)
                          <-[:PART_OF]-(z:Zone)
                    WHERE e.disruption_risk > 0.4
                    RETURN e.date        AS event_date,
                           e.intensity   AS solar_intensity,
                           r.name        AS affected_region,
                           z.name        AS vulnerable_zone,
                           e.description AS impact_description
                    ORDER BY e.disruption_risk DESC
                    LIMIT 5
                """).data()

            elif state['query_domain'] == 'cross':
                # Full multi-hop: asteroids → location → zone → change
                results = session.run("""
                    MATCH (a:Asteroid)-[:APPROACH_RISK]->(l:Location)
                          <-[:LOCATED_IN]-(z:Zone)
                          -[:SHOWS_CHANGE]->(c:LandCoverChange)
                    RETURN a.designation  AS asteroid,
                           a.risk_category AS risk,
                           l.region        AS location,
                           z.name          AS zone,
                           c.type          AS change_type,
                           c.confidence    AS confidence
                    ORDER BY c.confidence DESC
                    LIMIT 5
                """).data()

            elif state['query_domain'] == 'astronomy':
                results = session.run("""
                    MATCH (a:Asteroid)
                    RETURN a.designation  AS asteroid,
                           a.risk_category AS risk,
                           a.anomaly_score AS anomaly_score
                    ORDER BY a.anomaly_score DESC
                    LIMIT 5
                """).data()

            else:
                # geospatial or agro
                results = session.run("""
                    MATCH (z:Zone)-[:SHOWS_CHANGE]->(c:LandCoverChange)
                    RETURN z.name        AS zone,
                           c.type        AS change_type,
                           c.confidence  AS confidence
                    ORDER BY c.confidence DESC
                    LIMIT 5
                """).data()

        state['graph_context'] = results
        state['evidence_chain'].append({
            'step':    'graphrag',
            'source':  'Neo4j AuraDB',
            'results': len(results),
        })
        print(f"[GraphRAG] Retrieved {len(results)} graph results")

    except Exception as e:
        print(f"[GraphRAG] Neo4j error: {e}")
        state['graph_context'] = []

    return state

# ── Node 6: Synthesiser ───────────────────────────────────────
def synthesiser_node(state: AstroGeoState) -> AstroGeoState:
    context_parts = []

    if state.get('asteroid_context') and 'error' not in state['asteroid_context']:
        context_parts.append(f"Asteroid data: {state['asteroid_context']}")

    if state.get('geospatial_context') and 'error' not in state['geospatial_context']:
        context_parts.append(f"Geospatial data: {state['geospatial_context']}")

    if state.get('solar_context') and 'error' not in state['solar_context']:
        context_parts.append(f"Solar weather data: {state['solar_context']}")

    if state.get('agro_context') and 'error' not in state['agro_context']:
        context_parts.append(f"Agro data (Drought metrics): {state['agro_context']}")

    if state.get('graph_context'):
        context_parts.append(f"Cross-domain graph results: {state['graph_context']}")

    if not context_parts:
        state['final_answer'] = "No data could be retrieved for this query."
        return state

    simplify = state.get('simplify', False)

    if simplify:
        system_prompt = """
You are AstroGeo, an AI assistant explaining space and Earth data to non-scientists.

Rewrite the evidence below in plain, jargon-free language:
- Replace 'Kp-index 9.0 / G5 geomagnetic storm' with 'a very powerful space storm'
- Replace 'NDVI delta / vegetation stress anomaly' with 'plants showing signs of damage or poor health'
- Replace 'Isolation Forest anomaly score' with 'our AI flagged this as unusual'
- Replace 'kinetic_energy_proxy' with 'how dangerous the asteroid could be if it hit Earth'
- Replace 'SHAP feature contribution' with 'the main reason our model gave this result'
- Replace '4-hop graph traversal' with 'we traced the connection through four linked data sources'
- Replace 'ERA5 precipitation' with 'rainfall recorded at the launch site'
- Replace 'monsoon_season flag' with 'whether it is monsoon season'
- Replace 'ROC-AUC' with 'model reliability'
- Replace 'LandCoverChange: Urban Encroachment' with 'farmland being replaced by buildings'
- Replace 'SHA-256 verified' with 'this prediction has been checked and has not been altered'

Do NOT mention model names, Cypher paths, confidence scores, or evidence chain steps.
Lead with the practical implication for the user.
Write in 2-3 sentences maximum.
End with a one-sentence action recommendation if relevant.
"""
    else:
        system_prompt = """
You are AstroGeo, a scientific AI assistant specialising in
astronomy, space weather, and Earth observation over India.

Answer the following query using ONLY the provided evidence.
Be precise, cite specific values, and acknowledge uncertainty.

When solar/geomagnetic data is present, explain the causal chain:
Solar Event → GPS Degradation → Smart Irrigation Disruption
→ Agricultural Impact in vulnerable zones.

Provide a concise scientific answer with specific numbers where available.
"""

    prompt = f"""{system_prompt}

Query: {state['query']}

Evidence gathered:
{chr(10).join(context_parts)}
"""

    response = llm.invoke(prompt)
    state['final_answer'] = response.content
    state['evidence_chain'].append({
        'step':  'synthesiser',
        'model': 'gpt-4o-mini',
    })
    print(f"[Synthesiser] Answer generated (simplify={simplify})")
    return state

# ── Routing logic ─────────────────────────────────────────────
def route_after_router(state: AstroGeoState) -> str:
    domain = state.get('query_domain', 'cross')
    if domain == 'astronomy':
        return 'astronomy'
    elif domain == 'geospatial':
        return 'geospatial'
    elif domain == 'agro':
        return 'agro'
    elif domain == 'solar':
        return 'solar'
    else:
        return 'astronomy'  # cross: run all via sequence

# ── Build the graph ───────────────────────────────────────────
def build_astrogeo_graph():
    graph = StateGraph(AstroGeoState)

    graph.add_node('router',      router_node)
    graph.add_node('astronomy',   astronomy_node)
    graph.add_node('geospatial',  geospatial_node)
    graph.add_node('agro',        agro_node)        # ← NEW
    graph.add_node('solar',       solar_node)
    graph.add_node('graphrag',    graphrag_node)
    graph.add_node('synthesiser', synthesiser_node)

    graph.add_edge(START, 'router')

    graph.add_conditional_edges(
        'router',
        route_after_router,
        {
            'astronomy':  'astronomy',
            'geospatial': 'geospatial',
            'agro':       'agro',           # ← NEW
            'solar':      'solar',
        }
    )

    # All paths converge into graphrag → synthesiser
    graph.add_edge('astronomy',  'geospatial')
    graph.add_edge('geospatial', 'agro')            # ← NEW
    graph.add_edge('agro',       'solar')           # ← NEW
    graph.add_edge('solar',      'graphrag')
    graph.add_edge('graphrag',   'synthesiser')
    graph.add_edge('synthesiser', END)

    return graph.compile()


# ── Compiled graph (rebuilding on every request exhausts CPU under load) ──
_compiled_graph = None


def _get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_astrogeo_graph()
    return _compiled_graph


# ── Public API ────────────────────────────────────────────────
def run_query(query: str, simplify: bool = False) -> dict:
    initial_state = {"query": query, "evidence_chain": [], "simplify": simplify}
    return _get_compiled_graph().invoke(initial_state)

# ── Test ──────────────────────────────────────────────────────
if __name__ == '__main__':
    test_queries = [
        # Original 3
        "Which regions in India show the most vegetation loss?",
        "What are the highest risk asteroids right now?",
        "Were any dangerous asteroids approaching India during periods of vegetation stress?",
        # New solar queries
        "Did any solar flares disrupt smart irrigation in Maharashtra?",
        "Which Indian farming regions are most at risk from geomagnetic storms?",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        result = run_query(query)
        print(f"\nDomain:         {result['query_domain']}")
        print(f"Answer:\n{result['final_answer']}")
        print(f"Evidence steps: {len(result['evidence_chain'])}")