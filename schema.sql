-- ---------------------------------------------------------
-- 1. AGGRESSIVE CLEANUP
-- "CASCADE" forces Postgres to delete the table AND anything 
-- that depends on it (like keys or views) instantly.
-- ---------------------------------------------------------
DROP TABLE IF EXISTS public.staging_projects CASCADE;
DROP TABLE IF EXISTS public.staging_participants CASCADE;
DROP TABLE IF EXISTS public.cordis_projects CASCADE;
DROP TABLE IF EXISTS public.cordis_participants CASCADE;

-- ---------------------------------------------------------
-- 2. CREATE PRODUCTION TABLES (The Master Structure)
-- ---------------------------------------------------------
CREATE TABLE public.cordis_projects (
    rcn INTEGER PRIMARY KEY,
    acronym TEXT,                 -- TEXT = Unlimited length (Fixes your crash)
    title TEXT,
    start_date DATE,
    end_date DATE,
    total_cost NUMERIC(15, 2),
    ec_max_contribution NUMERIC(15, 2),
    objective TEXT,
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE TABLE public.cordis_participants (
    participant_id SERIAL PRIMARY KEY,
    project_rcn INTEGER REFERENCES public.cordis_projects(rcn) ON DELETE CASCADE,
    org_id TEXT,                  -- TEXT = Unlimited length
    legal_name TEXT,
    country_code VARCHAR(10),
    role TEXT,                    -- TEXT = Unlimited length
    ec_contribution NUMERIC(15, 2)
);

-- ---------------------------------------------------------
-- 3. CREATE STAGING TABLES (Clones)
-- We clone the structure of the Production tables.
-- Note: This copies column names and types (TEXT, etc.)
-- but intentionally DOES NOT copy Primary Keys or Constraints.
-- This makes staging "loose" and safe for bulk loading.
-- ---------------------------------------------------------
CREATE TABLE public.staging_projects AS 
SELECT * FROM public.cordis_projects WITH NO DATA;

CREATE TABLE public.staging_participants AS 
SELECT * FROM public.cordis_participants WITH NO DATA;

-- 4. COMMIT (Just to be sure)
COMMIT;