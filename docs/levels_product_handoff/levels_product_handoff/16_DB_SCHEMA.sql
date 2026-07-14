PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
 id TEXT PRIMARY KEY,
 display_name TEXT NOT NULL,
 height_cm INTEGER CHECK (height_cm IS NULL OR height_cm BETWEEN 100 AND 250),
 body_weight_kg NUMERIC CHECK (body_weight_kg IS NULL OR body_weight_kg BETWEEN 20 AND 400),
 preferred_units TEXT NOT NULL CHECK (preferred_units IN ('imperial','metric')),
 timezone TEXT NOT NULL,
 avatar_variant TEXT NOT NULL DEFAULT 'brandan-original-v1',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visibility_settings (
 id TEXT PRIMARY KEY,
 profile_id TEXT NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
 show_height INTEGER NOT NULL DEFAULT 1 CHECK (show_height IN (0,1)),
 show_body_weight INTEGER NOT NULL DEFAULT 0 CHECK (show_body_weight IN (0,1)),
 show_water INTEGER NOT NULL DEFAULT 0 CHECK (show_water IN (0,1)),
 show_session_summaries INTEGER NOT NULL DEFAULT 1 CHECK (show_session_summaries IN (0,1)),
 show_set_details INTEGER NOT NULL DEFAULT 0 CHECK (show_set_details IN (0,1)),
 show_public_notes INTEGER NOT NULL DEFAULT 0 CHECK (show_public_notes IN (0,1)),
 show_progress_charts INTEGER NOT NULL DEFAULT 1 CHECK (show_progress_charts IN (0,1)),
 show_personal_records INTEGER NOT NULL DEFAULT 1 CHECK (show_personal_records IN (0,1)),
 show_readiness INTEGER NOT NULL DEFAULT 0 CHECK (show_readiness IN (0,1))
);

