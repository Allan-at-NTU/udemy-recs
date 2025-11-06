
import os, json, re
from typing import Dict, Any
from groq import Groq

LEVELS = ["none","basic","intermediate","advanced"]

def _get_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    return Groq(api_key=key)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    from pdfminer.high_level import extract_text
    import tempfile, os as _os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes); tmp.flush()
        path = tmp.name
    try:
        return extract_text(path) or ""
    finally:
        try: _os.remove(path)
        except Exception: pass

def parse_cv_and_goal(cv_text: str, goal: str) -> Dict[str, Any]:
    client = _get_client()
    system = "You extract concise skill summaries from resumes. Respond with JSON only."
    user = f"""
CV:
```
{cv_text[:15000]}
```
Target role: "{goal}"
Return JSON with keys:
- current_skills: object mapping canonical_skill -> level (none|basic|intermediate|advanced)
- summary: one sentence
"""
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.2, max_tokens=400
    )
    txt = r.choices[0].message.content.strip()
    m = re.search(r'\{[\s\S]*\}', txt)
    if not m: return {"current_skills":{}, "summary": ""}
    try:
        data = json.loads(m.group(0))
    except Exception:
        data = {"current_skills":{}, "summary": ""}
    cs = {}
    for k,v in (data.get("current_skills") or {}).items():
        k2 = re.sub(r'[^a-z0-9_+ ]','',str(k).lower()).strip().replace(" ","_")
        v2 = str(v).lower()
        if v2 not in LEVELS: v2 = "basic"
        cs[k2]=v2
    data["current_skills"]=cs
    return data
