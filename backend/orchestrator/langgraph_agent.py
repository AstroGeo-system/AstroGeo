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
# Temporal keywords that indicate the user wants recent/upcoming data
_FUTURE_KEYWORDS = {
    'approaching', 'upcoming', 'future', 'going to', 'will there',
    'next', 'soon', 'forecast', 'predict', 'incoming', 'imminent',
    'expected', 'about to', 'coming', 'ahead',
}

class AstroGeoState(TypedDict):
    query:              str
    query_domain:       str
    simplify:           bool          # plain English mode
    temporal_intent:    str           # 'recent' | 'historical' | 'any'
    asteroid_context:   Optional[dict]
    geospatial_context: Optional[dict]
    agro_context:       Optional[dict]
    solar_context:      Optional[dict]
    graph_context:      Optional[list]
    final_answer:       Optional[str]
    evidence_chain:     list

# ── LLM ──────────────────────────────────────────────────────
llm = ChatOpenAI(
    model='gpt-4o-mini',
    api_key=os.getenv('OPENAI_API_KEY')
)

# ── Keyword → domain map (checked BEFORE the LLM to guarantee correct routing) ─
# Longer / more specific phrases are checked first (dict is ordered in Python 3.7+).
_KEYWORD_DOMAIN: list[tuple[str, str]] = [
    # ── Solar (must beat cross for explict solar terms) ──────────
    ('solar flare',          'solar'),
    ('geomagnetic storm',    'solar'),
    ('geomagnetic',          'solar'),
    ('space weather',        'solar'),
    ('kp index',             'solar'),
    ('kp-index',             'solar'),
    ('solar storm',          'solar'),
    ('cme',                  'solar'),
    ('donki',                'solar'),
    ('magnetosphere',        'solar'),
    ('aurora',               'solar'),
    # ── Astronomy / launch / ML ──────────────────────────────────
    ('shap',                 'astronomy'),
    ('launch failure',       'astronomy'),
    ('launch risk',          'astronomy'),
    ('launch probability',   'astronomy'),
    ('launch success',       'astronomy'),
    ('kinetic energy proxy', 'astronomy'),
    ('anomaly score',        'astronomy'),
    ('risk category',        'astronomy'),
    ('risk score',           'astronomy'),
    ('feature importance',   'astronomy'),
    ('ml model',             'astronomy'),
    ('asteroid',             'astronomy'),
    ('near-earth',           'astronomy'),
    ('orbit',                'astronomy'),
    ('iss ',                 'astronomy'),
    ('isro',                 'astronomy'),
    # ── Geospatial ───────────────────────────────────────────────
    ('ndvi',                 'geospatial'),
    ('vegetation',           'geospatial'),
    ('land cover',           'geospatial'),
    ('urban growth',         'geospatial'),
    ('deforestation',        'geospatial'),
    # ── Agro ─────────────────────────────────────────────────────
    ('drought',              'agro'),
    ('crop',                 'agro'),
    ('rainfall',             'agro'),
    ('monsoon',              'agro'),
    ('food price',           'agro'),
]

