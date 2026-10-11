/*
Role setup for one environment (dev, staging, production, or a Neon branch).

This file is intentionally NOT run through Alembic. PostgreSQL roles are
cluster-level objects, not schema-managed objects, and re-running CREATE ROLE
from every migration would fail on the second run. Apply this file manually
once per environment, after db/views.sql has created farmers_scoring_safe.

The membership blocks use current_user as the login role that is running this
script. Run it as the application's login role for app_scoring, and as the
analytics login role for app_analytics when those login roles differ. Each
CREATE ROLE and each role-membership grant is idempotent.

app_scoring is deliberately denied the farmers base table and receives only
the scoring-safe view. Do not replace the explicit table grants below with
GRANT ... ON ALL TABLES: every new table requires a reviewed grant.
*/

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_scoring') THEN
        CREATE ROLE app_scoring NOLOGIN;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_analytics') THEN
        CREATE ROLE app_analytics NOLOGIN;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_auth_members m
        JOIN pg_roles r ON r.oid = m.roleid AND r.rolname = 'app_scoring'
        JOIN pg_roles u ON u.oid = m.member AND u.rolname = current_user
        WHERE m.set_option
    ) THEN
        EXECUTE format('GRANT app_scoring TO %I WITH SET TRUE', current_user);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_auth_members m
        JOIN pg_roles r ON r.oid = m.roleid AND r.rolname = 'app_analytics'
        JOIN pg_roles u ON u.oid = m.member AND u.rolname = current_user
        WHERE m.set_option
    ) THEN
        EXECUTE format('GRANT app_analytics TO %I WITH SET TRUE', current_user);
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO app_scoring;
GRANT USAGE ON SCHEMA public TO app_analytics;

-- The scoring role must never receive the base farmers table, including gender.
REVOKE ALL ON TABLE farmers FROM app_scoring;
GRANT SELECT ON TABLE farmers_scoring_safe TO app_scoring;

-- Explicit scoring read/write grants. Keep this list reviewed when models add a table.
GRANT SELECT, INSERT, UPDATE ON TABLE farms TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE institutions TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE trust_sources TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE social_groups TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE market_actors TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE farmer_trust_source_links TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE farmer_institution_links TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE farmer_social_group_links TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE farmer_market_actor_links TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE verification_sessions TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE verification_participants TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE testimonials TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE buyer_testimonials TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE discipline_proxies TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE in_kind_settlement_proofs TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE farm_activity_signals TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE score_profiles TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE score_components TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE loans TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE verifier_credibility TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE fraud_flags TO app_scoring;
GRANT SELECT, INSERT, UPDATE ON TABLE audit_logs TO app_scoring;

-- New tables are never silently exposed to scoring; add reviewed grants above.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON TABLES FROM app_scoring;

-- Analytics retains read access to every current table, including farmers.gender.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_analytics;
