# Workspace Persistence — Options & Recommendation

A "workspace" in this app is the combination of:
- the original Excel workbook (source data)
- the chain configuration (iv_chain, ev_chain, selected_machines)
- the generated report payload (all pivot / delta tables)
- metadata (user, timestamp, report name)

---

## What you get from persistence

| Capability | Without | With |
|---|---|---|
| Re-open a past report | ✗ | ✓ |
| Download Excel for a past report | ✗ | ✓ |
| Share a report link with a colleague | ✗ | ✓ |
| Audit trail (who ran what, when) | ✗ | ✓ |
| Multi-user isolation | ✗ | ✓ |

---

## Options

### Option A — SQLite + local file store (zero-dependency, single server)

**How it works**
- SQLite database (one file) stores workspace metadata, chain config, and the
  serialised report JSON.
- The original `.xlsx` upload is kept on disk in `backend/tmp/uploads/` and
  its path recorded in the DB.
- `report_id` in the DB links the metadata row to the stored JSON blob.

**Stack addition:** `sqlalchemy` (or plain `sqlite3`) — already available in
most Python environments.

**Pros**
- Zero extra services to run.
- Dead simple to back up (copy one file + one directory).
- Perfect for a single-server / local deployment.

**Cons**
- Does not scale beyond one server process.
- No built-in user authentication.

**When to choose:** Single analyst / small team running locally or on one VM.

---

### Option B — PostgreSQL + SQLAlchemy (production-grade, multi-user)

**How it works**
- `reports` table: `id UUID PK, created_at, user_id, upload_filename, iv_chain jsonb, ev_chain jsonb, selected_machines jsonb, report_payload jsonb`
- `users` table (optional, if you add auth).
- The Excel file is stored either in the DB as a `bytea` column or on disk /
  object storage, with the path recorded in the DB.

**Stack additions:** `sqlalchemy[asyncio]`, `asyncpg` (or `psycopg2`), `alembic` for migrations.

**Pros**
- Full ACID guarantees.
- Scales horizontally (multiple FastAPI workers, multiple servers).
- Rich query support — filter by date, user, scenario name, etc.
- Alembic handles schema migrations.

**Cons**
- Requires running a Postgres server.
- More moving parts.

**When to choose:** Any multi-user or cloud deployment.

---

### Option C — MongoDB (schema-flexible, document-oriented)

**How it works**
- One `reports` collection.
- Each document contains all the workspace data (chains, report payload,
  metadata) as a nested document.
- GridFS or a separate `uploads` collection for the raw Excel bytes.

**Stack addition:** `motor` (async MongoDB driver for FastAPI).

**Pros**
- No schema migration needed — add new fields freely.
- Native JSON storage — the report payload (already a dict) can be inserted as-is.
- Easy to get started with MongoDB Atlas (free tier).

**Cons**
- No joins / foreign keys — manual referential integrity.
- Less familiar to SQL-trained developers.

**When to choose:** Rapid iteration where the report schema is still evolving.

---

### Option D — Redis (fast, ephemeral / TTL-based)

**How it works**
- Store the report payload in Redis with a TTL (e.g. 24 h).
- Use `report_id` as the key.
- Not suited for permanent storage but great for caching a "session".

**Stack addition:** `redis`, `redis-py`.

**Pros**
- Microsecond read latency — instant re-open of a cached report.
- TTL-based expiry means no manual cleanup.

**Cons**
- Data is lost when Redis restarts (unless persistence is configured).
- Not suitable as the primary store; best paired with Option B.

**When to choose:** As a cache layer on top of Postgres, not as a standalone store.

---

## Recommended path

| Stage | Recommendation |
|---|---|
| MVP / local | **Option A** (SQLite). One file, no new services, works today. |
| Team deployment | **Option B** (Postgres + SQLAlchemy). Add `alembic`, define models, swap the SQLite URL for Postgres. The service layer stays unchanged. |
| High-scale read | Add **Option D** (Redis) as a read cache on top of Postgres. |

---

## What the codebase needs (Option A / B path)

### New files
```
backend/
  db/
    __init__.py
    models.py         # SQLAlchemy ORM models (Report, Upload)
    session.py        # get_db() dependency
    migrations/       # alembic (Option B only)
  services/
    workspace_service.py   # save_workspace(), load_workspace(), list_workspaces()
```

### Schema sketch (SQLAlchemy, database-agnostic)

```python
class Report(Base):
    __tablename__ = "reports"

    id           = Column(String, primary_key=True)   # UUID
    created_at   = Column(DateTime, default=datetime.utcnow)
    upload_id    = Column(String)                     # points to upload dir
    upload_name  = Column(String)
    iv_chain     = Column(JSON)
    ev_chain     = Column(JSON)
    sel_machines = Column(JSON, nullable=True)
    payload      = Column(JSON)                       # full GenerateReportResponse dict
```

### API additions needed

| Endpoint | Purpose |
|---|---|
| `GET /workspaces` | List all saved reports (id, name, date) |
| `GET /workspaces/{id}` | Re-open a saved report (returns full payload) |
| `DELETE /workspaces/{id}` | Delete a saved report |

### Effort estimate

- SQLite + SQLAlchemy (no auth): **~4 hours**
- Postgres + Alembic + auth (JWT/OAuth): **~2 days**

---

## Open-source tools to evaluate

| Tool | Purpose | Stars | Notes |
|---|---|---|---|
| `SQLAlchemy` | ORM (SQLite → Postgres) | 10 k+ | De-facto Python ORM |
| `Alembic` | DB migrations | 3 k+ | Works with SQLAlchemy |
| `SQLModel` | Pydantic + SQLAlchemy combined | 15 k+ | FastAPI author's library |
| `tortoise-orm` | Async-native ORM | 4 k+ | Alternative to SQLAlchemy async |
| `motor` | Async MongoDB driver | 2 k+ | Only for Option C |
| `redis-py` | Redis client | 12 k+ | Only for Option D |
| `python-jose` / `authlib` | JWT auth | — | When you add users |