# ── Node 1: Router ────────────────────────────────────────────
def router_node(state: AstroGeoState) -> AstroGeoState:
    query_lower = state['query'].lower()

    # 1. Deterministic keyword pre-routing (fast, reliable, no LLM needed)
    domain = None
    for keyword, mapped_domain in _KEYWORD_DOMAIN:
        if keyword in query_lower:
            domain = mapped_domain
            print(f"[Router] Keyword match: '{keyword}' → {mapped_domain}")
            break

    # 2. LLM routing only for queries with no keyword match
    if domain is None:
        prompt = f"""
    Classify this scientific query into exactly one domain.
    Choose the MOST SPECIFIC single domain. Only use 'cross' when the query
    explicitly connects two or more different domains in one question.

    Domains:
    - astronomy  : asteroids, orbits, launch risk, ML predictions, ISS, space missions
    - geospatial : vegetation, NDVI, land cover, satellite imagery
    - agro       : crops, drought, rainfall, food prices, monsoon
    - solar      : solar flares, geomagnetic storms, space weather, Kp index, GPS
    - cross      : ONLY for explicit cross-domain, e.g. "Did the solar storm affect crops?"

    Query: {state['query']}

    Respond with just the domain word. Nothing else.
    """
        response = llm.invoke(prompt)
        domain = response.content.strip().lower()
        if domain not in ('astronomy', 'geospatial', 'agro', 'solar', 'cross'):
            domain = 'astronomy'
        print(f"[Router] LLM classified: {domain}")

    # ── Detect temporal intent ─────────────────────────────────
    if any(kw in query_lower for kw in _FUTURE_KEYWORDS):
        temporal_intent = 'recent'
    elif any(kw in query_lower for kw in ('was', 'were', 'did', 'happened', 'occurred', 'last year', 'in 2024', 'in 2023')):
        temporal_intent = 'historical'
    else:
        temporal_intent = 'any'

    state['query_domain']    = domain
    state['temporal_intent'] = temporal_intent
    state['evidence_chain'].append({
        'step':            'router',
        'domain':          domain,
        'temporal_intent': temporal_intent,
    })
    print(f"[Router] Domain: {domain} | Temporal intent: {temporal_intent}")

    return state

# ── Node 2: Astronomy Agent ───────────────────────────────────
def astronomy_node(state: AstroGeoState) -> AstroGeoState:
    if state['query_domain'] not in ('astronomy', 'cross'):
        print("[Astronomy] Skipped — not relevant domain")
        return state

    query_lower = state['query'].lower()
    needs_asteroids = any(kw in query_lower for kw in ('asteroid', 'anomaly', 'kinetic', 'orbit', 'near-earth'))
    needs_launch = any(kw in query_lower for kw in ('launch', 'shap', 'isro', 'failure', 'success', 'probability', 'feature'))

    # Default to fetching asteroids if no specific keywords
    if not needs_asteroids and not needs_launch:
        needs_asteroids = True

    conn = None
    try:
        p = _get_pg_pool()
        conn = p.getconn()

        if needs_asteroids:
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

        if needs_launch:
            df_launch = pd.read_sql("""
                SELECT mission, vehicle, date, launch_site, outcome, success
                FROM public.launch_history
                ORDER BY date DESC
                LIMIT 5
            """, conn)
            
            # Simulated model SHAP values (aligned with the main.py model)
            shap_drivers = [
                {"feature": "Precipitation", "impact": "High (increases risk if > 2mm)"},
                {"feature": "Monsoon Season", "impact": "Moderate (increases risk in June-Sept)"},
                {"feature": "Cloud Cover", "impact": "Moderate (increases risk if > 50%)"},
                {"feature": "Wind Speed", "impact": "Low (increases risk if > 10m/s)"}
            ]

            state['launch_context'] = {
                'recent_launches': df_launch.to_dict('records'),
                'model_shap_drivers': shap_drivers,
                'model_version': 'astrogeo-launch-v2.0'
            }
            
            state['evidence_chain'].append({
                'step':   'astronomy_agent',
                'source': 'PostgreSQL launch_history + SHAP model base',
                'rows':   len(df_launch),
            })
            print(f"[Astronomy] Loaded {len(df_launch)} recent launches + SHAP drivers")

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
# Regions mentioned in queries → Neo4j macro-region names
_REGION_MENTIONS = {
    'karnataka':        'South India',
    'bangalore':        'South India',
    'tamil nadu':       'South India',
    'kerala':           'South India',
    'andhra':           'South India',
    'telangana':        'South India',
    'south india':      'South India',
    'maharashtra':      'West India',
    'gujarat':          'West India',
    'rajasthan':        'West India',
    'west india':       'West India',
    'punjab':           'North India',
    'haryana':          'North India',
    'uttar pradesh':    'North India',
    'delhi':            'North India',
    'north india':      'North India',
    'west bengal':      'East India',
    'odisha':           'East India',
    'east india':       'East India',
    'madhya pradesh':   'Central India',
    'chhattisgarh':     'Central India',
    'central india':    'Central India',
    'assam':            'Northeast India',
    'northeast':        'Northeast India',
}


