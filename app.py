import io
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Load the .env file located beside this app.py file.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

APP_NAME = os.getenv("APP_NAME", "AI Career Assistant").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
    description="AI-powered career guidance, skill-gap analysis and preparation platform",
)

STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.is_dir():
    raise RuntimeError(f"Static folder was not found: {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_db = None
_ai = None


def get_db():
    """Create and cache the Supabase client."""
    global _db

    if _db is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise HTTPException(
                status_code=503,
                detail="Database is not configured. Set SUPABASE_URL and SUPABASE_KEY in .env.",
            )

        try:
            from supabase import create_client

            _db = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Could not initialize Supabase client: {str(exc)[:200]}",
            ) from exc

    return _db


def get_ai():
    """Create and cache the Gemini client."""
    global _ai

    if _ai is None:
        if not GEMINI_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="AI is not configured. Set GEMINI_API_KEY in .env.",
            )

        try:
            from google import genai

            _ai = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Could not initialize AI client: {str(exc)[:200]}",
            ) from exc

    return _ai


def generate_ai(prompt: str) -> str:
    """Generate a non-empty response using Gemini."""
    try:
        response = get_ai().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        result = (response.text or "").strip()
        if not result:
            raise ValueError("The AI returned an empty response.")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI request failed. Check GEMINI_MODEL, GEMINI_API_KEY, and quota. "
                f"Details: {str(exc)[:200]}"
            ),
        ) from exc


def save_report(
    report_type: str,
    summary: dict,
    result: str,
    profile_id: Optional[int] = None,
):
    """Save a generated report in career_reports."""
    db = get_db()

    row = {
        "report_type": report_type,
        "report_data": result,
        "input_summary": summary,
        "ai_result": result,
        "model_name": GEMINI_MODEL,
    }

    if profile_id is not None:
        row["profile_id"] = profile_id

    try:
        db.table("career_reports").insert(row).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI result was generated, but the report could not be saved. "
                "Check the career_reports table columns and its RLS policies. "
                f"Database details: {str(exc)[:200]}"
            ),
        ) from exc


def comma_separated_items(value: str) -> list[str]:
    """Convert a comma-separated input string into a list for PostgreSQL text[] columns."""
    return [item.strip() for item in value.split(",") if item.strip()]


class CareerRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    education: str = Field(min_length=2, max_length=200)
    interests: str = Field(min_length=2, max_length=1000)
    skills: str = Field(min_length=1, max_length=1500)
    experience_level: str = Field(default="Student / Fresher", max_length=100)
    target_role: str = Field(default="", max_length=150)
    weekly_hours: int = Field(default=6, ge=1, le=60)


class TextRequest(BaseModel):
    text: str = Field(min_length=10, max_length=12000)
    target_role: str = Field(default="", max_length=150)


class InterviewRequest(BaseModel):
    target_role: str = Field(min_length=2, max_length=150)
    experience_level: str = Field(default="Student / Fresher", max_length=100)
    difficulty: str = Field(default="Mixed", max_length=50)
    count: int = Field(default=8, ge=3, le=15)


@app.get("/", response_class=HTMLResponse)
def home():
    index_file = STATIC_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(
            status_code=500,
            detail="static/index.html was not found.",
        )
    return index_file.read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "ai_configured": bool(GEMINI_API_KEY),
        "database_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "model": GEMINI_MODEL,
    }


