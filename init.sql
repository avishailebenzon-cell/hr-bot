-- HR Bot Database Initialization Script
-- Run this script to set up the initial database schema

-- Create ENUM types
CREATE TYPE meeting_type AS ENUM ('team_lunch', 'site_visit', 'company_event', 'custom');
CREATE TYPE meeting_status AS ENUM ('draft', 'scheduled', 'cancelled', 'completed');
CREATE TYPE conversation_state_type AS ENUM (
    'quarterly_lunch',
    'quarterly_gifts',
    'monthly_site_visit',
    'monthly_company_event',
    'custom_meeting'
);

-- HR Configurations table
CREATE TABLE hr_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    timezone VARCHAR(50) DEFAULT 'Asia/Jerusalem',
    outlook_email VARCHAR(255),
    outlook_access_token TEXT,
    outlook_refresh_token TEXT,
    outlook_token_expiry TIMESTAMP,
    company_sites JSONB DEFAULT '[]'::jsonb,
    site_managers JSONB DEFAULT '{}'::jsonb,
    last_quarterly_reminder TIMESTAMP,
    last_monthly_reminder TIMESTAMP,
    last_gift_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled Meetings table
CREATE TABLE scheduled_meetings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    meeting_type meeting_type DEFAULT 'custom',
    event_name VARCHAR(255) NOT NULL,
    description TEXT,
    scheduled_date TIMESTAMP NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    recipients JSONB DEFAULT '[]'::jsonb,
    outlook_event_id VARCHAR(255) UNIQUE,
    outlook_event_url TEXT,
    status meeting_status DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES hr_configs(id) ON DELETE CASCADE
);

-- Conversation States table
CREATE TABLE conversation_states (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    state_type conversation_state_type NOT NULL,
    current_step VARCHAR(50) NOT NULL,
    context_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '24 hours',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES hr_configs(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX idx_hr_configs_user_id ON hr_configs(user_id);
CREATE INDEX idx_scheduled_meetings_user_id ON scheduled_meetings(user_id);
CREATE INDEX idx_scheduled_meetings_scheduled_date ON scheduled_meetings(scheduled_date);
CREATE INDEX idx_scheduled_meetings_outlook_event_id ON scheduled_meetings(outlook_event_id);
CREATE INDEX idx_conversation_states_user_id ON conversation_states(user_id);
CREATE INDEX idx_conversation_states_expires_at ON conversation_states(expires_at);

-- Add comment
COMMENT ON TABLE hr_configs IS 'Stores user configurations and Outlook tokens';
COMMENT ON TABLE scheduled_meetings IS 'Records of all scheduled meetings';
COMMENT ON TABLE conversation_states IS 'Tracks multi-step user conversations';
