-- PostgreSQL initialization script for Service Collections system
-- This script creates the necessary enum types and initial schema

-- Create custom enum types
-- Note: PostgreSQL enum names are case-sensitive and typically lowercase
CREATE TYPE projectrole AS ENUM ('OWNER', 'ADMIN', 'MANAGER', 'DEVELOPER', 'VIEWER');
CREATE TYPE projectstatus AS ENUM ('ACTIVE', 'SUSPENDED', 'ARCHIVED');
CREATE TYPE collectionenvironment AS ENUM ('DEVELOPMENT', 'TESTING', 'STAGING', 'PRODUCTION');
CREATE TYPE collectionstatus AS ENUM ('ACTIVE', 'INACTIVE', 'SUSPENDED', 'ARCHIVED');
CREATE TYPE auditaction AS ENUM (
    'CREATE', 'UPDATE', 'DELETE', 'START', 'STOP', 'RESTART',
    'APPROVE', 'REJECT', 'DEPLOY', 'ROLLBACK', 'PROMOTE'
);
CREATE TYPE notificationtype AS ENUM ('EMAIL', 'WEBHOOK', 'SLACK');

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Procrastinate job queue extension (for background tasks)
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create indexes for better performance on UUID fields
-- These will be created when SQLAlchemy creates the tables, but we can prepare

-- Note: The actual tables will be created by SQLAlchemy/Alembic migrations
-- This script only creates the enum types that are required for the column definitions
