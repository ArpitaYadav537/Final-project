-- Run in Supabase Dashboard > SQL Editor.
-- This is a quick demo schema. Keep the service-role key on the backend only.
create extension if not exists pgcrypto;

create table if not exists public.career_profiles (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  education text not null,
  interests text not null,
  skills text not null,
  experience_level text not null default 'Student / Fresher',
  target_role text,
  created_at timestamptz not null default now()
);

create table if not exists public.career_reports (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.career_profiles(id) on delete set null,
  report_type text not null,
  input_summary jsonb not null default '{}'::jsonb,
  ai_result text not null,
  model_name text,
  created_at timestamptz not null default now()
);

create index if not exists career_reports_created_at_idx on public.career_reports(created_at desc);
create index if not exists career_reports_profile_id_idx on public.career_reports(profile_id);

-- Demo app writes through the backend only. Do not expose a service-role key in browser code.
-- For a production multi-user app, add Supabase Auth + user_id columns and per-user RLS policies.
