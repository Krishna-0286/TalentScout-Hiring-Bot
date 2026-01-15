# 🤖 TalentScout - Intelligent Hiring Assistant

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)
![AI Model](https://img.shields.io/badge/AI-Llama_3.3-purple)
![Audio](https://img.shields.io/badge/Audio-Whisper_Turbo-green)

## 📋 Project Overview
**TalentScout** is an AI-powered conversational agent designed to automate the initial screening process for recruitment agencies. Acting as a first-round interviewer, the bot gathers candidate details and dynamically generates technical interview questions based on the candidate's specific tech stack.

Unlike standard chatbots, TalentScout features **Multimodal capabilities**, allowing candidates to answer via text or voice (Speech-to-Text).

## ✨ Key Features
* **Context-Aware Conversation:** Maintains memory of the entire chat history to ensure logical flow using Streamlit Session State.
* **Dynamic Question Generation:** Automatically detects the candidate's tech stack (e.g., "Python", "React") and generates relevant technical questions using **Llama 3.3**.
* **🎙️ Voice Interaction:** Integrated **Whisper-Large-V3-Turbo** to transcribe candidate voice responses in real-time.
* **Role-Based Behavior:** Strictly adheres to a "Recruiter" persona via robust System Prompt engineering.

## 🛠️ Tech Stack
* **Frontend:** Streamlit (Python)
* **LLM Inference:** Groq API (Llama-3.3-70b-versatile)
* **Speech-to-Text:** Groq API (Whisper-large-v3-turbo)
* **Audio Handling:** `streamlit-mic-recorder`

## 🚀 Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/Krishna-0286/TalentScout-Hiring-Bot.git](https://github.com/Krishna-0286/TalentScout-Hiring-Bot.git)
   cd TalentScout-Hiring-Bot
