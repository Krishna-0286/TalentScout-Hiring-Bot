import streamlit as st
from groq import Groq
from streamlit_mic_recorder import mic_recorder
import io
import json
import re

# --- CONFIGURATION ---
# Define the strict order of the interview
ROUND_ORDER = ["Aptitude", "Technical", "HR"]
ROUND_QUESTIONS = {
    "Aptitude": 10,
    "Technical": 5,
    "HR": 5
}
PASSING_SCORE = 7  # Minimum score to move to next round

# --- PAGE CONFIG ---
st.set_page_config(page_title="TalentScout AI", page_icon="🚀", layout="wide")

# --- CUSTOM CSS FOR MODERN LOOK ---
st.markdown("""
<style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton button { border-radius: 20px; font-weight: bold; }
    h1 { color: #2E86C1; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "stage" not in st.session_state: st.session_state.stage = "SETUP" 
if "current_round_name" not in st.session_state: st.session_state.current_round_name = "Aptitude"
if "messages" not in st.session_state: st.session_state.messages = []
if "question_count" not in st.session_state: st.session_state.question_count = 0
if "round_log" not in st.session_state: st.session_state.round_log = [] 
if "feedback_data" not in st.session_state: st.session_state.feedback_data = None

# --- CLIENT SETUP ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("🚨 API Key Missing! Please check .streamlit/secrets.toml")
    st.stop()

# --- HELPER FUNCTIONS ---
def get_ai_response(messages):
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
        )
        return stream.choices[0].message.content
    except Exception as e: return f"Error: {e}"

def transcribe_audio(audio_data):
    if not audio_data: return None
    try:
        audio_file = io.BytesIO(audio_data['bytes'])
        audio_file.name = "audio.wav"
        transcription = client.audio.transcriptions.create(
            file=(audio_file.name, audio_file.read()),
            model="whisper-large-v3-turbo", 
            response_format="verbose_json", 
            language="en"
        )
        return transcription.text
    except: return None

def analyze_performance(round_name, logs):
    """
    Analyzes the round and returns a structured JSON-like response 
    so we can programmatically check if the user passed.
    """
    prompt = f"""
    You are a Senior Interviewer. The candidate just finished the {round_name} round.
    Transcript: {logs}

    TASK:
    1. Calculate a score from 1-10 based on accuracy and clarity.
    2. Decide if they PASS (Score >= 7) or FAIL.
    3. Provide brief feedback.

    OUTPUT FORMAT (Strictly follow this):
    SCORE: [Insert Number]
    DECISION: [PASS or FAIL]
    FEEDBACK: [Write 2-3 sentences of advice]
    """
    response = get_ai_response([{"role": "user", "content": prompt}])
    
    # Simple parsing logic to extract score and decision
    score_match = re.search(r"SCORE:\s*(\d+)", response)
    decision_match = re.search(r"DECISION:\s*(PASS|FAIL)", response)
    feedback_match = re.search(r"FEEDBACK:\s*(.*)", response, re.DOTALL)
    
    score = int(score_match.group(1)) if score_match else 0
    decision = decision_match.group(1) if decision_match else "FAIL"
    feedback = feedback_match.group(1) if feedback_match else "Could not generate feedback."
    
    return {"score": score, "decision": decision, "feedback": feedback}

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
    st.title("TalentScout AI")
    st.caption("Advanced Interview Simulator")
    
    with st.expander("👤 Candidate Profile", expanded=True):
        target_role = st.text_input("Target Role", "Full Stack Developer")
        tech_stack = st.text_input("Tech Stack", "React, Node.js, AWS")
    
    st.divider()
    st.markdown("### 🎙️ Voice Control")
    audio_input = mic_recorder(start_prompt="Start Speaking", stop_prompt="Stop Speaking", key='recorder')
    
    if st.button("🔄 Reset Interview"):
        st.session_state.clear()
        st.rerun()

# --- MAIN APP LOGIC ---

# 1. SETUP PAGE
if st.session_state.stage == "SETUP":
    st.title("🚀 Ready to Interview?")
    st.markdown(f"""
    Welcome to the **{target_role}** simulation.
    
    **The Gauntlet:**
    1. **🧠 Aptitude** ({ROUND_QUESTIONS['Aptitude']} Qs) - Logic & Reasoning
    2. **💻 Technical** ({ROUND_QUESTIONS['Technical']} Qs) - {tech_stack} Deep Dive
    3. **🤝 HR Round** ({ROUND_QUESTIONS['HR']} Qs) - Culture Fit
    
    *You must score **{PASSING_SCORE}/10** to unlock the next round.*
    """)
    
    if st.button("Start Round 1: Aptitude", type="primary"):
        st.session_state.stage = "INTERVIEW"
        st.session_state.current_round_name = "Aptitude"
        st.session_state.question_count = 1
        st.session_state.round_log = []
        st.session_state.messages = [{"role": "assistant", "content": "Welcome to the Aptitude Round. Let's begin with Question 1."}]
        st.rerun()

# 2. FEEDBACK & QUALIFICATION PAGE
elif st.session_state.stage == "FEEDBACK":
    data = st.session_state.feedback_data
    
    st.title("📊 Round Results")
    
    # Modern Metric Cards
    col1, col2, col3 = st.columns(3)
    col1.metric("Round", st.session_state.current_round_name)
    col2.metric("Score", f"{data['score']}/10")
    col3.metric("Status", data['decision'], delta="Qualified" if data['decision'] == "PASS" else "-Failed")
    
    st.info(f"**Feedback:** {data['feedback']}")
    
    # QUALIFICATION LOGIC
    current_index = ROUND_ORDER.index(st.session_state.current_round_name)
    
    if data['decision'] == "PASS":
        st.success("🎉 You have qualified for the next stage!")
        st.balloons()
        
        # Check if there is a next round
        if current_index < len(ROUND_ORDER) - 1:
            next_round = ROUND_ORDER[current_index + 1]
            if st.button(f"👉 Proceed to {next_round} Round", type="primary"):
                st.session_state.current_round_name = next_round
                st.session_state.stage = "INTERVIEW"
                st.session_state.question_count = 1
                st.session_state.round_log = []
                st.session_state.messages = [{"role": "assistant", "content": f"Welcome to the {next_round} Round. Let's begin."}]
                st.rerun()
        else:
            st.success("🏆 YOU ARE HIRED! You have completed all rounds successfully.")
    else:
        st.error("❌ You did not meet the passing criteria.")
        if st.button("🔄 Retry This Round"):
            st.session_state.stage = "INTERVIEW"
            st.session_state.question_count = 1
            st.session_state.round_log = []
            st.session_state.messages = [{"role": "assistant", "content": "Let's try this round again. Question 1:"}]
            st.rerun()

# 3. INTERVIEW CHAT PAGE
elif st.session_state.stage == "INTERVIEW":
    # Top Progress Bar
    q_limit = ROUND_QUESTIONS[st.session_state.current_round_name]
    progress = st.session_state.question_count / q_limit
    st.progress(progress, text=f"{st.session_state.current_round_name} Round: Question {st.session_state.question_count}/{q_limit}")

    # Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input Handling
    voice_text = None
    if audio_input:
        if "last_audio_id" not in st.session_state: st.session_state.last_audio_id = None
        if st.session_state.last_audio_id != audio_input['id']:
            st.session_state.last_audio_id = audio_input['id']
            voice_text = transcribe_audio(audio_input)

    user_input = st.chat_input("Type your answer...")
    final_input = user_input if user_input else voice_text

    if final_input:
        # Show User Message
        with st.chat_message("user"):
            st.write(final_input)
        st.session_state.messages.append({"role": "user", "content": final_input})
        st.session_state.round_log.append(f"User Answer: {final_input}")

        # Check if Round is Over
        if st.session_state.question_count >= q_limit:
            with st.spinner("🧠 AI is analyzing your performance..."):
                # Generate Score and Decision
                result = analyze_performance(st.session_state.current_round_name, st.session_state.round_log)
                st.session_state.feedback_data = result
                st.session_state.stage = "FEEDBACK"
                st.rerun()
        else:
            # Generate Next Question
            st.session_state.question_count += 1
            
            # Dynamic Prompt
            system_prompt = f"""
            Role: Interviewer for {target_role}.
            Round: {st.session_state.current_round_name}.
            Tech Stack: {tech_stack}.
            Task: Ask Question {st.session_state.question_count} of {q_limit}.
            Rule: Keep it short. Do not repeat topics.
            """
            
            # Get Response
            full_history = [{"role": "system", "content": system_prompt}] + st.session_state.messages
            ai_reply = get_ai_response(full_history)
            
            with st.chat_message("assistant"):
                st.write(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            st.session_state.round_log.append(f"AI Question: {ai_reply}")