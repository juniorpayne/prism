-- Database Initialization Script for Prism DNS Server (SCRUM-13)
-- SQLite schema for host registration tracking

-- Create hosts table
CREATE TABLE IF NOT EXISTS hosts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname VARCHAR(255) NOT NULL UNIQUE,
    current_ip VARCHAR(45) NOT NULL,
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'online',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_hosts_hostname ON hosts(hostname);
CREATE INDEX IF NOT EXISTS idx_hosts_status ON hosts(status);
CREATE INDEX IF NOT EXISTS idx_hosts_last_seen ON hosts(last_seen);
CREATE INDEX IF NOT EXISTS idx_hosts_hostname_status ON hosts(hostname, status);
CREATE INDEX IF NOT EXISTS idx_hosts_last_seen_status ON hosts(last_seen, status);
CREATE INDEX IF NOT EXISTS idx_hosts_created_at ON hosts(created_at);

-- Create schema version table for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_version (version, description) 
VALUES (1, 'Initial schema creation');

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_hosts_updated_at 
    AFTER UPDATE ON hosts
    FOR EACH ROW
BEGIN
    UPDATE hosts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;