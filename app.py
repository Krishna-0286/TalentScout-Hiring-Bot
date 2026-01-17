import streamlit as st
from groq import Groq
from streamlit_mic_recorder import mic_recorder
import io
import json
import re
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
ROUND_ORDER = ["Aptitude", "Technical", "HR"]
ROUND_QUESTIONS = {"Aptitude": 10, "Technical": 5, "HR": 5}
PASSING_SCORE = 7
DB_FILE = "candidate_database.csv"
CHAT_HISTORY_FILE = "chat_logs.json"

# --- PAGE CONFIG ---
st.set_page_config(page_title="TalentScout AI", page_icon="🚀", layout="wide")

# --- FOUNDER BRANDING (Top of Website) ---
st.markdown("""
<style>
    .founder { font-size: 14px; color: #888; text-align: center; margin-top: -50px; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 TalentScout AI")
st.markdown("<div class='founder'>Founded by <b>Krishna Kumar</b> (MNNIT Allahabad)</div>", unsafe_allow_html=True)
st.write("---")

# --- SESSION STATE ---
# --- SESSION STATE ---
if "user_email" not in st.session_state: st.session_state.user_email = None
if "target_role" not in st.session_state: st.session_state.target_role = None  # <--- THIS WAS MISSING
if "stage" not in st.session_state: st.session_state.stage = "LOGIN"
if "current_round_name" not in st.session_state: st.session_state.current_round_name = "Aptitude"
if "messages" not in st.session_state: st.session_state.messages = []
if "question_count" not in st.session_state: st.session_state.question_count = 0
if "round_log" not in st.session_state: st.session_state.round_log = [] 
if "feedback_data" not in st.session_state: st.session_state.feedback_data = None

# --- DATA HANDLING FUNCTIONS (EXCEL & SAVING) ---
def save_user_to_excel(name, email, role):
    # Check if file exists, if not create with headers
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=["Timestamp", "Name", "Email", "Target Role"])
        df.to_csv(DB_FILE, index=False)
    
    # Load existing data
    df = pd.read_csv(DB_FILE)
    
    # Check if user already exists to avoid duplicates
    if email not in df["Email"].values:
        new_data = pd.DataFrame({
            "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "Name": [name],
            "Email": [email],
            "Target Role": [role]
        })
        # Append new user
        df = pd.concat([df, new_data], ignore_index=True)
        df.to_csv(DB_FILE, index=False)

def save_chat_history(email, messages):
    """Saves the chat list to a local JSON file key-ed by email"""
    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump({}, f)
    
    with open(CHAT_HISTORY_FILE, "r") as f:
        data = json.load(f)
    
    data[email] = messages # Overwrite/Update history for this email
    
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(data, f)

def load_chat_history(email):
    """Loads chat history if it exists"""
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            data = json.load(f)
            return data.get(email, [])
    return []

def clear_chat_history(email):
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            data = json.load(f)
        if email in data:
            del data[email]
            with open(CHAT_HISTORY_FILE, "w") as f:
                json.dump(data, f)

# --- CLIENT SETUP ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("🚨 API Key Missing! Check .streamlit/secrets.toml")
    st.stop()

# --- HELPER FUNCTIONS (AI) ---
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
    prompt = f"""
    You are a Senior Interviewer. Round: {round_name}.
    Transcript: {logs}
    TASK: Score 1-10. Decide PASS/FAIL (>=7 Pass). Brief feedback.
    OUTPUT FORMAT: SCORE: [Num] DECISION: [PASS/FAIL] FEEDBACK: [Text]
    """
    response = get_ai_response([{"role": "user", "content": prompt}])
    score_match = re.search(r"SCORE:\s*(\d+)", response)
    decision_match = re.search(r"DECISION:\s*(PASS|FAIL)", response)
    feedback_match = re.search(r"FEEDBACK:\s*(.*)", response, re.DOTALL)
    
    return {
        "score": int(score_match.group(1)) if score_match else 0,
        "decision": decision_match.group(1) if decision_match else "FAIL",
        "feedback": feedback_match.group(1) if feedback_match else "No feedback."
    }

# --- STAGE 1: LOGIN SCREEN ---
if st.session_state.stage == "LOGIN":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/2919/2919600.png", width=150)
    with col2:
        st.subheader("Login to Start Interview")
        with st.form("login_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            role = st.text_input("Target Job Role", "Software Engineer")
            submitted = st.form_submit_button("Start Interview")
            
            if submitted and name and email:
                # 1. Save User to CSV
                save_user_to_excel(name, email, role)
                
                # 2. Load Old Chat if exists
                old_chat = load_chat_history(email)
                
                # 3. Update Session
                st.session_state.user_email = email
                st.session_state.target_role = role
                
                if old_chat:
                    st.session_state.messages = old_chat
                    st.session_state.stage = "INTERVIEW"
                    st.toast("Welcome back! Chat history restored.", icon="🔄")
                else:
                    st.session_state.stage = "SETUP"
                
                st.rerun()

# --- SIDEBAR (ONLY SHOWS AFTER LOGIN) ---
elif st.session_state.stage != "LOGIN":
    with st.sidebar:
        st.info(f"👤 Logged in as: **{st.session_state.user_email}**")
        st.write(f"Target Role: {st.session_state.target_role}")
        
        st.divider()
        st.markdown("### 🎙️ Voice Control")
        audio_input = mic_recorder(start_prompt="Start Speaking", stop_prompt="Stop Speaking", key='recorder')
        
        st.divider()
        col_a, col_b = st.columns(2)
        if col_a.button("Logout"):
            st.session_state.clear()
            st.rerun()
        if col_b.button("🗑️ Clear Chat"):
            clear_chat_history(st.session_state.user_email)
            st.session_state.messages = []
            st.rerun()

    # --- STAGE 2: SETUP ---
    if st.session_state.stage == "SETUP":
        st.title(f"Ready for your {st.session_state.target_role} Interview?")
        st.write("Your progress will be saved automatically.")
        if st.button("Start Round 1: Aptitude", type="primary"):
            st.session_state.stage = "INTERVIEW"
            st.session_state.current_round_name = "Aptitude"
            st.session_state.question_count = 1
            st.session_state.round_log = []
            st.session_state.messages = [{"role": "assistant", "content": "Welcome to the Aptitude Round. Let's begin Question 1."}]
            save_chat_history(st.session_state.user_email, st.session_state.messages)
            st.rerun()

    # --- STAGE 3: FEEDBACK ---
    elif st.session_state.stage == "FEEDBACK":
        data = st.session_state.feedback_data
        st.title("📊 Round Results")
        col1, col2, col3 = st.columns(3)
        col1.metric("Round", st.session_state.current_round_name)
        col2.metric("Score", f"{data['score']}/10")
        col3.metric("Result", data['decision'])
        st.info(f"**Feedback:** {data['feedback']}")
        
        current_index = ROUND_ORDER.index(st.session_state.current_round_name)
        
        if data['decision'] == "PASS":
            st.balloons()
            if current_index < len(ROUND_ORDER) - 1:
                next_round = ROUND_ORDER[current_index + 1]
                if st.button(f"Proceed to {next_round}"):
                    st.session_state.current_round_name = next_round
                    st.session_state.stage = "INTERVIEW"
                    st.session_state.question_count = 1
                    st.session_state.round_log = []
                    msg = {"role": "assistant", "content": f"Welcome to {next_round}. Let's begin."}
                    st.session_state.messages.append(msg)
                    save_chat_history(st.session_state.user_email, st.session_state.messages)
                    st.rerun()
            else:
                st.success("🏆 HIRED!")
        else:
            st.error("❌ Failed.")
            if st.button("Retry Round"):
                st.session_state.stage = "INTERVIEW"
                st.session_state.question_count = 1
                st.session_state.round_log = []
                st.session_state.messages.append({"role": "assistant", "content": "Let's retry."})
                st.rerun()

    # --- STAGE 4: INTERVIEW ---
    elif st.session_state.stage == "INTERVIEW":
        q_limit = ROUND_QUESTIONS[st.session_state.current_round_name]
        st.progress(st.session_state.question_count / q_limit, text=f"{st.session_state.current_round_name}: Q {st.session_state.question_count}/{q_limit}")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        voice_text = None
        if audio_input:
            if "last_audio_id" not in st.session_state: st.session_state.last_audio_id = None
            if st.session_state.last_audio_id != audio_input['id']:
                st.session_state.last_audio_id = audio_input['id']
                voice_text = transcribe_audio(audio_input)

        user_input = st.chat_input("Type answer...")
        final_input = user_input if user_input else voice_text

        if final_input:
            with st.chat_message("user"):
                st.write(final_input)
            st.session_state.messages.append({"role": "user", "content": final_input})
            st.session_state.round_log.append(f"User Answer: {final_input}")
            
            # SAVE CHAT AUTOMATICALLY
            save_chat_history(st.session_state.user_email, st.session_state.messages)

            if st.session_state.question_count >= q_limit:
                with st.spinner("Analyzing..."):
                    result = analyze_performance(st.session_state.current_round_name, st.session_state.round_log)
                    st.session_state.feedback_data = result
                    st.session_state.stage = "FEEDBACK"
                    st.rerun()
            else:
                st.session_state.question_count += 1
                system_prompt = f"Role: Interviewer for {st.session_state.target_role}. Round: {st.session_state.current_round_name}. Ask Q {st.session_state.question_count} of {q_limit}."
                full_history = [{"role": "system", "content": system_prompt}] + st.session_state.messages
                ai_reply = get_ai_response(full_history)
                
                with st.chat_message("assistant"):
                    st.write(ai_reply)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                
                # SAVE CHAT AUTOMATICALLY
                save_chat_history(st.session_state.user_email, st.session_state.messages)