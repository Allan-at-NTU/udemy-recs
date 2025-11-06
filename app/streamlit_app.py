# app/streamlit_app.py
import os, json, re, requests
import streamlit as st
from groq import Groq

from cv_parser import extract_text_from_pdf, parse_cv_and_goal
from planner import build_plan_from_profile, build_plan_from_skill_queries

st.set_page_config(page_title="Course Finder", page_icon="🎓", layout="wide")

# ---------------------------- Global CSS ----------------------------
st.markdown("""
<style>
:root{
  --accent:#5624D0; /* Udemy purple */
  --text:#0F172A;
  --muted:#475569;
  --bg-grad-1:#F8FAFF;
  --bg-grad-2:#EEF1FF;
}
html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 50% -200px, var(--bg-grad-2), var(--bg-grad-1));
}
h1,h2,h3{ color:var(--text); }
.small{ color:var(--muted); font-size:0.95rem; }

.hero{ text-align:center; padding:32px 0 12px; }
.hero h1{ font-size:46px; font-weight:800; line-height:1.05; letter-spacing:-0.2px; }
.hero .accent{ color:var(--accent); }
.hero .sub{ color:var(--muted); max-width:820px; margin:10px auto 26px; }

.card{
  border:1px solid rgba(0,0,0,.06);
  border-radius:16px; padding:20px 20px 16px; background:#fff;
  box-shadow:0 6px 22px rgba(60,64,67,.08), 0 2px 6px rgba(60,64,67,.08);
}

.topbar{ display:flex; align-items:center; justify-content:space-between; padding:10px 8px 0; }
.topbar a{ text-decoration:none; }
.topbar .brand{ font-weight:800; color:var(--text); font-size:18px; }
.topbar .links{ display:flex; gap:10px; }

/* Udemy-like CTAs */
.ud-cta{ display:flex; gap:14px; margin-top:14px; justify-content:flex-start; }
.ud-btn{
  font-weight:700; font-size:16px; padding:12px 22px; border-radius:10px; cursor:pointer;
  transition:all .15s ease;
}
.ud-btn.primary{ background:var(--accent); color:#fff; border:0; }
.ud-btn.primary:hover{ filter:brightness(0.95); }
.ud-btn.ghost{ background:transparent; color:var(--accent); border:2px solid var(--accent); }
.ud-btn.ghost:hover{ background:rgba(86,36,208,0.06); }
</style>
""", unsafe_allow_html=True)

# ---------------------------- Top bar ----------------------------
st.markdown("""
<div class="topbar">
  <div class="brand">LearnAI</div>
  <div class="links">
    <a class="ud-btn ghost" href="https://www.udemy.com/" target="_blank">Learn about Udemy</a>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------- Hero ----------------------------
st.markdown("""
<div class="hero">
  <h1>Find Your Perfect <span class="accent">Udemy Course</span> with AI</h1>
  <div class="sub">Discover course recommendations tailored to your goals, budget, and skill level. Try role discovery or upload your CV for a custom plan.</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------- Groq helper ----------------------------
def _groq():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    return Groq(api_key=key)

def suggest_roles(studies: str, likes: str, dislikes: str):
    """Ask the LLM for 3–5 roles + core skills, JSON only."""
    client = _groq()
    prompt = f"""
User background:
- Studies: {studies}
- Likes: {likes}
- Dislikes: {dislikes}

Return JSON with exactly:
roles: [
  {{"title": "...", "why": "...", "skills": ["skill1","skill2","skill3"]}},
  ...
]
Keep 3–5 options, concise skills, no extra text.
"""
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.4,
        max_tokens=500
    )
    txt = r.choices[0].message.content or ""
    m = re.search(r'\{[\\s\\S]*\}', txt)
    try:
        data = json.loads(m.group(0)) if m else {"roles":[]}
    except Exception:
        data = {"roles":[]}
    return data.get("roles", [])[:5]

# ---------------------------- Tabs ----------------------------
tabs = st.tabs(["Home", "Career plan", "Role discovery"])

