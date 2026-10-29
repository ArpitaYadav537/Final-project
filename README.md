# PathPilot — AI Career Assistant

A full-stack final-year project demo with a responsive web dashboard, FastAPI backend, Gemini AI integration, Supabase/PostgreSQL persistence, PDF resume extraction, career planning, interview preparation, learning roadmaps, and saved report history.

## Architecture

Browser (HTML/CSS/JS) → FastAPI REST API → Gemini API for generation → Supabase PostgreSQL for profiles and report persistence.

## Requirements

- Windows/macOS/Linux, Python 3.10+
- Google AI Studio API key
- Supabase project URL and backend-only key
- Internet access for AI/database calls

## Setup (Windows)

1. Extract the project ZIP to a folder such as `D:\AI-Career-Assistant`.
2. Open that folder in VS Code. Open Terminal > New Terminal.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt terminal and run `.venv\Scripts\activate.bat`.

4. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to a new file named `.env`. Fill in the real values:

   ```env
   GEMINI_API_KEY=your_real_key
   GEMINI_MODEL=gemini-2.5-flash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_backend_secret_key
   APP_NAME=AI Career Assistant
   ```

   Get the AI key from https://aistudio.google.com/apikey. Get the project URL/key from Supabase Dashboard > Project Settings / API. The key used by the backend must be kept secret; never put it in `static/app.js` or publish `.env`.

6. In Supabase Dashboard > SQL Editor, open `sql/schema.sql`, paste all SQL, and click Run. Confirm the `career_profiles` and `career_reports` tables appear.

7. Start the backend from the project folder:

   ```powershell
   uvicorn app:app --reload
   ```

8. Open http://127.0.0.1:8000. API documentation is at http://127.0.0.1:8000/docs.

## Demonstration flow

1. Open Overview and show the dashboard.
2. Complete Career Assessment and generate a plan.
3. Show career matches, skill gaps, portfolio projects and 12-week roadmap.
4. Open Saved Reports and reopen the stored result.
5. Run Resume Intelligence with sample resume text or a text-based PDF.
6. Generate interview preparation and a learning roadmap.
7. Show `/docs` and `/api/health` to explain the API and integrations.

## Database design

- `career_profiles`: educational background, interests, skills, experience and target role.
- `career_reports`: report type, JSON input summary, AI output, model name, timestamp, and optional profile foreign key.

## Security and limitations

- API secrets are server-side only and should not be committed to source control.
- This submission/demo schema does not implement multi-user authentication. Before production, add Supabase Auth, a `user_id` column, row-level security policies, rate limits, request logging, and data retention controls.
- Resume text is sent to the configured AI provider for review; only upload data you have permission to process. Avoid sensitive personal details where possible.
- AI career suggestions may be inaccurate. They are planning support, not guaranteed employment outcomes or professional aptitude diagnoses.
- Gemini model names and quotas can change. If the configured model is unavailable, choose a model currently enabled for your key in AI Studio and update `GEMINI_MODEL` in `.env`.

## Project objectives

1. Generate personalized career recommendations from a structured profile.
2. Identify skills to strengthen and create actionable learning milestones.
3. Provide role-specific resume feedback and interview practice material.
4. Persist profiles and AI reports in a relational database for later retrieval.
5. Expose a REST API that can be extended with authentication, course integrations and analytics.
