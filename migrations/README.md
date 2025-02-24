# Database Migrations

This directory contains database migrations using Alembic.

## Setup

1. Copy `alembic.ini.template` to `alembic.ini`:
   ```bash
   cp alembic.ini.template alembic.ini
   ```

2. Update `alembic.ini` with your database URL:
   ```ini
   sqlalchemy.url = postgresql://username:password@host:port/dbname
   ```

## Running Migrations

- To upgrade to the latest version:
  ```bash
  alembic upgrade head
  ```

- To downgrade to base:
  ```bash
  alembic downgrade base
  ```

- To create a new migration:
  ```bash
  alembic revision -m "description of changes"
  ```

## Note

The following files are ignored by git to protect sensitive information:
- `alembic.ini` (contains database credentials)
- `__pycache__/` (Python bytecode)
- `.env` files
- Database files (*.db, *.sqlite)
- IDE specific files 