# ---------------------------- Tab 0: Home ----------------------------
with tabs[0]:
    st.subheader("Welcome")
    st.write("Pick how you want to start:")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            "<div class='card'><b>Career plan (CV)</b><br>"
            "<span class='small'>Upload your resume and target role. We extract your skills, find gaps, and build a step-by-step plan with Udemy courses.</span>"
            "<div class='ud-cta'>"
            "<button class='ud-btn primary' onclick=\"const t=window.parent.document.querySelectorAll('button[role=tab]'); if(t.length>1){t[1].click(); window.scrollTo({top:0,behavior:'smooth'});} \">Get started</button>"
            "</div></div>",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            "<div class='card'><b>Role discovery</b><br>"
            "<span class='small'>Not sure which role fits? Tell us your studies, likes, and dislikes. We’ll suggest roles and turn one into a plan with Udemy courses.</span>"
            "<div class='ud-cta'>"
            "<button class='ud-btn ghost' onclick=\"const t=window.parent.document.querySelectorAll('button[role=tab]'); if(t.length>2){t[2].click(); window.scrollTo({top:0,behavior:'smooth'});} \">Explore roles</button>"
            "</div></div>",
            unsafe_allow_html=True
        )

# ---------------------------- Tab 1: Career plan ----------------------------
with tabs[1]:
    st.subheader("Build my learning plan")
    cv_file = st.file_uploader("Upload your CV (PDF or TXT)", type=["pdf","txt"])
    goal = st.text_input("Target role", placeholder="e.g., Data Analyst")
    colA, colB = st.columns(2)
    with colA:
        budget = st.number_input("Max total budget (USD, optional)", min_value=0, value=0, step=10)
    with colB:
        hours = st.number_input("Max total hours (optional)", min_value=0, value=0, step=1)

    use_api = st.toggle("Use local API if available", value=False,
                        help="If on, posts to /api/plan_from_cv on your server.")

    if st.button("Create my plan", type="primary"):
        if not goal:
            st.warning("Please enter a target role.")
        elif not cv_file:
            st.warning("Please upload your CV.")
        else:
            if cv_file.type == "application/pdf":
                cv_text = extract_text_from_pdf(cv_file.read())
            else:
                cv_text = cv_file.read().decode("utf-8", errors="ignore")

            try:
                if use_api:
                    API_URL = os.getenv("RECS_API_URL","http://localhost:8000")
                    payload = {"goal_role": goal, "cv_text": cv_text}
                    if budget: payload["budget_usd"] = budget
                    if hours:  payload["max_hours"] = hours
                    r = requests.post(f"{API_URL}/api/plan_from_cv", json=payload, timeout=120)
                    r.raise_for_status()
                    data = r.json()
                    plan = data["plan"]
                    profile = data.get("profile",{})
                else:
                    profile = parse_cv_and_goal(cv_text, goal)
                    plan = build_plan_from_profile(
                        profile, goal,
                        budget if budget>0 else None,
                        hours if hours>0 else None
                    )

                st.success("Plan created")
                if profile.get("summary"):
                    st.caption(profile["summary"])

                for step in plan:
                    st.markdown(f"### {step['skill'].title()} — {step.get('level','')}")
                    for i, c in enumerate(step["courses"], start=1):
                        price = int(round(c["price"])) if c["price"]>0 else 0
                        stars = float(c.get("combined_rating", 0)) * 5.0  # 0–5 scale
                        meta = f'${price} • ~{int(round(c["content_duration"]))}h • {c["subject"]} • {stars:.1f}★ • {int(c["num_reviews"]):,} reviews'
                        st.markdown(
                            f"**{i}. [{c['course_title']}]({c['url']})**  \n"
                            f"Why: {c['why']}  \n*{meta}*"
                        )
            except Exception as e:
                st.error(str(e))

