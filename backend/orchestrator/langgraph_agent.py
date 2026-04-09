# orchestrator/langgraph_agent.py

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional
import psycopg2
import pandas as pd
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

# ── Shared state ──────────────────────────────────────────────
class AstroGeoState(TypedDict):
    query:              str
    query_domain:       str
    asteroid_context:   Optional[dict]
    geospatial_context: Optional[dict]
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
    - cross      (requires multiple domains)

    Query: {state['query']}

    Respond with just the domain word. Nothing else.
    """
    response = llm.invoke(prompt)
    domain = response.content.strip().lower()
    
    # Sanitise — fallback to cross if unexpected output
    if domain not in ('astronomy', 'geospatial', 'agro', 'cross'):
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

    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
        )
        df = pd.read_sql("""
            SELECT asteroid_id AS des, risk_category, improved_risk_score,
                   is_anomaly, anomaly_score, cluster
            FROM astronomy.asteroid_ml_predictions
            WHERE risk_category = 'High' OR is_anomaly = true
            ORDER BY improved_risk_score DESC
            LIMIT 10
        """, conn)
        conn.close()

        state['asteroid_context'] = {
            'high_risk_count': int(len(df[df['risk_category'] == 'High'])),
            'anomaly_count':   int(len(df[df['is_anomaly'] == True])),
            'top_risks':       df.head(3).to_dict('records'),
        }
        state['evidence_chain'].append({
            'step':   'astronomy_agent',
            'source': 'PostgreSQL asteroid_ml_results',
            'rows':   len(df),
        })
        print(f"[Astronomy] Loaded {len(df)} high-risk asteroids")

    except Exception as e:
        print(f"[Astronomy] DB error: {e}")
        state['asteroid_context'] = {'error': str(e)}

    return state

# ── Node 3: Geospatial Agent ──────────────────────────────────
def geospatial_node(state: AstroGeoState) -> AstroGeoState:
    if state['query_domain'] not in ('geospatial', 'cross'):
        print("[Geospatial] Skipped — not relevant domain")
        return state

    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
        )
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
        conn.close()

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

    return state

# ── Node 4: GraphRAG Node ─────────────────────────────────────
def graphrag_node(state: AstroGeoState) -> AstroGeoState:
    try:
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )

        with driver.session() as session:
            if state['query_domain'] == 'cross':
                # Multi-hop: asteroids → location → zone → change
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
                    RETURN a.designation AS asteroid,
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

        driver.close()

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

# ── Node 5: Synthesiser ───────────────────────────────────────
def synthesiser_node(state: AstroGeoState) -> AstroGeoState:
    context_parts = []

    if state.get('asteroid_context') and 'error' not in state['asteroid_context']:
        context_parts.append(f"Asteroid data: {state['asteroid_context']}")

    if state.get('geospatial_context') and 'error' not in state['geospatial_context']:
        context_parts.append(f"Geospatial data: {state['geospatial_context']}")

    if state.get('graph_context'):
        context_parts.append(f"Cross-domain graph results: {state['graph_context']}")

    if not context_parts:
        state['final_answer'] = "No data could be retrieved for this query."
        return state

    prompt = f"""
    You are AstroGeo, a scientific AI assistant specialising in
    astronomy and Earth observation over India.

    Answer the following query using ONLY the provided evidence.
    Be precise, cite specific values, and acknowledge uncertainty.

    Query: {state['query']}

    Evidence gathered:
    {chr(10).join(context_parts)}

    Provide a concise scientific answer with specific numbers where available.
    """

    response = llm.invoke(prompt)
    state['final_answer'] = response.content
    state['evidence_chain'].append({
        'step':  'synthesiser',
        'model': 'gpt-4o-mini',
    })
    print("[Synthesiser] Answer generated")
    return state

# ── Routing logic ─────────────────────────────────────────────
def route_after_router(state: AstroGeoState) -> str:
    domain = state.get('query_domain', 'cross')
    if domain == 'astronomy':
        return 'astronomy'
    elif domain == 'geospatial':
        return 'geospatial'
    else:
        return 'astronomy'  # cross/agro: run both via sequence

# ── Build the graph ───────────────────────────────────────────
def build_astrogeo_graph():
    graph = StateGraph(AstroGeoState)

    graph.add_node('router',      router_node)
    graph.add_node('astronomy',   astronomy_node)
    graph.add_node('geospatial',  geospatial_node)
    graph.add_node('graphrag',    graphrag_node)
    graph.add_node('synthesiser', synthesiser_node)

    graph.add_edge(START, 'router')

    graph.add_conditional_edges(
        'router',
        route_after_router,
        {
            'astronomy':  'astronomy',
            'geospatial': 'geospatial',
        }
    )

    # All paths flow through geospatial → graphrag → synthesiser
    graph.add_edge('astronomy',  'geospatial')
    graph.add_edge('geospatial', 'graphrag')
    graph.add_edge('graphrag',   'synthesiser')
    graph.add_edge('synthesiser', END)

    return graph.compile()

# ── Public API ────────────────────────────────────────────────
def run_query(query: str) -> dict:
    app = build_astrogeo_graph()
    initial_state = {"query": query, "evidence_chain": []}
    return app.invoke(initial_state)

# ── Test ──────────────────────────────────────────────────────
if __name__ == '__main__':
    test_queries = [
        "Which regions in India show the most vegetation loss?",
        "What are the highest risk asteroids right now?",
        "Were any dangerous asteroids approaching India during periods of vegetation stress?",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        result = run_query(query)
        print(f"\nDomain:          {result['query_domain']}")
        print(f"Answer:\n{result['final_answer']}")
        print(f"Evidence steps:  {len(result['evidence_chain'])}")