# Backend

## Database migrations

This backend uses [Alembic](https://alembic.sqlalchemy.org/) to manage the SQLite schema.

### Setup

```bash
pip install -r requirements.txt
```

### Apply migrations

```bash
cd backend
alembic upgrade head
```

To target a specific database file, set the `DB_PATH` environment variable:

```bash
DB_PATH=/path/to/whispr.db alembic upgrade head
```

### Create a new migration

```bash
cd backend
alembic revision -m "add something"
```

### Downgrade (optional)

```bash
alembic downgrade -1
```