@app.post("/api/career-plan")
def career_plan(req: CareerRequest):
    db = get_db()

    skills_list = comma_separated_items(req.skills)
    interests_list = comma_separated_items(req.interests)
    target_role = req.target_role.strip()

    # skills and interests are PostgreSQL text[] columns in your database.
    profile = {
        "full_name": req.full_name.strip(),
        "education": req.education.strip(),
        "interests": interests_list,
        "skills": skills_list,
        "experience_level": req.experience_level.strip(),
        "target_role": target_role or None,
        # Your table also has a career_goal column.
        "career_goal": target_role or "Career exploration",
    }

    weekly_hours = req.weekly_hours

    prompt = f"""You are PathPilot, a friendly, professional AI career coach.
Help the user make practical career decisions using their profile.

Write naturally, as if responding directly to the user in a modern AI chatbot.
Be encouraging, specific, realistic, and concise. Personalize the advice.

USER PROFILE:
{json.dumps({**profile, "weekly_hours": weekly_hours}, ensure_ascii=False)}

RESPONSE FORMAT:
Use clean Markdown. Avoid escaped Markdown, literal backslashes before
headings, empty bullet points, and unnecessary horizontal rules.
Use short paragraphs, meaningful headings, numbered steps, and tables
only when they improve readability.

Structure the response as follows:

# Your Personalized Career Roadmap

Begin with a short, personalized introduction.

## 1. Career Matches
Recommend 3 suitable career paths, explaining fit, existing and missing
skills, entry-level job titles, and confidence with a brief rationale.

## 2. Skill Gap Analysis
Use a concise table with Skill, Current Level (if known), Target Level,
Priority, and Recommended Action. Do not assume unreported skills.

## 3. Your 12-Week Learning Plan
Include the topic, a practical task, and a tangible deliverable each week.
Respect the user's available study hours.

## 4. Portfolio Projects
Suggest 3 progressively challenging projects, including purpose, features,
technologies, and measurable completion criteria.

## 5. Learning Resources
Prioritize reputable free official resources. Include valid Markdown links
only when confident they are correct. Do not invent courses or credentials.

## 6. Your First 30 Days
Give a realistic week-by-week action plan.

## 7. Risks and Next Steps
Explain relevant skill gaps and practical constraints. Do not guarantee
employment or claim this is a definitive aptitude diagnosis.

Keep the response useful and readable, not unnecessarily long.
Return only the final Markdown response."""

    result = generate_ai(prompt)

    try:
        inserted = db.table("career_profiles").insert(profile).execute()
        profile_id = inserted.data[0]["id"] if inserted.data else None
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI response generated, but the profile could not be saved. "
                "Check the Supabase key and career_profiles RLS policy. "
                f"Database details: {str(exc)[:200]}"
            ),
        ) from exc

    save_report(
        "career_plan",
        {**profile, "weekly_hours": weekly_hours},
        result,
        profile_id,
    )

    return {
        "profile_id": profile_id,
        "result": result,
        "saved": True,
    }


@app.post("/api/resume-review")
def resume_review(req: TextRequest):
    prompt = f"""Act as a careful resume coach for an early-career applicant.
Target role: {req.target_role or 'not specified'}.
Do not invent qualifications or personal details.

Return Markdown sections:
- Overall Assessment
- Strong Points
- Issues to Fix (prioritized)
- ATS/Keyword Alignment (explain that ATS behavior varies)
- 3 Before-and-After Bullet Rewrites using only facts already present
- Missing Evidence to Add if truthful
- Suggested Skills to Learn
- 5 Tailoring Actions

Never promise an ATS score or interview.

Resume text:
---
{req.text}
---"""

    result = generate_ai(prompt)
    save_report("resume_review", {"target_role": req.target_role}, result)
    return {"result": result, "saved": True}


@app.post("/api/interview-prep")
def interview_prep(req: InterviewRequest):
    prompt = f"""Create an interview preparation pack for a {req.experience_level}
applying for {req.target_role}. Difficulty: {req.difficulty}.
Provide {req.count} questions, balanced between technical/role knowledge,
behavioral, and scenario questions. For each include: what the interviewer
tests, a concise answer framework, and one follow-up question. Use STAR for
behavioral questions. Clearly label sample answers as examples to personalize
honestly; do not encourage fabricated experience. End with a 1-day practice
schedule and 5 questions the candidate can ask the interviewer. Use Markdown."""

    result = generate_ai(prompt)
    save_report("interview_prep", req.model_dump(), result)
    return {"result": result, "saved": True}


@app.post("/api/course-roadmap")
def course_roadmap(req: TextRequest):
    prompt = f"""Based on this career goal and current context, suggest a
structured learning roadmap.

Goal/context: {req.text}
Target role: {req.target_role or 'infer from context'}

Return: prerequisite check, ordered topics, hands-on practice, 3 portfolio
milestones, suggested reputable free official learning resources (names and
URLs only when confident; tell the user to verify current availability), and
weekly checkpoints. Distinguish foundational knowledge from job-ready
proficiency; do not claim course completion guarantees a job. Use Markdown."""

    result = generate_ai(prompt)
    save_report(
        "learning_roadmap",
        {"context": req.text, "target_role": req.target_role},
        result,
    )
    return {"result": result, "saved": True}


@app.post("/api/resume-upload")
async def resume_upload(file: UploadFile = File(...), target_role: str = ""):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF resume.",
        )

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="PDF must be 5 MB or smaller.",
        )

    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        resume_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read PDF: {str(exc)[:180]}",
        ) from exc

    if len(resume_text.strip()) < 30:
        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text found. If this is a scanned PDF, paste the "
                "resume text into the Resume Review tab instead."
            ),
        )

    req = TextRequest(text=resume_text[:12000], target_role=target_role)
    return resume_review(req)


@app.get("/api/history")
def history(limit: int = 10):
    if not 1 <= limit <= 50:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 50.",
        )

    try:
        result = (
            get_db()
            .table("career_reports")
            .select(
                "id,report_type,input_summary,ai_result,model_name,created_at"
            )
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"items": result.data or []}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load saved reports: {str(exc)[:200]}",
        ) from exc
