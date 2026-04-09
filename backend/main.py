from fastapi import FastAPI
from backend.routers import iss, asteroids
from backend.config import settings

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)

# Include routers
app.include_router(iss.router)
app.include_router(asteroids.router)

from pydantic import BaseModel
from backend.agents.astronomy.astronomy_agent import AstronomyAgent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

agent = AstronomyAgent()

class QueryRequest(BaseModel):
    query: str
    location: str = "Mumbai, India"

@app.get("/")
async def root():
    return {"message": "AstroGeo API", "version": settings.API_VERSION}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/query")
async def query_agent(request: QueryRequest):
    prompt = request.query
    location = request.location
    prompt_lower = prompt.lower()
    response_content = ""
    
    try:
        if "iss" in prompt_lower and ("where" in prompt_lower or "pass" in prompt_lower):
            pass_info = agent.get_next_iss_pass(location)
            if pass_info:
                response_content = f"The next ISS pass for {location} is at {pass_info.get('rise_time')} with a max elevation of {pass_info.get('max_elevation_deg')}°."
            else:
                response_content = f"I couldn't find any upcoming ISS passes for {location}."
                
        elif "asteroid" in prompt_lower or "approach" in prompt_lower:
            if any(x in prompt_lower for x in ["next", "upcoming", "closest", "soon"]):
                approaches = agent.asteroid_monitor.get_next_approaches_from_db(limit=1)
                if approaches:
                    app = approaches[0]
                    date_str = str(app['next_predicted_approach'])
                    response_content = f"The next predicted asteroid approach is **{app['asteroid_id']}** on {date_str}. Risk Score: {app['improved_risk_score']:.1f} ({app['adaptive_risk_category']})."
                else:
                    response_content = "I found no upcoming asteroid approaches in the database."
            elif any(x in prompt_lower for x in ["risk", "dangerous", "threat"]):
                risky = agent.get_high_risk_asteroids(min_risk_score=50)
                if risky:
                    top = risky[0]
                    response_content = f"The highest risk asteroid currently tracked is **{top['asteroid_id']}** with a score of {top['improved_risk_score']:.1f}."
                else:
                    response_content = "There are no asteroids currently flagged as high risk (>50)."
            else:
                ignore_words = ["asteroid", "risk", "score", "details", "about", "is", "flag", "what", "the"]
                words = prompt.split()
                potential_id_parts = [w for w in words if w.lower() not in ignore_words]
                search_candidate = " ".join(potential_id_parts).strip()
                
                found = False
                profile = None
                if len(search_candidate) > 2:
                    profile = agent.get_asteroid_profile(search_candidate)
                    if profile:
                        found = True
                    else:
                        matches = agent.search_asteroids(search_candidate)
                        if matches:
                            profile = agent.get_asteroid_profile(matches[0]['asteroid_id'])
                            found = True
                
                if found and profile:
                    response_content = f"**Asteroid {profile['asteroid_id']}**:\n- Risk Score: {profile.get('improved_risk_score', 'N/A')}\n- Category: {profile.get('adaptive_risk_category', 'N/A')}\n- Diameter: {profile.get('estimated_diameter_km', 'N/A')} km"
                else:
                    api_key = os.getenv("OPENAI_API_KEY")
                    llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
                    messages = [HumanMessage(content=f"You are an astronomy assistant. Context: User is in {location}. Question: {prompt}")]
                    ai_msg = llm.invoke(messages)
                    response_content = ai_msg.content
                    
        elif "weather" in prompt_lower or "rainfall" in prompt_lower:
            weather = agent.get_observation_conditions(location)
            if weather:
                response_content = f"Current conditions in {location}: {weather.get('weather_description')}, {weather.get('temperature_celsius')}°C, {weather.get('cloud_cover_percent')}% clouds."
            else:
                response_content = "Sorry, I couldn't fetch the weather data."
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
            messages = [HumanMessage(content=f"You are an astronomy assistant. Context: User is in {location}. Question: {prompt}")]
            ai_msg = llm.invoke(messages)
            response_content = ai_msg.content
            
        return {"response": response_content}
        
    except Exception as e:
        return {"error": str(e)}