def solar_node(state: AstroGeoState) -> AstroGeoState:
    """
    Queries Neo4j for solar events and their disruption risk
    to Indian agricultural zones. Runs for 'solar' and 'cross'
    domains. This is the cross-domain bridge:
    Space Weather → GPS Disruption → Smart Irrigation Failure
    → Crop Stress in already drought-vulnerable zones.
    """
    if state['query_domain'] not in ('solar', 'cross'):
        print("[Solar] Skipped — not solar/cross domain")
        return state

    # For 'cross' domain, only run solar if the query has solar-related keywords.
    # This prevents solar DB queries from firing on SHAP/asteroid/vegetation questions.
    if state['query_domain'] == 'cross':
        solar_keywords = {
            'solar', 'flare', 'geomagnetic', 'storm', 'kp', 'kp index',
            'space weather', 'gps', 'cme', 'aurora', 'magnetosphere',
            'donki', 'disruption', 'irrigation', 'space storm',
        }
        query_lower_check = state['query'].lower()
        if not any(kw in query_lower_check for kw in solar_keywords):
            print("[Solar] Skipped — cross domain but no solar keywords in query")
            return state

    # ── Detect if the query targets a specific region ──────────
    query_lower = state['query'].lower()
    target_macro_region = None
    for keyword, macro in _REGION_MENTIONS.items():
        if keyword in query_lower:
            target_macro_region = macro
            break
    print(f"[Solar] Region filter: {target_macro_region or 'all India'}")

    try:
        driver = get_neo4j_driver()
        db_name = os.getenv("NEO4J_DATABASE")

        from datetime import datetime, timedelta
        today_str      = datetime.now().strftime('%Y-%m-%d')
        cutoff_90d     = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        temporal       = state.get('temporal_intent', 'any')

        # When the user asks about upcoming/approaching storms:
        #   → Query the most RECENT events (last 90 days), sorted date DESC
        #   → This surfaces April 2026 events instead of the eternal May 2024 Kp9 winner
        # When historical or any:
        #   → Sort by risk DESC, date DESC (mixed)
        if temporal == 'recent':
            date_filter  = 'AND e.date >= $cutoff'
            order_clause = 'ORDER BY e.date DESC, e.disruption_risk DESC'
            cutoff_param = cutoff_90d
        else:
            date_filter  = ''
            order_clause = 'ORDER BY e.disruption_risk DESC, e.date DESC'
            cutoff_param = '2000-01-01'

        with driver.session(database=db_name) as session:

            # 1. High-impact solar events — temporally filtered
            if target_macro_region:
                recent_events = session.run(f"""
                    MATCH (e:SolarEvent)-[:DISRUPTS]->(r:Region {{name: $region}})
                    WHERE e.disruption_risk > 0.3 {date_filter}
                    RETURN e.date         AS date,
                           e.event_type   AS type,
                           e.intensity    AS intensity,
                           e.kp_index     AS kp_index,
                           e.disruption_risk AS risk,
                           e.description  AS description
                    {order_clause}
                    LIMIT 5
                """, {'region': target_macro_region, 'cutoff': cutoff_param}).data()
            else:
                recent_events = session.run(f"""
                    MATCH (e:SolarEvent)
                    WHERE e.disruption_risk > 0.3 {date_filter}
                    RETURN e.date         AS date,
                           e.event_type   AS type,
                           e.intensity    AS intensity,
                           e.kp_index     AS kp_index,
                           e.disruption_risk AS risk,
                           e.description  AS description
                    {order_clause}
                    LIMIT 5
                """, {'cutoff': cutoff_param}).data()

            # 2. Cross-domain: solar event → region (1-2 hop PART_OF) → zone → land change
            if target_macro_region:
                cross_domain = session.run(f"""
                    MATCH (e:SolarEvent)-[:DISRUPTS]->(mr:Region {{name: $region}})
                    MATCH (z:Zone)-[:PART_OF*1..2]->(mr)
                    MATCH (z)-[:SHOWS_CHANGE]->(c:LandCoverChange)
                    WHERE e.disruption_risk > 0.4 {date_filter}
                    OPTIONAL MATCH (z)-[:PART_OF]->(sr:Region)
                    WHERE sr.level = 'state'
                    RETURN DISTINCT
                           e.date           AS event_date,
                           e.intensity      AS intensity,
                           e.disruption_risk AS risk,
                           mr.name          AS macro_region,
                           coalesce(sr.name, mr.name) AS state,
                           z.name           AS zone,
                           c.type           AS land_change,
                           c.confidence     AS confidence
                    {order_clause}, c.confidence DESC
                    LIMIT 8
                """, {'region': target_macro_region, 'cutoff': cutoff_param}).data()
            else:
                cross_domain = session.run(f"""
                    MATCH (e:SolarEvent)-[:DISRUPTS]->(mr:Region)
                    MATCH (z:Zone)-[:PART_OF*1..2]->(mr)
                    MATCH (z)-[:SHOWS_CHANGE]->(c:LandCoverChange)
                    WHERE e.disruption_risk > 0.4 {date_filter}
                    OPTIONAL MATCH (z)-[:PART_OF]->(sr:Region)
                    WHERE sr.level = 'state'
                    RETURN DISTINCT
                           e.date           AS event_date,
                           e.intensity      AS intensity,
                           e.disruption_risk AS risk,
                           mr.name          AS macro_region,
                           coalesce(sr.name, mr.name) AS state,
                           z.name           AS zone,
                           c.type           AS land_change,
                           c.confidence     AS confidence
                    {order_clause}, c.confidence DESC
                    LIMIT 8
                """, {'cutoff': cutoff_param}).data()

            # 3. Storm frequency per region (always all-time)
            region_exposure = session.run("""
                MATCH (e:SolarEvent)-[d:DISRUPTS]->(r:Region)
                WHERE e.disruption_risk > 0.3
                RETURN r.name            AS region,
                       count(e)          AS storm_count,
                       avg(d.risk_score) AS avg_risk
                ORDER BY storm_count DESC
            """).data()

        state['solar_context'] = {
            'region_filter':           target_macro_region or 'All India',
            'temporal_intent':         temporal,
            'data_window':             'last 90 days' if temporal == 'recent' else 'all-time highest risk',
            'data_as_of':              today_str,
            'recent_high_risk_events': recent_events,
            'cross_domain_impacts':    cross_domain,
            'most_exposed_regions':    region_exposure[:3],
            'total_events_found':      len(recent_events),
        }
        state['evidence_chain'].append({
            'step':            'solar_agent',
            'source':          'Neo4j — SolarEvent nodes (NASA DONKI)',
            'region_filter':   target_macro_region or 'All India',
            'temporal_intent': temporal,
            'data_window':     'last 90 days' if temporal == 'recent' else 'all-time highest risk',
            'events_found':    len(recent_events),
            'cross_impacts':   len(cross_domain),
        })
        print(f"[Solar] temporal={temporal} | {len(recent_events)} events | "
              f"{len(cross_domain)} cross-domain impacts")

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
                    MATCH (e:SolarEvent)-[:DISRUPTS]->(mr:Region)
                          <-[:PART_OF]-(sr:Region)<-[:PART_OF]-(z:Zone)
                    WHERE e.disruption_risk > 0.4
                    RETURN e.date        AS event_date,
                           e.intensity   AS solar_intensity,
                           mr.name       AS macro_region,
                           sr.name       AS state,
                           z.name        AS vulnerable_zone,
                           e.description AS impact_description
                    ORDER BY e.disruption_risk DESC
                    LIMIT 5
                """).data()

            elif state['query_domain'] == 'cross':
                # Full multi-hop: asteroids → country → macro → state → zone → change
                results = session.run("""
                    MATCH (a:Asteroid)-[:APPROACH_RISK]->(c:Country {name: 'India'})
                          <-[:PART_OF]-(mr:Region)<-[:PART_OF]-(sr:Region)
                          <-[:PART_OF]-(z:Zone)-[:SHOWS_CHANGE]->(lcc:LandCoverChange)
                    RETURN a.designation   AS asteroid,
                           a.risk_category  AS risk,
                           sr.name          AS state,
                           z.name           AS zone,
                           lcc.type         AS change_type,
                           lcc.confidence   AS confidence
                    ORDER BY lcc.confidence DESC
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

    if state.get('launch_context'):
        context_parts.append(f"Launch data & SHAP features: {state['launch_context']}")

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
        # Check if the user asked about future/approaching events
        solar_ctx = state.get('solar_context') or {}
        temporal  = solar_ctx.get('temporal_intent') or state.get('temporal_intent', 'any')
        data_window = solar_ctx.get('data_window', 'all-time highest risk')
        data_as_of  = solar_ctx.get('data_as_of', 'unknown')

        if temporal == 'recent':
            temporal_instruction = f"""
IMPORTANT — TEMPORAL FRAMING:
The user is asking about UPCOMING or APPROACHING solar events.
AstroGeo does NOT have a real-time prediction API. Instead, these results
represent the MOST RECENT events in our database (window: {data_window},
as of: {data_as_of}) from NASA DONKI live-seeded data.

Frame your answer correctly:
- Say "Based on the most recent solar activity in our database (as of {data_as_of})…"
- Do NOT say an old event is "approaching" — cite its actual date.
- If the most recent events are moderate (M-class), say that; do not escalate to 'X-class danger'.
- End with: "AstroGeo's dataset is updated from NASA DONKI. For real-time space weather
  forecasts, also check NOAA Space Weather Prediction Center (swpc.noaa.gov)."
"""
        elif temporal == 'historical':
            temporal_instruction = """
IMPORTANT — TEMPORAL FRAMING:
The user is asking about PAST events. Cite exact dates clearly.
"""
        else:
            temporal_instruction = ""

        system_prompt = f"""You are AstroGeo, a scientific AI assistant specialising in
astronomy, space weather, and Earth observation over India.
{temporal_instruction}
RULES:
1. Answer EXACTLY what the user asked. Do not drift into unrelated topics.
2. Use ONLY the evidence provided below. Do not invent facts.
3. Only say data is unavailable if the user's question CANNOT be answered at all
   from the evidence — and even then, keep it to one short sentence.
   Do NOT add "AstroGeo does not have X" as a trailing disclaimer on an answer
   that already addressed the question.
4. Do NOT mention ISRO launches, SHAP values, or any other topic unless the
   user explicitly asked about it.

FORMATTING:
- Use numbered sections (1. 2. 3.) for multi-part answers.
- Use **bold** for key terms, values, and dates.
- Keep each section to 2-3 sentences.
- Cite specific numbers (dates, Kp index, intensity class, risk score) from the evidence.

DOMAIN GUIDANCE (apply only when relevant to the question):
- Solar/geomagnetic: Solar Event → GPS Degradation → Smart Irrigation → Crop Impact.
- Asteroids: cite risk category, anomaly score.
- Vegetation/agro: cite NDVI delta, zone name, drought score.
- Launch/SHAP: cite feature contributions and probability values if in evidence.
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
    initial_state = {
        "query":           query,
        "evidence_chain":  [],
        "simplify":        simplify,
        "temporal_intent": "",   # router_node will set 'recent' | 'historical' | 'any'
    }
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