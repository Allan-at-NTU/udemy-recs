
import json
from typing import Dict, List, Tuple
from recsys.pipeline import top3_with_reasons

LEVEL_ORDER = ["none","basic","intermediate","advanced"]

def load_role_skills(goal_role: str) -> Dict:
    with open("roles.json","r") as f:
        roles = json.load(f)
    key = goal_role.strip().lower()
    for r in roles.keys():
        if r in key or key in r:
            return roles[r]
    return {"required":{}}

def compute_gaps(current: Dict[str,str], target: Dict[str,str]) -> List[Tuple[str,str,str]]:
    out = []
    for skill, tlevel in target.items():
        clevel = current.get(skill, "none")
        if LEVEL_ORDER.index(clevel) < LEVEL_ORDER.index(tlevel):
            out.append((skill, clevel, tlevel))
    return out

def level_hint(clevel: str, tlevel: str):
    i1, i2 = LEVEL_ORDER.index(clevel), LEVEL_ORDER.index(tlevel)
    if i1 <= 0 and i2 <= 1: return "beginner"
    if i2 - i1 >= 2: return "from basics to advanced"
    if i2 <= 2: return "intermediate"
    return "advanced"

def build_plan_from_skill_queries(skill_queries: List[Dict], budget=None, hours=None):
    plan = []
    for sq in skill_queries:
        q = sq["query"]
        if budget and "budget_usd" not in sq: q += f" under ${int(budget)}"
        if hours and "max_hours" not in sq:   q += f" under {int(hours)} hours"
        df = top3_with_reasons(q)
        plan.append({"skill": sq.get("skill",""), "level": sq.get("level"), "query": q, "courses": df.to_dict(orient="records")})
    return plan

def build_plan_from_profile(profile: Dict, goal_role: str, budget=None, hours=None):
    roles = load_role_skills(goal_role)
    req = roles.get("required", {})
    gaps = compute_gaps(profile.get("current_skills",{}), req)
    queries = []
    for skill, clevel, tlevel in gaps:
        lh = level_hint(clevel, tlevel)
        q = f"{lh} {skill} course"
        if budget: q += f" under ${int(budget)}"
        if hours:  q += f" under {int(hours)} hours"
        queries.append({"skill": skill, "level": tlevel, "query": q})
    return build_plan_from_skill_queries(queries, budget, hours)
