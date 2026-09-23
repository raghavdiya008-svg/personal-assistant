-- Project JARVIS v2 Authoritative Ledger Schema
-- Database Initialization Script

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Schemas
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS n8n;

-- 1. System Events Ledger (Append-Only Event Store)
CREATE TABLE IF NOT EXISTS public.system_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id VARCHAR(64) NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    trust_level VARCHAR(32) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_trace ON public.system_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON public.system_events(event_type, created_at DESC);

-- 2. Human-In-The-Loop Approval Registry
DO $$ BEGIN
    CREATE TYPE public.approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'EXECUTED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS public.approval_tickets (
    ticket_id VARCHAR(64) PRIMARY KEY,
    action_type VARCHAR(64) NOT NULL,
    risk_level VARCHAR(16) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    details JSONB NOT NULL,
    nonce VARCHAR(32) UNIQUE NOT NULL,
    status public.approval_status DEFAULT 'PENDING' NOT NULL,
    requested_by VARCHAR(64) NOT NULL,
    decided_by VARCHAR(64),
    signature TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    executed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON public.approval_tickets(status, expires_at);

-- 3. Consent & Compliance Ledger (Telephony, Outreach, Privacy)
CREATE TABLE IF NOT EXISTS public.consent_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_identifier VARCHAR(128) NOT NULL, -- Email, Phone (E.164), or Domain
    channel VARCHAR(32) NOT NULL,            -- 'EMAIL', 'VOICE_CALL', 'SMS'
    jurisdiction VARCHAR(8) NOT NULL,        -- 'US-CA', 'EU', 'IN', 'GLOBAL'
    consent_status VARCHAR(16) NOT NULL,     -- 'GRANTED', 'WITHDRAWN', 'EXPIRED'
    proof_source VARCHAR(255) NOT NULL,      -- Opt-in URL, Contract Ref, Discovery Log
    obtained_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    withdrawn_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_consent_subject_channel ON public.consent_records(subject_identifier, channel);

-- 4. Staged Tool Promotion Pipeline (Self-Improvement Quarantine)
DO $$ BEGIN
    CREATE TYPE public.tool_stage AS ENUM ('GENERATED', 'SANDBOX_TESTED', 'SECURITY_SCANNED', 'STAGED', 'APPROVED_PRODUCTION', 'REVOKED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS public.staged_tools (
    tool_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    source_code TEXT NOT NULL,
    permissions JSONB NOT NULL,              -- e.g. {"filesystem": "/tmp/sandbox", "network": "none"}
    stage public.tool_stage DEFAULT 'GENERATED' NOT NULL,
    test_results JSONB DEFAULT '{}'::jsonb,
    security_audit JSONB DEFAULT '{}'::jsonb,
    signed_by VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    promoted_at TIMESTAMPTZ,
    UNIQUE (name, version)
);

-- 5. Capabilities Registry (ACL & Risk Boundary)
CREATE TABLE IF NOT EXISTS public.capability_registry (
    capability_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    risk_level VARCHAR(16) NOT NULL,         -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    requires_approval BOOLEAN DEFAULT FALSE NOT NULL,
    allowed_agents JSONB DEFAULT '["*"]'::jsonb,
    rate_limit_per_minute INT DEFAULT 60,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Seed baseline core capabilities
INSERT INTO public.capability_registry (capability_id, name, risk_level, requires_approval, allowed_agents, rate_limit_per_minute)
VALUES 
    ('cap_fs_read', 'filesystem.read', 'LOW', false, '["*"]', 120),
    ('cap_fs_write', 'filesystem.write', 'MEDIUM', false, '["code_agent", "admin"]', 30),
    ('cap_browser', 'browser.navigate', 'MEDIUM', false, '["research_agent", "admin"]', 20),
    ('cap_email', 'outbound.email', 'HIGH', true, '["outreach_agent", "admin"]', 10),
    ('cap_shell', 'shell.execute', 'CRITICAL', true, '["admin"]', 5)
ON CONFLICT (name) DO NOTHING;
