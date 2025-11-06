# 🎓 LearnAI — Udemy Course Finder & Career Path Assistant

**LearnAI** is an intelligent course recommender built on top of Udemy’s catalog.  
It helps users **discover their ideal learning path** based on their skills, goals, or even their resume.

🚀 **Live Demo:** _coming soon on Render_  
🧠 Powered by: **Groq (Llama-3)** for reasoning & **Sentence-Transformers** for course similarity.

---

## 🌟 Features

### 🔍 1. Home Page
- Clean landing page styled with Udemy-inspired colors.  
- Choose between two paths:
  - **Career Plan (CV)** → upload a resume and target role.
  - **Role Discovery** → describe what you study, like, and dislike.

### 🧾 2. Career Plan (CV Upload)
- Upload your **CV** (PDF or text).  
- The AI extracts your current skills, finds skill gaps for your chosen career goal,  
  and recommends Udemy courses that fill those gaps.
- Results show:
  - Skill roadmap (step-by-step)
  - Top course per skill with a friendly “Why this course” explanation
  - Ratings (0-5★), price, duration, and subject

### 💡 3. Role Discovery
- Not sure what to study next? Tell LearnAI about your interests.  
- The AI suggests 3–5 potential **career roles** (e.g., “UI/UX Designer”, “Data Analyst”)  
  and builds a learning roadmap for each, using Udemy courses for the required skills.

### 🎨 4. Modern UI
- Udemy-style purple gradient theme  
- Clean cards and buttons  
- Responsive design built entirely in **Streamlit**

---

## ⚙️ Tech Stack

| Area | Technology |
|------|-------------|
| Frontend | Streamlit |
| Backend Logic | Python |
| Recommender Engine | FAISS + Sentence-Transformers |
| LLMs | Groq (Llama-3) for reasoning & skill extraction |
| Data | Udemy Course Dataset (`data/*.parquet`, `courses.faiss`) |
| Hosting | Render (Python Web Service) |

---

## 🧰 Setup (Local)

### 1️⃣ Clone the repo
```bash
git clone https://github.com/Allan-at-NTU/udemy-recs.git
cd udemy-recs
```

### 2️⃣ Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
```
### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```
### 4️⃣ Set up your Groq API key
```bash
export GROQ_API_KEY=gsk_your_real_key_here
```
### 5️⃣ Build the embeddings (only once)
```bash
python -m recsys.data_prep
python -m recsys.build_index
```
### 6️⃣ Run the app
```bash
streamlit run app/streamlit_app.py
```
