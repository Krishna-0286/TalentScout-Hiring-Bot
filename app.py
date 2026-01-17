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
# ⚠️ CHANGE THIS TO YOUR EMAIL TO SEE THE ADMIN BUTTON
ADMIN_EMAIL = "krishna@example.com" 

ROUND_ORDER = ["Aptitude", "Technical", "HR"]
ROUND_QUESTIONS = {"Aptitude": 10, "Technical": 5, "HR": 5}
PASSING_SCORE = 7
DB_FILE = "candidate_database.csv"
CHAT_HISTORY_FILE = "chat_logs.json"

# --- PAGE CONFIG ---
st.set_page_config(page_title="TalentScout AI", page_icon="🚀", layout="wide")

# --- FOUNDER BRANDING ---
st.markdown("""
<style>
    .founder { font-size: 14px; color: #888; text-align: center; margin-top: -50px; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "user_email" not in st.session_state: st.session_state.user_email = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "target_role" not in st.session_state: st.session_state.target_role = None
if "stage" not in st.session_state: st.session_state.stage = "LOGIN"
if "current_round_name" not in st.session_state: st.session_state.current_round_name = "Aptitude"
if "messages" not in st.session_state: st.session_state.messages = []
if "question_count" not in st.session_state: st.session_state.question_count = 0
if "round_log" not in st.session_state: st.session_state.round_log = [] 
if "feedback_data" not in st.session_state: st.session_state.feedback_data = None

# --- DATA HANDLING (EXCEL & SAVING) ---
def update_excel_db(name, email, role, status="Started", score="N/A"):
    """Creates or Updates the Excel Database"""
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=["Timestamp", "Name", "Email", "Target Role", "Status", "Last Score"])
        df.to_csv(DB_FILE, index=False)
    
    df = pd.read_csv(DB_FILE)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if email in df["Email"].values:
        df.loc[df["Email"] == email, ["Status", "Last Score", "Timestamp"]] = [status, score, timestamp]
    else:
        new_row = pd.DataFrame({
            "Timestamp": [timestamp], "Name": [name], "Email": [email],
            "Target Role": [role], "Status": [status], "Last Score": [score]
        })
        df = pd.concat([df, new_row], ignore_index=True)
    
    df.to_csv(DB_FILE, index=False)

def save_chat_history(email, messages):
    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f: json.dump({}, f)
    
    with open(CHAT_HISTORY_FILE, "r") as f: data = json.load(f)
    data[email] = messages
    with open(CHAT_HISTORY_FILE, "w") as f: json.dump(data, f)

def load_chat_history(email):
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            data = json.load(f)
            return data.get(email, [])
    return []

# --- CLIENT SETUP ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("🚨 API Key Missing! Check .streamlit/secrets.toml")
    st.stop()

# --- AI FUNCTIONS ---
def get_ai_response(messages):
    try:
        return client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7
        ).choices[0].message.content
    except Exception as e: return f"Error: {e}"

def transcribe_audio(audio_data):
    if not audio_data: return None
    try:
        audio_file = io.BytesIO(audio_data['bytes'])
        audio_file.name = "audio.wav"
        return client.audio.transcriptions.create(
            file=(audio_file.name, audio_file.read()),
            model="whisper-large-v3-turbo", 
            response_format="verbose_json", 
            language="en"
        ).text
    except: return None

def analyze_performance(round_name, logs):
    prompt = f"""
    Role: Senior Tech Recruiter. Round: {round_name}. Transcript: {logs}
    Task: Score 1-10. Decision PASS (>=7) or FAIL. Brief feedback.
    Format: SCORE: [Num] DECISION: [PASS/FAIL] FEEDBACK: [Text]
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
    st.title("🚀 TalentScout AI")
    st.markdown("<div class='founder'>Founded by <b>Krishna Kumar</b> (MNNIT Allahabad)</div>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/2919/2919600.png", width=150)
    with col2:
        st.subheader("Candidate Login")
        with st.form("login_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            role = st.text_input("Target Job Role", "Software Engineer")
            submitted = st.form_submit_button("Start Interview")
            
            if submitted and name and email:
                # 1. Update DB
                update_excel_db(name, email, role, status="Login", score="0")
                
                # 2. Update Session
                st.session_state.user_email = email
                st.session_state.user_name = name
                st.session_state.target_role = role
                
                # 3. Load History
                old_chat = load_chat_history(email)
                if old_chat:
                    st.session_state.messages = old_chat
                    st.session_state.stage = "INTERVIEW"
                    st.toast("Restored previous session!", icon="🔄")
                else:
                    st.session_state.stage = "SETUP"
                st.rerun()

    # --- ADMIN BUTTON (Only visible if email matches) ---
    if st.text_input("Admin Check (Type Email to test admin access)", key="admin_check") == ADMIN_EMAIL:
         if os.path.exists(DB_FILE):
            st.divider()
            st.subheader("👨‍💼 Admin Panel")
            with open(DB_FILE, "rb") as f:
                st.download_button("📥 Download Database (Excel)", f, file_name="candidate_database.csv")

# --- SIDEBAR (LOGGED IN) ---
elif st.session_state.stage != "LOGIN":
    with st.sidebar:
        st.info(f"👤 {st.session_state.user_name}")
        
        # Admin Download in Sidebar too
        if st.session_state.user_email == ADMIN_EMAIL:
            st.warning("🔓 Admin Mode")
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "rb") as f:
                    st.download_button("📥 Download Excel", f, file_name="candidate_database.csv", key='sidebar_dl')
        
        st.divider()
        audio_input = mic_recorder(start_prompt="🎤 Speak Answer", stop_prompt="🛑 Stop", key='recorder')
        
        st.divider()
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    # --- STAGE 2: SETUP ---
    if st.session_state.stage == "SETUP":
        st.title(f"Interview for {st.session_state.target_role}")
        st.info("You must score 7/10 to pass each round.")
        if st.button("Start Round 1: Aptitude", type="primary"):
            st.session_state.stage = "INTERVIEW"
            st.session_state.current_round_name = "Aptitude"
            st.session_state.question_count = 1
            st.session_state.round_log = []
            st.session_state.messages = [{"role": "assistant", "content": "Welcome to the Aptitude Round. Question 1:"}]
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
        st.write(f"**Feedback:** {data['feedback']}")
        
        # Save Score to Excel
        update_excel_db(
            st.session_state.user_name, st.session_state.user_email, st.session_state.target_role, 
            status=f"{st.session_state.current_round_name} {data['decision']}", score=str(data['score'])
        )

        if data['decision'] == "PASS":
            st.balloons()
            idx = ROUND_ORDER.index(st.session_state.current_round_name)
            if idx < len(ROUND_ORDER) - 1:
                next_r = ROUND_ORDER[idx + 1]
                if st.button(f"Start {next_r} Round"):
                    st.session_state.current_round_name = next_r
                    st.session_state.stage = "INTERVIEW"
                    st.session_state.question_count = 1
                    st.session_state.round_log = []
                    st.session_state.messages.append({"role": "assistant", "content": f"Starting {next_r}."})
                    save_chat_history(st.session_state.user_email, st.session_state.messages)
                    st.rerun()
            else:
                st.success("🏆 CONGRATULATIONS! YOU ARE HIRED.")
                update_excel_db(st.session_state.user_name, st.session_state.user_email, st.session_state.target_role, status="HIRED", score="10")
        else:
            st.error("❌ You did not pass.")
            if st.button("Retry Round"):
                st.session_state.stage = "INTERVIEW"
                st.session_state.question_count = 1
                st.session_state.round_log = []
                st.session_state.messages.append({"role": "assistant", "content": "Let's try again."})
                st.rerun()

    # --- STAGE 4: INTERVIEW ---
    elif st.session_state.stage == "INTERVIEW":
        q_limit = ROUND_QUESTIONS[st.session_state.current_round_name]
        st.progress(st.session_state.question_count / q_limit, text=f"Q {st.session_state.question_count}/{q_limit}")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.write(msg["content"])

        voice_text = None
        if audio_input:
            if st.session_state.get("last_audio_id") != audio_input['id']:
                st.session_state.last_audio_id = audio_input['id']
                voice_text = transcribe_audio(audio_input)

        user_input = st.chat_input("Type answer...")
        final_input = user_input if user_input else voice_text

        if final_input:
            with st.chat_message("user"): st.write(final_input)
            st.session_state.messages.append({"role": "user", "content": final_input})
            st.session_state.round_log.append(f"User: {final_input}")
            save_chat_history(st.session_state.user_email, st.session_state.messages)

            if st.session_state.question_count >= q_limit:
                with st.spinner("Analyzing performance..."):
                    res = analyze_performance(st.session_state.current_round_name, st.session_state.round_log)
                    st.session_state.feedback_data = res
                    st.session_state.stage = "FEEDBACK"
                    st.rerun()
            else:
                st.session_state.question_count += 1
                prompt = f"Role: Interviewer for {st.session_state.target_role}. Round: {st.session_state.current_round_name}. Ask Q {st.session_state.question_count}."
                ai_msg = get_ai_response([{"role": "system", "content": prompt}] + st.session_state.messages)
                with st.chat_message("assistant"): st.write(ai_msg)
                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                save_chat_history(st.session_state.user_email, st.session_state.messages)