import streamlit as st
from groq import Groq
from streamlit_mic_recorder import mic_recorder
import io

# --- CONFIGURATION ---
APTITUDE_ROUNDS = 10
TECHNICAL_ROUNDS = 5
HR_ROUNDS = 5

st.set_page_config(page_title="TalentScout: Interview Mentor", page_icon="👨‍🏫", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Candidate Profile")
    target_role = st.text_input("Target Role", "Data Scientist")
    tech_stack = st.text_input("Tech Stack", "Python, SQL, Machine Learning")
    
    st.divider()
    st.write("🎤 **Voice Input**")
    audio_input = mic_recorder(start_prompt="🎙️ Answer", stop_prompt="🛑 Stop", key='recorder')

# --- SESSION STATE ---
if "stage" not in st.session_state:
    st.session_state.stage = "SETUP"  # Stages: SETUP, APTITUDE, FEEDBACK, TECHNICAL, HR, FINAL_REPORT
if "messages" not in st.session_state:
    st.session_state.messages = []
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "current_round_log" not in st.session_state:
    st.session_state.current_round_log = [] # Stores Q&A for the current round only (for feedback)
if "feedback_report" not in st.session_state:
    st.session_state.feedback_report = ""

# --- CLIENT SETUP ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Missing API Key in .streamlit/secrets.toml")
    st.stop()

# --- FUNCTIONS ---
def get_ai_response(messages):
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
        )
        return stream.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def generate_feedback(round_name, chat_log):
    """Generates the Report Card between rounds"""
    prompt = f"""
    You are an Expert Interview Coach. The user just finished the {round_name} round.
    Here is the transcript of their answers:
    {chat_log}

    TASK:
    1. Give a Rating out of 10 based on accuracy and clarity.
    2. List 3 specific concepts they struggled with (if any).
    3. Critique their Communication Style (Were they confident? Too vague?).
    4. Provide actionable advice on what to study next.
    
    FORMAT:
    ### 📊 Score: X/10
    ### 🛑 Weak Areas: ...
    ### 🗣️ Communication: ...
    ### 💡 Next Steps: ...
    """
    return get_ai_response([{"role": "user", "content": prompt}])

def transcribe_audio(audio_data):
    if not audio_data: return None
    try:
        audio_file = io.BytesIO(audio_data['bytes'])
        audio_file.name = "audio.wav"
        return client.audio.transcriptions.create(
            file=(audio_file.name, audio_file.read()),
            model="whisper-large-v3-turbo", response_format="text", language="en"
        )
    except: return None

# --- MAIN UI ---
st.title(f"👨‍🏫 Interview & Mentor Bot")
st.caption(f"Target: {target_role} | Stage: {st.session_state.stage}")

# 1. SETUP SCREEN
if st.session_state.stage == "SETUP":
    st.info(f"The interview will cover: Aptitude ({APTITUDE_ROUNDS} Qs), Technical ({TECHNICAL_ROUNDS} Qs), and HR ({HR_ROUNDS} Qs).")
    if st.button("Start Round 1: Aptitude"):
        st.session_state.stage = "APTITUDE"
        st.session_state.question_count = 1
        st.session_state.current_round_log = []
        
        intro = "Welcome. I am your interviewer. We will start with 10 Aptitude questions covering Logic, Math, and Verbal reasoning. Here is Q1:"
        st.session_state.messages.append({"role": "assistant", "content": intro})
        st.rerun()

