import streamlit as st
from groq import Groq
from streamlit_mic_recorder import mic_recorder
import io

# 1. Setup the Page
st.set_page_config(page_title="TalentScout Hiring Assistant", page_icon="🤖")
st.title("🤖 TalentScout Hiring Assistant")

# 2. Setup the AI Client
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# 3. System Prompt
system_prompt = """
You are the "TalentScout" Hiring Assistant. Your goal is to screen candidates for technology placements.

YOUR PROCESS:
1. GREETING: Introduce yourself briefly and ask for the candidate's Full Name.
2. INFORMATION GATHERING: One by one, collect the following details. Do not ask for everything at once. Wait for the user to answer before asking the next:
   - Email Address
   - Phone Number
   - Years of Experience
   - Desired Position
   - Current Location
   - Tech Stack (Languages, Frameworks, Tools)
3. TECHNICAL SCREENING: Once the user provides their Tech Stack, generate 3-5 technical interview questions based specifically on their stack.
4. CLOSING: Once they answer the technical questions, thank them and say a recruiter will be in touch.

RULES:
- Be professional and polite.
- If the user asks something irrelevant, gently bring them back to the interview.
- Keep your questions short and clear.
"""

# 4. Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": "Hello! I am the TalentScout Hiring Assistant. I'm here to learn a bit more about your background. To start, could you please provide your full name?"}
    ]

# 5. Display Chat History
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- SIDEBAR: VOICE INPUT ---
# We move the microphone here so it never disappears!
with st.sidebar:
    st.title("🎤 Voice Input")
    st.write("Click to speak instead of typing:")
    
    # The Microphone Button
    audio_input = mic_recorder(
        start_prompt="Start Recording",
        stop_prompt="Stop Recording", 
        key='recorder'
    )

# Variable to store the final user text
final_user_input = None

# PROCESS AUDIO (If used)
if audio_input:
    if "last_audio_id" not in st.session_state:
        st.session_state.last_audio_id = None
    
    if st.session_state.last_audio_id != audio_input['id']:
        st.session_state.last_audio_id = audio_input['id']
        
        with st.spinner("Transcribing your voice..."):
            try:
                audio_file = io.BytesIO(audio_input['bytes'])
                audio_file.name = "audio.wav"
                
                # Using the NEW working model
                transcription = client.audio.transcriptions.create(
                    file=(audio_file.name, audio_file.read()),
                    model="whisper-large-v3-turbo", 
                    response_format="text",
                    language="en"
                )
                final_user_input = transcription
            except Exception as e:
                st.sidebar.error(f"Audio Error: {e}")

# --- TEXT INPUT ---
# This stays at the bottom of the main screen
text_input = st.chat_input("Type your answer here...")

# If user typed, use that instead
if text_input:
    final_user_input = text_input

# --- MAIN LOGIC ---
if final_user_input:
    # A. Display user message
    with st.chat_message("user"):
        st.write(final_user_input)
    st.session_state.messages.append({"role": "user", "content": final_user_input})

    # B. Generate AI Response
    with st.chat_message("assistant"):
        # Using the NEW working model
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=st.session_state.messages,
            temperature=0.7,
        )
        response = stream.choices[0].message.content
        st.write(response)
    
    # C. Save AI response
    st.session_state.messages.append({"role": "assistant", "content": response})