Research dump on Chainlit's own thread-persistence system (`BaseDataLayer`), gathered while
deciding how to resume chat history across restarts (Further Considerations' "Chat history
reloaded on startup?"). **Not implemented** - Decisions Log Round 29 went with the lighter
"persist last thread_id + replay messages" approach instead, described in
[G - Kathrena Agent Core](../Modules/G%20-%20Kathrena%20Agent%20Core.md)/[K - Chat Interface](../Modules/K%20-%20Chat%20Interface.md). This doc exists so a future pass can revisit
the full data layer (native thread-history sidebar, click-to-resume, multi-thread switching)
without re-deriving all of this from scratch. Sourced from `docs.chainlit.io` and the installed
`chainlit` 2.12.0 package (`.venv/Lib/site-packages/chainlit/`), not guessed.

## What this actually buys you over the lighter approach
- A native thread-history sidebar (browse/search/rename/delete past conversations) - the
  translation strings for this (`threadHistory.*`, `navigation.newChat.*`) already ship in
  `.chainlit/translations/en-US.json`, unused today.
- A working "New Chat" button that actually starts a new thread rather than just always
  continuing the resumed one.
- Multiple independent, named, switchable conversations instead of one continuously-resumed
  thread.
- Element/feedback persistence (thumbs up/down, attached files) tied to specific messages -
  we don't currently use either, so not a driver on its own.

## Hard prerequisite: authentication must be enabled
Confirmed directly in Chainlit's own docs and source, not inferred:
- `docs.chainlit.io/api-reference/lifecycle-hooks/on-chat-resume`: *"Requires both data
  persistence and authentication to be enabled."*
- `docs.chainlit.io/data-persistence/history`: *"If data persistence is enabled but the user is
  not authenticated, the conversations will be stored but users won't be able to see the chat
  history. You need both data persistence and authentication configured to enable the chat
  history."*
- Traced in `chainlit/socket.py`'s `resume_thread()`: bails out immediately unless
  `session.user` is set. `session.user` is only ever populated when `require_login()` is true -
  i.e. only if the app registers a `password_auth_callback`, `header_auth_callback`, or OAuth
  (`chainlit/auth/__init__.py`). There is no "anonymous persisted thread" path - Chainlit's
  `Thread` model is fundamentally scoped to a user identifier.

This app is currently zero-auth by design (single local user, no login page, no accounts - see
Architecture Overview's runtime architecture). Adopting the full data layer means adding *some*
auth callback, even if it's a no-op that always succeeds.

### Least-invasive auth option: `header_auth_callback`
Doesn't render a login page at all (meant for reverse-proxy-delegated auth, but nothing stops a
single-user local app from just ignoring the headers and always returning the same user):

```python
import chainlit as cl

@cl.header_auth_callback
def header_auth_callback(headers: dict) -> cl.User | None:
    return cl.User(identifier="jesper")
```

Still requires a `CHAINLIT_AUTH_SECRET` environment variable to be set (signs auth tokens) per
`docs.chainlit.io/authentication/overview` - one new piece of required runtime config, even
though nothing ever actually gets typed into a login form.

## Implementation shape
### 1. Choose a community data layer: `SQLAlchemyDataLayer`
`chainlit.data.sql_alchemy.SQLAlchemyDataLayer` (bundled with the `chainlit` package already
installed) is the only self-hosted option that isn't PostgreSQL-only-by-design (the "official"
data layer is Postgres + asyncpg, S3/Azure/GCS for element storage - overkill for one local
user). Registered via:

```python
import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo="sqlite+aiosqlite:///./data/chainlit.sqlite")
```

New dependencies needed: `sqlalchemy`, `aiosqlite` (not currently in `pyproject.toml`).

**Caveat found, not yet verified hands-on:** the docs state this layer "has been tested for
PostgreSQL, however it should support more SQL databases thanks to the use of SQLAlchemy" - i.e.
SQLite support is *not* the tested/primary target. The bundled schema (below) uses Postgres-only
column types (`UUID`, `JSONB`, `TEXT[]` arrays) that SQLite has no native equivalent for -
`id UUID` would need to become `TEXT`, `metadata JSONB` becomes `TEXT` (JSON-encoded), `tags
TEXT[]` becomes a JSON-encoded list stored as `TEXT`, etc. Whether `SQLAlchemyDataLayer`'s own
query code (written with Postgres semantics like `JSONB` containment operators) works unmodified
against a SQLite connection is unverified - would need to actually stand this up and exercise it
before trusting it in a single-user always-on app of this kind.