# 2. FEEDBACK SCREEN (Between Rounds)
elif st.session_state.stage == "FEEDBACK":
    st.markdown("## 📝 Round Performance Report")
    st.success("Round Complete! Here is your analysis:")
    
    # Show the generated report
    st.markdown(st.session_state.feedback_report)
    
    st.write("---")
    col1, col2 = st.columns(2)
    
    # Logic to decide next button
    next_stage = ""
    next_btn_text = ""
    
    if "Aptitude" in st.session_state.feedback_report: # If we just finished Aptitude
        next_stage = "TECHNICAL"
        next_btn_text = "Start Round 2: Technical"
    elif "Technical" in st.session_state.feedback_report: # If we just finished Technical
        next_stage = "HR"
        next_btn_text = "Start Round 3: HR"
    else:
        next_stage = "FINISHED"
        next_btn_text = "Finish Interview"

    if next_stage != "FINISHED":
        if st.button(next_btn_text):
            st.session_state.stage = next_stage
            st.session_state.question_count = 1
            st.session_state.current_round_log = [] # Reset log for new round
            
            # Seed the first question for the new round
            first_q_prompt = f"Start the {next_stage} round. Ask the first question immediately."
            seed_msg = [{"role": "system", "content": f"You are interviewing for {next_stage}. {tech_stack}. Ask Q1."}]
            q1 = get_ai_response(seed_msg)
            
            st.session_state.messages.append({"role": "assistant", "content": q1})
            st.rerun()
    else:
        if st.button("Restart Simulator"):
            st.session_state.clear()
            st.rerun()

# 3. INTERVIEW SCREEN (Chat Logic)
else:
    # Display History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Handle Input
    voice_text = None
    if audio_input:
        if "last_audio_id" not in st.session_state: st.session_state.last_audio_id = None
        if st.session_state.last_audio_id != audio_input['id']:
            st.session_state.last_audio_id = audio_input['id']
            voice_text = transcribe_audio(audio_input)
            
    user_input = st.chat_input("Type answer...")
    final_input = user_input if user_input else voice_text

    if final_input:
        # Display User Input
        with st.chat_message("user"):
            st.write(final_input)
        st.session_state.messages.append({"role": "user", "content": final_input})
        
        # Log for feedback
        st.session_state.current_round_log.append(f"User: {final_input}")

        # --- LOGIC CONTROL ---
        current_limit = APTITUDE_ROUNDS if st.session_state.stage == "APTITUDE" else \
                        TECHNICAL_ROUNDS if st.session_state.stage == "TECHNICAL" else HR_ROUNDS
        
        # CHECK IF ROUND IS OVER
        if st.session_state.question_count >= current_limit:
            with st.spinner("Analyzing your performance..."):
                # Generate Report Card
                report = generate_feedback(st.session_state.stage, st.session_state.current_round_log)
                st.session_state.feedback_report = report
                st.session_state.stage = "FEEDBACK"
                st.rerun()
        
        else:
            # ASK NEXT QUESTION
            st.session_state.question_count += 1
            
            # Dynamic Prompting based on Stage
            system_instruction = ""
            if st.session_state.stage == "APTITUDE":
                system_instruction = f"""
                Round: Aptitude (Question {st.session_state.question_count} of {APTITUDE_ROUNDS}).
                Goal: Test logic, math, and verbal skills.
                Rule: DO NOT repeat topics. If you asked math, ask logic next.
                Acknolwedge the previous answer briefly ("Correct" or "Incorrect, the answer was X"), then ask the next Q.
                """
            elif st.session_state.stage == "TECHNICAL":
                system_instruction = f"""
                Round: Technical (Question {st.session_state.question_count} of {TECHNICAL_ROUNDS}).
                Stack: {tech_stack}.
                Goal: Cover ALL concepts in the stack. 
                Rule: If user listed Python and SQL, ensure you ask about BOTH.
                Current Q: {st.session_state.question_count}.
                """
            elif st.session_state.stage == "HR":
                system_instruction = f"""
                Round: HR (Question {st.session_state.question_count} of {HR_ROUNDS}).
                Goal: Assess culture fit, salary expectations, and conflict resolution.
                """

            # Get AI Response
            messages = [{"role": "system", "content": system_instruction}] + st.session_state.messages
            ai_reply = get_ai_response(messages)
            
            with st.chat_message("assistant"):
                st.write(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            st.session_state.current_round_log.append(f"AI Question: {ai_reply}")