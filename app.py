import streamlit as st
from groq import Groq

# 1. Setup the Page
st.set_page_config(page_title="TalentScout Hiring Assistant", page_icon="🤖")
st.title("🤖 TalentScout Hiring Assistant")

# 2. Setup the AI Client (The Brain)
# This grabs the key you put in secrets.toml
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# 3. The "System Prompt" - This instructions the AI how to behave.
# This covers Assignment Requirements: Gathering Info  and Technical Questions.
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
        {"role": "system", "content": system_prompt}, # This instructs the AI secretly
        {"role": "assistant", "content": "Hello! I am the TalentScout Hiring Assistant. I'm here to learn a bit more about your background. To start, could you please provide your full name?"}
    ]

# 5. Display Chat History (excluding the secret system message)
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

# 6. Handle User Input
user_input = st.chat_input("Type your answer here...")

if user_input:
    # A. Display user message
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # B. Generate AI Response
    # We send the WHOLE history so the AI remembers your name and previous answers.
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Using Llama 3 as suggested in the assignment
            messages=st.session_state.messages,
            temperature=0.7, # Controls creativity (0.7 is balanced)
        )
        response = stream.choices[0].message.content
        st.write(response)
    
    # C. Save AI response to memory
    st.session_state.messages.append({"role": "assistant", "content": response})