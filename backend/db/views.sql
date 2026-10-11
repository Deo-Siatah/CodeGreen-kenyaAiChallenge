-- Scoring-safe farmer projection. gender is deliberately excluded.
-- This view is defense in depth; app_scoring must also lack farmers privileges.
CREATE OR REPLACE VIEW farmers_scoring_safe AS
SELECT id, full_name, national_id, phone, date_of_birth, location, village,
       sub_county, county, farming_type, years_farming, created_at, updated_at
FROM farmers;
