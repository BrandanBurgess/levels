# LEVELS Data Model

## Principles

- UUID/ULID text IDs.
- UTC timestamps; local date derived by profile time zone.
- kg, cm, mL, seconds and metres as canonical units.
- database checks plus application validation.
- soft archive referenced exercises/splits.
- template changes never rewrite completed sessions.
- public schemas are explicit allow-lists.

## Entities

### Profile

- id
- display_name
- height_cm nullable
- body_weight_kg nullable
- preferred_units: imperial|metric
- timezone
- avatar_variant
- created_at, updated_at

### VisibilitySettings

Booleans:

- show_height
- show_body_weight
- show_water
- show_session_summaries
- show_set_details
- show_public_notes
- show_progress_charts
- show_personal_records
- show_readiness

### AppSettings

- active_split_id
- week_starts_on
- default_water_goal_ml
- water_quick_add_ml JSON array
- primary_muscle_weight
- secondary_muscle_weight
- default_target_rir
- default_load_increment_kg
- reduced_motion_override
- timestamps

### MuscleGroup

- id, slug, display_name
- body_region
- svg_region_ids JSON array
- highlightable

### Exercise

- id, slug, name, aliases
- variation_group
- movement_pattern
- equipment
- measurement_type: load_reps|bodyweight_reps|duration|distance|rounds
- compound, unilateral
- default rep range/rest
- progression_increment_kg
- automatic_progression_enabled
- metadata_json
- archived_at

### ExerciseMuscle

- exercise_id
- muscle_group_id
- role: primary|secondary|stabilizer
- contribution 0–1

### Split

- id, name, slug, description
- is_active, is_seeded
- display_order
- archived_at
- timestamps

### SplitDay

- id, split_id
- name, day_type, sequence
- recommended_weekday nullable
- description
- is_optional

### WorkoutTemplateItem

- id, split_day_id, exercise_id
- sequence
- item_type: activation|power|main|accessory|core|conditioning
- sets, rep_min, rep_max
- duration/distance
- rest, target_rir
- superset_group
- notes, optional

### TemplateAlternative

- template_item_id
- exercise_id
- sequence

### WorkoutSession

- id, split_day_id nullable
- session_date_local
- started_at, completed_at
- status: draft|in_progress|completed|cancelled
- title
- public_visibility: private|summary|full
- perceived_effort
- notes_private, notes_public
- deleted_at
- timestamps

### SessionExercise

Historical snapshot:

- id, workout_session_id, exercise_id
- source_template_item_id
- sequence
- display_name_snapshot
- variation_group_snapshot
- rep range and target RIR snapshots
- notes
- substitution_reason

### SetLog

- id, session_exercise_id, sequence
- set_type: warmup|working|backoff|drop|failure
- load_kg, reps, RIR
- duration_seconds, distance_meters, rounds
- bodyweight_assistance_kg
- form_quality 1–5
- pain_flag
- completed_at
- notes
- deleted_at
- idempotency_key

Measurement fields must match exercise measurement type.

### ReadinessLog

One per local date:

- energy, soreness, sleep quality 1–5
- pain_flag
- private note
- timestamps

### WaterLog

- occurred_at UTC
- local_date
- positive amount_ml
- source: quick_add|custom|correction
- note

Daily total is derived.

### PersonalRecord

- exercise_id
- record_type: max_load|reps_at_load|estimated_1rm|session_volume|duration|distance|rounds
- value_numeric, unit
- reps_context nullable
- set_log_id
- achieved_at
- is_current

### Achievement

- type
- exercise_id/set_log_id nullable
- title, message
- achieved_at
- public
- unique idempotency_key

### ProgressionSuggestion

May be computed on demand; persistence optional:

- local_date
- exercise_id
- suggestion_type
- delta
- confidence
- explanation JSON
- source session IDs
- accepted/dismissed timestamps

## Enums

Body region: chest, shoulders, back, arms, core, hips, legs, calves, full_body, cardiovascular.

Movement pattern: horizontal_push, vertical_push, horizontal_pull, vertical_pull, squat, lunge, hip_extension, knee_flexion, knee_extension, calf_raise, carry, jump, locomotion, anti_extension, anti_rotation, trunk_flexion, isolation, conditioning.

Equipment: bodyweight, barbell, dumbbell, cable, plate_loaded_machine, selectorized_machine, smith_machine, resistance_band, pullup_bar, bike, jump_rope, rower, sled, other.

## History

- Old SessionExercise snapshots never change.
- Archived exercises remain queryable.
- Deleted template items do not delete sets.
- Current muscle maps may be used for present UI; historical snapshots can be added later.

## Privacy

- private notes never enter public DTOs;
- private session public request returns 404;
- summary omits sets;
- profile metrics are independently controlled;
- public serializers use allow-lists.

## Required indexes

- workout_sessions(session_date_local, status)
- session_exercises(workout_session_id, sequence)
- set_logs(session_exercise_id, sequence)
- water_logs(local_date)
- personal_records(exercise_id, record_type, is_current)
- exercise_muscles(exercise_id)
- exercises(variation_group)
- split_days(split_id, sequence)
- workout_template_items(split_day_id, sequence)
