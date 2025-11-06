
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from recsys.pipeline import load_assets
from planner import build_plan_from_skill_queries
from cv_parser import parse_cv_and_goal

app = FastAPI(title="Udemy Recs API", version="1.0.0")
load_assets()

class SkillQuery(BaseModel):
    skill: str
    level: Optional[str] = None
    query: str
    budget_usd: Optional[float] = None
    max_hours: Optional[float] = None

class PlanRequest(BaseModel):
    goal_role: str
    constraints: Optional[Dict[str, Any]] = None
    skill_queries: List[SkillQuery]

class CVRequest(BaseModel):
    goal_role: str
    cv_text: str
    budget_usd: Optional[float] = None
    max_hours: Optional[float] = None

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/plan")
def plan(req: PlanRequest):
    budget = (req.constraints or {}).get("total_budget_usd")
    hours  = (req.constraints or {}).get("total_hours")
    plan = build_plan_from_skill_queries([sq.model_dump() for sq in req.skill_queries], budget, hours)
    total = sum(len(p["courses"]) for p in plan)
    return {"goal_role": req.goal_role, "plan": plan, "total_courses": total}

@app.post("/api/plan_from_cv")
def plan_from_cv(req: CVRequest):
    profile = parse_cv_and_goal(req.cv_text, req.goal_role)
    from planner import build_plan_from_profile
    plan = build_plan_from_profile(profile, req.goal_role, req.budget_usd, req.max_hours)
    total = sum(len(p["courses"]) for p in plan)
    return {"goal_role": req.goal_role, "profile": profile, "plan": plan, "total_courses": total}
