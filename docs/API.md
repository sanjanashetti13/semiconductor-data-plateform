# API Reference

Base URL: `http://localhost:8000`

## Manufacturing Copilot

### `GET /api/health`
Returns `{ "status": "healthy" }`.

### `GET /api/tools`
Registered manufacturing tool names.

### `GET /api/dataset`
SECOM / warehouse metadata for the UI header.

### `POST /api/chat`
```json
{
  "question": "Which month had the lowest yield?",
  "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
}
```
Response includes `answer`, `tool`, `tool_label`, `data_source`, `execution_time`, `model`, `follow_ups`.

## Generic SQL Agent

### `POST /api/sql-agent/connect`
```json
{
  "server": "....database.windows.net",
  "database": "my_db",
  "username": "sqladmin",
  "password": "***"
}
```
Returns `session_id`, `table_count`, `schema_preview` (password never returned).

### `POST /api/sql-agent/chat`
```json
{
  "session_id": "...",
  "question": "List the tables in this database"
}
```
Returns explanation + generated `sql` (SELECT-only).

### `DELETE /api/sql-agent/session/{session_id}`
Clears in-memory credentials and schema cache.

### `GET /api/sql-agent/session/{session_id}`
Non-sensitive session status.