### 2. The schema itself (Postgres-flavored, sourced from `docs.chainlit.io/data-layers/sqlalchemy`)
```sql
CREATE TABLE users (
    "id" UUID PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" JSONB NOT NULL,
    "createdAt" TEXT
);

CREATE TABLE IF NOT EXISTS threads (
    "id" UUID PRIMARY KEY,
    "createdAt" TEXT,
    "name" TEXT,
    "userId" UUID,
    "userIdentifier" TEXT,
    "tags" TEXT[],
    "metadata" JSONB,
    FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS steps (
    "id" UUID PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" UUID NOT NULL,
    "parentId" UUID,
    "streaming" BOOLEAN NOT NULL,
    "waitForAnswer" BOOLEAN,
    "isError" BOOLEAN,
    "metadata" JSONB,
    "tags" TEXT[],
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT,
    "command" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" JSONB,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INT,
    "defaultOpen" BOOLEAN,
    "modes" JSONB,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS elements (
    "id" UUID PRIMARY KEY,
    "threadId" UUID,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INT,
    "language" TEXT,
    "forId" UUID,
    "mime" TEXT,
    "props" JSONB,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedbacks (
    "id" UUID PRIMARY KEY,
    "forId" UUID NOT NULL,
    "threadId" UUID NOT NULL,
    "value" INT NOT NULL,
    "comment" TEXT,
    FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
);
```
Not bundled anywhere in the pip package itself - this has to be hand-applied (and hand-migrated
on Chainlit upgrades; the docs carry a running list of columns added to `steps` since 2.0.0:
`command` in 2.1.0, `defaultOpen` in 2.3.0, `modes` in 2.9.4 - a maintenance burden that tracks
Chainlit's own release notes, not something this project controls).

### 3. `BaseDataLayer` surface to implement (if hand-rolling instead of SQLAlchemy)
Sourced from `docs.chainlit.io/api-reference/data-persistence/custom-data-layer` - avoids the
Postgres-schema mismatch entirely by writing directly against our own SQLite schema, at the cost
of implementing/maintaining this surface by hand:
`get_user`, `create_user`, `upsert_feedback`, `delete_feedback`, `create_element`, `get_element`,
`delete_element`, `create_step`, `update_step`, `delete_step`, `get_thread_author`,
`delete_thread`, `list_threads`, `get_thread`, `update_thread`, `delete_user_session`,
`get_favorite_steps`, `close` (mandatory since Chainlit 2.8.2 - must close DB
connections/HTTP sessions on server shutdown).

### 4. Reconciling two separate thread-id systems
This app already has its own persisted "thread" concept: LangGraph's `SqliteSaver` checkpointer
(`data/agent_core_checkpoints.sqlite`), keyed by an arbitrary `thread_id` string passed into
`run_turn`. Chainlit's data layer introduces a *second*, independent thread concept (its own
`threads` table, its own UUID). These need to be kept in sync somehow - simplest option: use
Chainlit's own thread id (available via `cl.context.session.thread_id` once a data layer is
registered) as the same string passed as `thread_id` into `run_turn`, so "the LangGraph
checkpoint for this conversation" and "the Chainlit UI's record of this conversation" are always
the same key. Not yet verified hands-on whether Chainlit's auto-generated thread id is available
early enough in `on_chat_start`/`on_chat_resume` to use this way without extra plumbing.

### 5. `on_chat_resume` behavior (a plus, if adopted)
Per `docs.chainlit.io/api-reference/lifecycle-hooks/on-chat-resume`: registering
`@cl.on_chat_resume` makes Chainlit automatically (a) send the thread's persisted messages and
elements to the UI, and (b) restore the user session (JSON-serializable fields only) - i.e. the
manual `_replay_history` step the lighter approach needs (see [K - Chat Interface](../Modules/K%20-%20Chat%20Interface.md)) would
become unnecessary; Chainlit does it natively. Still need to reinstantiate anything
non-JSON-serializable ourselves (their own docs flag this explicitly for LangChain-style agents) -
in our case, nothing needs reinstantiating since `run_turn` rebuilds the graph fresh every turn
regardless.

## Recommendation if this gets revisited
Prototype against the hand-rolled `BaseDataLayer` + our own SQLite schema first, not
`SQLAlchemyDataLayer` - sidesteps the untested Postgres-type-on-SQLite question entirely, and the
method surface, while long, is mostly boilerplate CRUD against a schema we fully control and can
version ourselves (no upstream schema-migration treadmill to track). Pair with a
`header_auth_callback` that always authenticates the same fixed local user, so the login layer
stays invisible end-to-end.

## Related
- [Chainlit Thread Sidebar (Standard Pattern)](Chainlit%20Thread%20Sidebar%20%28Standard%20Pattern%29.md) - the generic/canonical version of this setup
  (auth + data layer + `on_chat_resume`, the official Postgres quickstart), plus a comparison
  against what this project actually implemented
- [G - Kathrena Agent Core](../Modules/G%20-%20Kathrena%20Agent%20Core.md)
- [K - Chat Interface](../Modules/K%20-%20Chat%20Interface.md)
- [Decisions Log](../Decisions%20Log.md) Round 29
- [Further Considerations](../Further%20Considerations.md)
