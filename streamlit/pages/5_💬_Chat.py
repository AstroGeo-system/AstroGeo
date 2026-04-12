import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from utils import get_agent
import os
from dotenv import load_dotenv

# Logic to find .env in backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# pages -> streamlit_app -> root
project_root = os.path.dirname(os.path.dirname(current_dir)) 
dotenv_path = os.path.join(project_root, 'backend', '.env')

load_dotenv(dotenv_path)

st.set_page_config(page_title="Chat Assistant", page_icon="💬", layout="wide")

st.title("💬 Ask AstroGeo Agent")
location = st.session_state.get('location', 'Mumbai, India')
agent = get_agent()

# Initialize LLM
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o"

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY not found in .env")
    st.stop()

llm = ChatOpenAI(model=st.session_state["openai_model"], api_key=api_key)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask about satellites, astroids, or weather..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Agent Logic / Routing
    response_content = ""
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Simple keyword routing (could be replaced by Tool calling in LangChain)
                if "ISS" in prompt.upper() and ("where" in prompt.lower() or "pass" in prompt.lower()):
                    pass_info = agent.get_next_iss_pass(location)
                    if pass_info:
                        response_content = f"The next ISS pass for {location} is at {pass_info['rise_time']} with a max elevation of {pass_info['max_elevation_deg']}°."
                    else:
                        response_content = f"I couldn't find any upcoming ISS passes for {location}."
                        
                elif "asteroid" in prompt.lower() or "approach" in prompt.lower():
                    # Sub-routing for Asteroids
                    prompt_lower = prompt.lower()
                    
                    # Case A: "Next" or "Upcoming" or "Closest" approach
                    if any(x in prompt_lower for x in ["next", "upcoming", "closest", "soon"]):
                        approaches = agent.asteroid_monitor.get_next_approaches_from_db(limit=1)
                        if approaches:
                            app = approaches[0]
                            date_str = str(app['next_predicted_approach'])
                            response_content = f"The next predicted asteroid approach is **{app['asteroid_id']}** on {date_str}. Risk Score: {app['improved_risk_score']:.1f} ({app['adaptive_risk_category']})."
                        else:
                            response_content = "I found no upcoming asteroid approaches in the database."
                            
                    # Case B: High Risk / Dangerous
                    elif any(x in prompt_lower for x in ["risk", "dangerous", "threat"]):
                        risky = agent.get_high_risk_asteroids(min_risk_score=50)
                        if risky:
                            top = risky[0]
                            response_content = f"The highest risk asteroid currently tracked is **{top['asteroid_id']}** with a score of {top['improved_risk_score']:.1f}."
                        else:
                            response_content = "There are no asteroids currently flagged as high risk (>50)."
                            
                    # Case C: Specific Asteroid (Look for patterns or fallback to search)
                    # Heuristic: if there's a number or common format, try profile
                    # Simple attempt: scan words
                    else:
                        # Attempt to find asteroid ID in the prompt
                        # 1. Clean prompt to get potential search term
                        # Remove common words
                        ignore_words = ["asteroid", "risk", "score", "details", "about", "is", "flag", "what", "the"]
                        words = prompt.split()
                        potential_id_parts = [w for w in words if w.lower() not in ignore_words]
                        search_candidate = " ".join(potential_id_parts).strip()
                        print(f"DEBUG: Search Candidate: '{search_candidate}'")
                        
                        found = False
                        if len(search_candidate) > 2:
                             # Try precise search first if it looks like an ID
                             profile = agent.get_asteroid_profile(search_candidate)
                             if profile:
                                 print(f"DEBUG: Exact match found for '{search_candidate}'")
                                 found = True
                             else:
                                 # Try fuzzy search
                                 print(f"DEBUG: No exact match. Trying fuzzy search for '{search_candidate}'")
                                 matches = agent.search_asteroids(search_candidate)
                                 if matches:
                                     print(f"DEBUG: Fuzzy match found: {matches[0]['asteroid_id']}")
                                     # Get full profile of best match
                                     profile = agent.get_asteroid_profile(matches[0]['asteroid_id'])
                                     found = True
                        
                        if found and profile:
                             response_content = f"**Asteroid {profile['asteroid_id']}**:\n- Risk Score: {profile.get('improved_risk_score', 'N/A')}\n- Category: {profile.get('adaptive_risk_category', 'N/A')}\n- Diameter: {profile.get('estimated_diameter_km', 'N/A')} km"
                        else:
                             # Fallback to LLM
                             messages = [
                                HumanMessage(content=f"You are an astronomy assistant. Context: User is in {location}. Question: {prompt}")
                            ]
                             ai_msg = llm.invoke(messages)
                             response_content = ai_msg.content

                elif "weather" in prompt.lower():
                    weather = agent.get_observation_conditions(location)
                    if weather:
                        response_content = f"Current conditions in {location}: {weather['weather_description']}, {weather['temperature_celsius']}°C, {weather['cloud_cover_percent']}% clouds."
                    else:
                        response_content = "Sorry, I couldn't fetch the weather data."
                        
                else:
                    # Fallback to LLM
                    # Pass specific context if available?
                    messages = [
                        HumanMessage(content=f"You are an astronomy assistant. Context: User is in {location}. Question: {prompt}")
                    ]
                    ai_msg = llm.invoke(messages)
                    response_content = ai_msg.content

                st.markdown(response_content)
                
            except Exception as e:
                response_content = f"I encountered an error: {str(e)}"
                st.error(response_content)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_content})