# ---------------------------- Tab 2: Role discovery ----------------------------
with tabs[2]:
    st.subheader("Not sure which role fits you? Start here.")
    c1, c2 = st.columns(2)
    with c1:
        studies = st.text_area("What are you studying / what’s your background?", height=100)
        likes = st.text_area("What do you enjoy doing?", height=100,
                             placeholder="e.g., data, design, helping people, problem solving")
    with c2:
        dislikes = st.text_area("What do you prefer to avoid?", height=100,
                                placeholder="e.g., heavy math proofs, long writing, sales")
        budget2 = st.number_input("Max total budget (USD, optional)", min_value=0, value=0, step=10, key="budget2")
        hours2 = st.number_input("Max total hours (optional)", min_value=0, value=0, step=1, key="hours2")

    if st.button("Suggest roles"):
        if not (studies or likes or dislikes):
            st.warning("Tell me at least one thing about you.")
        else:
            roles = suggest_roles(studies, likes, dislikes)
            if not roles:
                st.info("Couldn’t find good matches—try adding a bit more detail.")
            else:
                st.write("### Recommended roles")
                for idx, rinfo in enumerate(roles, start=1):
                    with st.container():
                        st.markdown(
                            f"<div class='card'><b>{idx}. {rinfo.get('title','Role')}</b><br>"
                            f"<span class='small'>{rinfo.get('why','')}</span><br>"
                            f"<span class='small'>Skills: {', '.join(rinfo.get('skills',[]))}</span></div>",
                            unsafe_allow_html=True
                        )

                        if st.button(f"Build plan for {rinfo.get('title','this role')}", key=f"plan_{idx}"):
                            # Build queries from suggested skills
                            sq = [
                                {"skill": s.lower().replace(' ','_'),
                                 "level": "basic",
                                 "query": f"beginner {s} course"}
                                for s in rinfo.get("skills", [])[:5]
                            ]

                            # Create the learning plan with your backend
                            plan = build_plan_from_skill_queries(
                                sq,
                                budget2 if budget2 > 0 else None,
                                hours2 if hours2 > 0 else None
                            )

                            st.success(f"Learning plan for **{rinfo.get('title','role')}**")
                            st.markdown("### Roadmap")

                            # 1) Roadmap steps
                            for step_i, step in enumerate(plan, start=1):
                                st.markdown(
                                    f"**Step {step_i}: {step['skill'].title()}**  "
                                    f"Target: {step.get('level','basic').title()} level"
                                )

                            st.divider()

                            # 2) Courses per step (Top pick + alternates)
                            for step in plan:
                                st.markdown(f"#### {step['skill'].title()} — {step.get('level','')}")
                                courses = step.get("courses", [])
                                if not courses:
                                    st.write("_No courses found for this skill._")
                                    continue

                                # Top pick
                                c0 = courses[0]
                                price0 = int(round(c0["price"])) if c0["price"] > 0 else 0
                                stars0 = float(c0.get("combined_rating", 0)) * 5.0
                                meta0 = (
                                    f"${price0} • ~{int(round(c0['content_duration']))}h • "
                                    f"{c0['subject']} • {stars0:.1f}★ • {int(c0['num_reviews']):,} reviews"
                                )
                                st.markdown(
                                    f"**Top pick: [{c0['course_title']}]({c0['url']})**  \n"
                                    f"Why: {c0['why']}  \n*{meta0}*"
                                )

                                # Alternates
                                if len(courses) > 1:
                                    with st.expander("See alternates"):
                                        for i, c in enumerate(courses[1:], start=2):
                                            price = int(round(c["price"])) if c["price"] > 0 else 0
                                            stars = float(c.get("combined_rating", 0)) * 5.0
                                            meta = (
                                                f"${price} • ~{int(round(c['content_duration']))}h • "
                                                f"{c['subject']} • {stars:.1f}★ • {int(c['num_reviews']):,} reviews"
                                            )
                                            st.markdown(
                                                f"**{i}. [{c['course_title']}]({c['url']})**  \n"
                                                f"Why: {c['why']}  \n*{meta}*"
                                            )