CREATE TABLE IF NOT EXISTS app_settings (
 id TEXT PRIMARY KEY,
 profile_id TEXT NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
 active_split_id TEXT,
 week_starts_on INTEGER NOT NULL DEFAULT 1 CHECK (week_starts_on BETWEEN 0 AND 6),
 default_water_goal_ml INTEGER NOT NULL DEFAULT 2800 CHECK (default_water_goal_ml BETWEEN 250 AND 10000),
 water_quick_add_ml TEXT NOT NULL DEFAULT '[250,500,750]',
 primary_muscle_weight NUMERIC NOT NULL DEFAULT 1.0,
 secondary_muscle_weight NUMERIC NOT NULL DEFAULT 0.45,
 default_target_rir NUMERIC NOT NULL DEFAULT 2.0 CHECK (default_target_rir BETWEEN 0 AND 10),
 default_load_increment_kg NUMERIC NOT NULL DEFAULT 1.133980925,
 reduced_motion_override INTEGER CHECK (reduced_motion_override IS NULL OR reduced_motion_override IN (0,1)),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS muscle_groups (
 id TEXT PRIMARY KEY,
 slug TEXT NOT NULL UNIQUE,
 display_name TEXT NOT NULL,
 body_region TEXT NOT NULL,
 svg_region_ids TEXT NOT NULL DEFAULT '[]',
 highlightable INTEGER NOT NULL DEFAULT 1 CHECK (highlightable IN (0,1))
);

CREATE TABLE IF NOT EXISTS exercises (
 id TEXT PRIMARY KEY,
 slug TEXT NOT NULL UNIQUE,
 name TEXT NOT NULL,
 aliases TEXT NOT NULL DEFAULT '[]',
 variation_group TEXT NOT NULL,
 movement_pattern TEXT NOT NULL,
 equipment TEXT NOT NULL,
 measurement_type TEXT NOT NULL CHECK (measurement_type IN ('load_reps','bodyweight_reps','duration','distance','rounds')),
 compound INTEGER NOT NULL CHECK (compound IN (0,1)),
 unilateral INTEGER NOT NULL CHECK (unilateral IN (0,1)),
 default_rep_min INTEGER,
 default_rep_max INTEGER,
 default_rest_seconds INTEGER,
 progression_increment_kg NUMERIC,
 automatic_progression_enabled INTEGER NOT NULL DEFAULT 1 CHECK (automatic_progression_enabled IN (0,1)),
 metadata_json TEXT NOT NULL DEFAULT '{}',
 archived_at TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 CHECK (default_rep_min IS NULL OR default_rep_min >= 0),
 CHECK (default_rep_max IS NULL OR default_rep_max >= default_rep_min)
);
CREATE INDEX IF NOT EXISTS idx_exercises_variation_group ON exercises(variation_group);

CREATE TABLE IF NOT EXISTS exercise_muscles (
 exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
 muscle_group_id TEXT NOT NULL REFERENCES muscle_groups(id) ON DELETE CASCADE,
 role TEXT NOT NULL CHECK (role IN ('primary','secondary','stabilizer')),
 contribution NUMERIC NOT NULL CHECK (contribution BETWEEN 0 AND 1),
 PRIMARY KEY (exercise_id,muscle_group_id,role)
);
CREATE INDEX IF NOT EXISTS idx_exercise_muscles_exercise ON exercise_muscles(exercise_id);

CREATE TABLE IF NOT EXISTS splits (
 id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 slug TEXT NOT NULL UNIQUE,
 description TEXT,
 is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
 is_seeded INTEGER NOT NULL DEFAULT 0 CHECK (is_seeded IN (0,1)),
 display_order INTEGER NOT NULL DEFAULT 0,
 archived_at TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS split_days (
 id TEXT PRIMARY KEY,
 split_id TEXT NOT NULL REFERENCES splits(id) ON DELETE CASCADE,
 name TEXT NOT NULL,
 day_type TEXT NOT NULL,
 sequence INTEGER NOT NULL,
 recommended_weekday INTEGER CHECK (recommended_weekday IS NULL OR recommended_weekday BETWEEN 0 AND 6),
 description TEXT,
 is_optional INTEGER NOT NULL DEFAULT 0 CHECK (is_optional IN (0,1)),
 UNIQUE(split_id,sequence)
);
CREATE INDEX IF NOT EXISTS idx_split_days_split_sequence ON split_days(split_id,sequence);

CREATE TABLE IF NOT EXISTS workout_template_items (
 id TEXT PRIMARY KEY,
 split_day_id TEXT NOT NULL REFERENCES split_days(id) ON DELETE CASCADE,
 exercise_id TEXT NOT NULL REFERENCES exercises(id),
 sequence INTEGER NOT NULL,
 item_type TEXT NOT NULL CHECK (item_type IN ('activation','power','main','accessory','core','conditioning')),
 sets INTEGER NOT NULL CHECK (sets BETWEEN 1 AND 20),
 rep_min INTEGER,
 rep_max INTEGER,
 duration_seconds INTEGER,
 distance_meters NUMERIC,
 rest_seconds INTEGER,
 target_rir NUMERIC CHECK (target_rir IS NULL OR target_rir BETWEEN 0 AND 10),
 superset_group TEXT,
 notes TEXT,
 optional INTEGER NOT NULL DEFAULT 0 CHECK (optional IN (0,1)),
 UNIQUE(split_day_id,sequence)
);
CREATE INDEX IF NOT EXISTS idx_template_items_day_sequence ON workout_template_items(split_day_id,sequence);

CREATE TABLE IF NOT EXISTS template_alternatives (
 template_item_id TEXT NOT NULL REFERENCES workout_template_items(id) ON DELETE CASCADE,
 exercise_id TEXT NOT NULL REFERENCES exercises(id),
 sequence INTEGER NOT NULL,
 PRIMARY KEY(template_item_id,exercise_id)
);

CREATE TABLE IF NOT EXISTS workout_sessions (
 id TEXT PRIMARY KEY,
 split_day_id TEXT REFERENCES split_days(id),
 session_date_local TEXT NOT NULL,
 started_at TEXT NOT NULL,
 completed_at TEXT,
 status TEXT NOT NULL CHECK (status IN ('draft','in_progress','completed','cancelled')),
 title TEXT NOT NULL,
 public_visibility TEXT NOT NULL DEFAULT 'private' CHECK (public_visibility IN ('private','summary','full')),
 perceived_effort INTEGER CHECK (perceived_effort IS NULL OR perceived_effort BETWEEN 1 AND 10),
 notes_private TEXT,
 notes_public TEXT,
 deleted_at TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_date_status ON workout_sessions(session_date_local,status);

CREATE TABLE IF NOT EXISTS session_exercises (
 id TEXT PRIMARY KEY,
 workout_session_id TEXT NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
 exercise_id TEXT NOT NULL REFERENCES exercises(id),
 source_template_item_id TEXT REFERENCES workout_template_items(id),
 sequence INTEGER NOT NULL,
 display_name_snapshot TEXT NOT NULL,
 variation_group_snapshot TEXT NOT NULL,
 rep_min_snapshot INTEGER,
 rep_max_snapshot INTEGER,
 target_rir_snapshot NUMERIC,
 notes TEXT,
 substitution_reason TEXT,
 UNIQUE(workout_session_id,sequence)
);
CREATE INDEX IF NOT EXISTS idx_session_exercises_session_sequence ON session_exercises(workout_session_id,sequence);

CREATE TABLE IF NOT EXISTS set_logs (
 id TEXT PRIMARY KEY,
 session_exercise_id TEXT NOT NULL REFERENCES session_exercises(id) ON DELETE CASCADE,
 sequence INTEGER NOT NULL,
 set_type TEXT NOT NULL CHECK (set_type IN ('warmup','working','backoff','drop','failure')),
 load_kg NUMERIC CHECK (load_kg IS NULL OR load_kg >= 0),
 reps INTEGER CHECK (reps IS NULL OR reps BETWEEN 0 AND 100),
 rir NUMERIC CHECK (rir IS NULL OR rir BETWEEN 0 AND 10),
 duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
 distance_meters NUMERIC CHECK (distance_meters IS NULL OR distance_meters >= 0),
 rounds INTEGER CHECK (rounds IS NULL OR rounds >= 0),
 bodyweight_assistance_kg NUMERIC,
 form_quality INTEGER CHECK (form_quality IS NULL OR form_quality BETWEEN 1 AND 5),
 pain_flag INTEGER NOT NULL DEFAULT 0 CHECK (pain_flag IN (0,1)),
 completed_at TEXT NOT NULL,
 notes TEXT,
 deleted_at TEXT,
 idempotency_key TEXT UNIQUE,
 UNIQUE(session_exercise_id,sequence)
);
CREATE INDEX IF NOT EXISTS idx_set_logs_session_exercise_sequence ON set_logs(session_exercise_id,sequence);

CREATE TABLE IF NOT EXISTS readiness_logs (
 id TEXT PRIMARY KEY,
 local_date TEXT NOT NULL UNIQUE,
 energy INTEGER NOT NULL CHECK (energy BETWEEN 1 AND 5),
 soreness INTEGER NOT NULL CHECK (soreness BETWEEN 1 AND 5),
 sleep_quality INTEGER NOT NULL CHECK (sleep_quality BETWEEN 1 AND 5),
 pain_flag INTEGER NOT NULL DEFAULT 0 CHECK (pain_flag IN (0,1)),
 note_private TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS water_logs (
 id TEXT PRIMARY KEY,
 occurred_at TEXT NOT NULL,
 local_date TEXT NOT NULL,
 amount_ml INTEGER NOT NULL CHECK (amount_ml BETWEEN 1 AND 5000),
 source TEXT NOT NULL CHECK (source IN ('quick_add','custom','correction')),
 note TEXT,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_water_logs_local_date ON water_logs(local_date);

CREATE TABLE IF NOT EXISTS personal_records (
 id TEXT PRIMARY KEY,
 exercise_id TEXT NOT NULL REFERENCES exercises(id),
 record_type TEXT NOT NULL CHECK (record_type IN ('max_load','reps_at_load','estimated_1rm','session_volume','duration','distance','rounds')),
 value_numeric NUMERIC NOT NULL,
 unit TEXT NOT NULL,
 reps_context INTEGER,
 set_log_id TEXT REFERENCES set_logs(id),
 achieved_at TEXT NOT NULL,
 is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1)),
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_personal_records_current ON personal_records(exercise_id,record_type,is_current);

CREATE TABLE IF NOT EXISTS achievements (
 id TEXT PRIMARY KEY,
 achievement_type TEXT NOT NULL,
 exercise_id TEXT REFERENCES exercises(id),
 set_log_id TEXT REFERENCES set_logs(id),
 title TEXT NOT NULL,
 message TEXT NOT NULL,
 achieved_at TEXT NOT NULL,
 public INTEGER NOT NULL DEFAULT 1 CHECK (public IN (0,1)),
 idempotency_key TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS progression_suggestions (
 id TEXT PRIMARY KEY,
 local_date TEXT NOT NULL,
 exercise_id TEXT NOT NULL REFERENCES exercises(id),
 suggestion_type TEXT NOT NULL,
 suggested_delta NUMERIC,
 confidence TEXT NOT NULL CHECK (confidence IN ('insufficient','low','medium','high')),
 explanation_json TEXT NOT NULL,
 source_session_ids_json TEXT NOT NULL,
 accepted_at TEXT,
 dismissed_at TEXT,
 created_at TEXT NOT NULL
);
