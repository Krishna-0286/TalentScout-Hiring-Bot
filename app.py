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
ADMIN_EMAIL = "krishna@example.com" # <--- PUT YOUR EMAIL HERE
ROUND_QUESTIONS = {"Aptitude": 10, "Technical": 5, "HR": 5}
DB_FILE = "candidate_database.csv"
CHAT_HISTORY_FILE = "chat_logs.json"

# --- PAGE SETUP & NEW ICON ---
st.set_page_config(page_title="TalentScout Pro", page_icon="🎓", layout="wide")

# --- CUSTOM CSS FOR ATTRACTIVE UI ---
st.markdown("""
<style>
    /* Founder Badge Style */
    .founder-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 15px;
        color: white;
        text-align: center;
        font-family: 'Helvetica', sans-serif;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .founder-name { font-size: 20px; font-weight: bold; }
    .founder-college { font-size: 14px; opacity: 0.9; }
    
    /* Chat Message Style */
    .stChatMessage { border-radius: 12px; border: 1px solid #eee; }
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

# --- DATABASE FUNCTIONS ---
def update_excel_db(name, email, role, status="Started", score="N/A"):
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

# --- AI FUNCTIONS ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("🚨 API Key Missing!")
    st.stop()

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
    Role: Interview Coach. Round: {round_name}. Transcript: {logs}
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

# --- HEADER (BRANDING) ---
st.markdown("""
<div class='founder-badge'>
    <div class='founder-name'>TalentScout AI 🎓</div>
    <div class='founder-college'>Created by <b>Krishna Kumar</b> | MNNIT Allahabad</div>
</div>
""", unsafe_allow_html=True)

# --- STAGE 1: LOGIN ---
if st.session_state.stage == "LOGIN":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150) # Professional Icon
    with col2:
        st.subheader("Candidate Portal")
        with st.form("login_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            role = st.text_input("Target Role", "Software Engineer")
            submitted = st.form_submit_button("Enter Dashboard")
            
            if submitted and name and email:
                update_excel_db(name, email, role, status="Login", score="0")
                st.session_state.user_email = email
                st.session_state.user_name = name
                st.session_state.target_role = role
                
                old_chat = load_chat_history(email)
                if old_chat:
                    st.session_state.messages = old_chat
                    st.session_state.stage = "INTERVIEW"
                else:
                    st.session_state.stage = "SETUP"
                st.rerun()

    # Admin Check on Login Page
    if st.text_input("Admin Access", type="password", key="admin_check") == ADMIN_EMAIL:
         if os.path.exists(DB_FILE):
            st.success("Admin Recognized")
            with open(DB_FILE, "rb") as f:
                st.download_button("📥 Download Database", f, file_name="candidate_database.csv")

# --- MAIN APP (AFTER LOGIN) ---
elif st.session_state.stage != "LOGIN":
    
    # --- SIDEBAR: PRACTICE MODE CONTROLS ---
    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.user_name}**")
        st.caption(f"Role: {st.session_state.target_role}")
        st.divider()
        
        st.subheader("🎯 Practice Mode")
        st.info("Choose a specific round to practice:")
        
        # DROPDOWN TO CHOOSE ROUND
        selected_round = st.selectbox("Select Round", ["Aptitude", "Technical", "HR"])
        
        if st.button(f"Start {selected_round} Round"):
            st.session_state.current_round_name = selected_round
            st.session_state.stage = "INTERVIEW"
            st.session_state.question_count = 1
            st.session_state.round_log = []
            st.session_state.messages = [{"role": "assistant", "content": f"Starting {selected_round} Round. Let's begin Question 1."}]
            save_chat_history(st.session_state.user_email, st.session_state.messages)
            st.rerun()

        st.divider()
        # Admin Download in Sidebar
        if st.session_state.user_email == ADMIN_EMAIL:
            st.warning("🔓 Admin Mode")
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "rb") as f:
                    st.download_button("📥 Download Excel", f, file_name="candidate_database.csv", key='sidebar_dl')
        
        audio_input = mic_recorder(start_prompt="🎤 Speak", stop_prompt="🛑 Stop", key='recorder')
        if st.button("Logout"): st.session_state.clear(); st.rerun()

    # --- STAGE 2: SETUP ---
    if st.session_state.stage == "SETUP":
        st.info("👈 Use the sidebar to select a specific round and click Start!")
        st.image("https://cdn-icons-png.flaticon.com/512/7491/7491035.png", width=100)
        st.write("""
        **Available Modules:**
        * **Aptitude:** Logic & Math puzzles.
        * **Technical:** Code questions based on your role.
        * **HR:** Behavioral & Culture fit questions.
        """)

    # --- STAGE 3: FEEDBACK ---
    elif st.session_state.stage == "FEEDBACK":
        data = st.session_state.feedback_data
        st.title("📊 Performance Report")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Round", st.session_state.current_round_name)
        col2.metric("Score", f"{data['score']}/10")
        col3.metric("Result", data['decision'])
        
        st.write(f"**Coach's Feedback:** {data['feedback']}")
        
        # Save to Excel
        update_excel_db(
            st.session_state.user_name, st.session_state.user_email, st.session_state.target_role, 
            status=f"{st.session_state.current_round_name} {data['decision']}", score=str(data['score'])
        )

        if st.button("🔄 Practice Another Round"):
            st.session_state.stage = "SETUP"
            st.rerun()

    # --- STAGE 4: INTERVIEW ---
    elif st.session_state.stage == "INTERVIEW":
        q_limit = ROUND_QUESTIONS[st.session_state.current_round_name]
        st.progress(st.session_state.question_count / q_limit, text=f"{st.session_state.current_round_name}: Q {st.session_state.question_count}/{q_limit}")

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
                with st.spinner("Analyzing..."):
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