-- PowerDNS PostgreSQL Schema
-- Based on PowerDNS 4.8.x

CREATE TABLE domains (
  id                    SERIAL PRIMARY KEY,
  name                  VARCHAR(255) NOT NULL,
  master                VARCHAR(128) DEFAULT NULL,
  last_check            INT DEFAULT NULL,
  type                  VARCHAR(8) NOT NULL,
  notified_serial       BIGINT DEFAULT NULL,
  account               VARCHAR(40) DEFAULT NULL,
  options               VARCHAR(65535) DEFAULT NULL,
  catalog               VARCHAR(255) DEFAULT NULL,
  CONSTRAINT domains_name_unique UNIQUE(name)
);

CREATE INDEX domains_name_index ON domains(name);
CREATE INDEX domains_catalog_index ON domains(catalog);

CREATE TABLE records (
  id                    BIGSERIAL PRIMARY KEY,
  domain_id             INT DEFAULT NULL,
  name                  VARCHAR(255) DEFAULT NULL,
  type                  VARCHAR(10) DEFAULT NULL,
  content               VARCHAR(65535) DEFAULT NULL,
  ttl                   INT DEFAULT NULL,
  prio                  INT DEFAULT NULL,
  disabled              BOOL DEFAULT 'f',
  ordername             VARCHAR(255),
  auth                  BOOL DEFAULT 't',
  CONSTRAINT records_domain_id_foreign FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE
);

CREATE INDEX records_name_type_index ON records(name, type);
CREATE INDEX records_domain_id_index ON records(domain_id);
CREATE INDEX records_ordername_index ON records(ordername);

CREATE TABLE supermasters (
  ip                    INET NOT NULL,
  nameserver            VARCHAR(255) NOT NULL,
  account               VARCHAR(40) NOT NULL,
  PRIMARY KEY(ip, nameserver)
);

CREATE TABLE comments (
  id                    SERIAL PRIMARY KEY,
  domain_id             INT NOT NULL,
  name                  VARCHAR(255) NOT NULL,
  type                  VARCHAR(10) NOT NULL,
  modified_at           INT NOT NULL,
  account               VARCHAR(40) DEFAULT NULL,
  comment               VARCHAR(65535) NOT NULL,
  CONSTRAINT comments_domain_id_foreign FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE
);

CREATE INDEX comments_domain_id_index ON comments(domain_id);
CREATE INDEX comments_name_type_index ON comments(name, type);

CREATE TABLE domainmetadata (
  id                    SERIAL PRIMARY KEY,
  domain_id             INT NOT NULL,
  kind                  VARCHAR(32),
  content               TEXT,
  CONSTRAINT domainmetadata_domain_id_foreign FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE
);

CREATE INDEX domainmetadata_domain_id_index ON domainmetadata(domain_id);

CREATE TABLE cryptokeys (
  id                    SERIAL PRIMARY KEY,
  domain_id             INT NOT NULL,
  flags                 INT NOT NULL,
  active                BOOL,
  published             BOOL DEFAULT 't',
  content               TEXT,
  CONSTRAINT cryptokeys_domain_id_foreign FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE
);

CREATE INDEX cryptokeys_domain_id_index ON cryptokeys(domain_id);

CREATE TABLE tsigkeys (
  id                    SERIAL PRIMARY KEY,
  name                  VARCHAR(255),
  algorithm             VARCHAR(50),
  secret                VARCHAR(255),
  CONSTRAINT tsigkeys_name_unique UNIQUE(name)
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO powerdns;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO powerdns;