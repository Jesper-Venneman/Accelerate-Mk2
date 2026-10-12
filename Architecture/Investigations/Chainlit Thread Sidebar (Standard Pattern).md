Research on the **standard, widely-used pattern** for getting Chainlit's native "multiple chats in
a left sidebar" UI (thread list, search, rename, delete, "New Chat" button, click-to-resume) -
i.e. what a typical/canonical Chainlit app actually wires up to get this, independent of our own
project's specific needs. Deliberately a separate document from
[Chainlit Data Layer](Chainlit%20Data%20Layer.md), which is written from *our* project's angle
(SQLite-specific caveats, our own thread-id reconciliation problem, etc.). This one documents the
generic shape first, then (second half) compares it against what we actually have today and
analyzes the gap. Sourced from `docs.chainlit.io`, the installed `chainlit` 2.12.0 package, and the
official `Chainlit/chainlit-datalayer` GitHub repo - not guessed.

## Part 1: the standard implementation

### The three pieces, together, are what produce the sidebar
Confirmed directly in `chainlit/server.py`'s `/project/settings` endpoint - the frontend decides
whether to show the sidebar/history UI from exactly these response flags, nothing else:
```python
"dataPersistence": data_layer is not None,
"threadResumable": bool(config.code.on_chat_resume),
```
(a third gate, login, is separate - per `docs.chainlit.io/data-persistence/history`: *"If data
persistence is enabled but the user is not authenticated, the conversations will be stored but
users won't be able to see the chat history."*) So the standard recipe is always these three
pieces, in this order:

1. **An auth callback** (`password_auth_callback`, `header_auth_callback`, or OAuth) - turns on
   `require_login()`, so a `session.user` exists at all. Most tutorials/examples use
   `password_auth_callback` (simplest to demo) or OAuth (most common in real deployments, since it
   needs no password database of your own).
2. **A registered data layer** via `@cl.data_layer` - persists users/threads/steps/elements/
   feedback. This is what flips `dataPersistence` to `true`.
3. **`@cl.on_chat_resume`** registered - this is what flips `threadResumable` to `true`, and is
   also what Chainlit's docs describe as doing the actual resume work automatically: *"This
   decorator will automatically: Send the persisted messages and elements to the UI. Restore the
   user session."* (`docs.chainlit.io/api-reference/lifecycle-hooks/on-chat-resume`)

There is no separate "enable the sidebar" toggle in `config.toml` - it's entirely derived from the
three things above being present. Skipping any one of them (e.g. data layer with no auth) leaves
conversations persisted in the database but invisible to the user in the UI.

### The official, most-followed path: Postgres via the `chainlit-datalayer` repo
Chainlit's own docs present this as *the* recommended route (`docs.chainlit.io/data-layers/official`):
*"Follow the steps in this repository to persist your conversations in 2 minutes"*, linking to
`github.com/Chainlit/chainlit-datalayer`. Concretely:

```bash
# from the chainlit-datalayer repo
docker compose up -d        # spins up Postgres + a local fake S3 (Localstack) for elements
npx prisma migrate deploy   # applies the bundled Prisma schema to that Postgres instance
```
Then, in the actual Chainlit app, just point at it via an env var - no `@cl.data_layer` function
needed at all for this path, Chainlit's built-in official data layer auto-activates off this:
```bash
# .env
DATABASE_URL=postgresql://root:root@localhost:5432/postgres
```
Plus whichever cloud storage env vars if file attachments matter (`BUCKET_NAME` + AWS/Azure/GCS
credentials - a local fake-S3 via Localstack for dev, a real bucket for production). This is
explicitly the path most tutorials, starter templates, and the official docs point at first -
everything else (`SQLAlchemyDataLayer`, hand-rolled `BaseDataLayer`) is positioned as the
alternative for people who don't want a Postgres dependency.

### What actually gets persisted (the official Prisma schema)
Sourced from `chainlit-datalayer`'s `prisma/schema.prisma` directly (not the same file as the
Postgres-flavored raw SQL in [Chainlit Data Layer](Chainlit%20Data%20Layer.md), which came from the *SQLAlchemy* layer's own
docs page - the two community/official paths don't even share one canonical schema):

- **`User`** - `id`, `identifier` (unique), `metadata` (JSON), has many `Thread`s.
- **`Thread`** - `id`, `name`, `metadata`, `tags` (string array), `userId`, soft-deletable
  (`deletedAt`), has many `Step`s and `Element`s.
- **`Step`** - `id`, `threadId`, `parentId` (self-referencing, for nested steps/tool calls),
  `type` (a `StepType` enum: `user_message`, `assistant_message`, `system_message`, `tool`, `run`,
  `llm`, `embedding`, `retrieval`, `rerank`, `undefined`), `input`/`output`, `startTime`/`endTime`,
  has many `Element`s and `Feedback`.
- **`Element`** - attached files, tied to a `Step` and/or `Thread`, with `objectKey`/`url`
  pointing at cloud storage.
- **`Feedback`** - thumbs up/down + comment, tied to a `Step`.

Notably: `Step.type` is a proper enum including `tool`, `llm`, `retrieval`, etc. - not just
`user_message`/`assistant_message`. This means, in the standard pattern, `cl.Step(...)` context
managers (used for showing intermediate "thinking"/tool-call status - the same pattern this
project already uses in `_handle_turn`'s `async with cl.Step(name="thinking")`) are themselves
persisted as first-class rows, not just live-session UI decoration. Whether they render inline
under a message or need explicit filtering when redisplaying thread history is a frontend
behavior, not something the data layer controls - not verified hands-on here.

### The thread list UI itself
Confirmed in the compiled frontend bundle (`chainlit/frontend/dist/assets/*.js`) and
`.chainlit/translations/en-US.json` (already present in this project's own `.chainlit/` folder,
unused): a left sidebar (`threadHistory.sidebar.*` strings - title "Past Chats", search filter,
"Today"/"Yesterday"/"Previous 7 days"/"Previous 30 days" groupings), a "New Chat" button
(`navigation.newChat.*` - with a confirmation dialog warning *"This will clear your current chat
history"*), and per-thread actions (rename, share, delete - `threadHistory.thread.*`). All of this
ships already-built into the `chainlit` pip package's frontend bundle; none of it needs to be
built - only the three backend pieces above need wiring for it to light up.

### Optional standard extras that ride along with this setup
- **`allow_thread_sharing`** (`config.toml`'s `[features]`) - lets a user generate a public link to
  a thread, gated on its own `on_shared_thread_view` callback in addition to auth + persistence.
- **`favorites`** (`config.toml`'s `[features]`) - star a message and reuse it as a prompt
  template later; also explicitly "requires data persistence" per the docs.
- **Chat profiles** (`set_chat_profiles`) - commonly paired with `auto_tag_thread = true` (default
  `true`) so each thread gets auto-tagged with whichever profile was active - a multi-persona/
  multi-model-preset pattern, unrelated to our own single-persona Kathrena.

## Part 2: comparison against what we actually have

### What we built instead (Decisions Log Round 29) - recap
`on_chat_start` reads/writes a single persisted `agent_core.last_thread_id` setting and resumes
it if nothing else already claimed it this run; `load_thread_messages` reads straight off our own
LangGraph `SqliteSaver` checkpoint; `_replay_history` manually re-sends past Human/AI turns as
plain `cl.Message`s. No auth, no Chainlit data layer, no sidebar, no thread switching - one
continuously-resumed conversation per install, by design.

### Pain points of the standard pattern, specifically for this project
1. **Auth is non-negotiable, not just for one feature.** All three standard extras above
   (favorites, thread sharing, and the sidebar/history itself) gate on the same
   `require_login()` flag. There's no "persistence without login" configuration that still shows
   history - confirmed directly in the docs, not assumed. For a single local user with zero
   accounts today (Architecture Overview's explicit design choice), this is pure overhead adopted
   only to unlock a UI feature, not because multiple real users need isolating from each other.
2. **The "official," most-supported path assumes a standing Postgres service.** This project is
   architected as one local process with no separate services (`Architecture Overview.md#Runtime
   architecture`) - `docker compose up -d` for Postgres + Localstack contradicts that outright.
   The community `SQLAlchemyDataLayer`/hand-rolled alternatives avoid this, but both come with
   their own costs already documented in [Chainlit Data Layer](Chainlit%20Data%20Layer.md) (untested-on-SQLite Postgres
   types, or a full `BaseDataLayer` method surface to hand-maintain).
3. **Two competing "what was said when" systems, not one.** Chainlit's own `steps`/`threads`
   tables would duplicate what our own `SqliteSaver` checkpoint already tracks for LangGraph's
   benefit. [Chainlit Data Layer](Chainlit%20Data%20Layer.md) already flags needing to reconcile the two thread-id spaces;
   this investigation adds a second duplication concern - Chainlit's `Step` rows (including our
   `cl.Step(name="thinking")` calls) vs LangGraph's own message list, two different shapes of the
   same conversation, persisted twice, for two different consumers (UI replay vs. LLM context).
4. **The mental model actually changes, not just the plumbing.** Our current design treats "the
   conversation" as one long-running, continuously-resumed relationship - deliberately, given
   Kathrena's framing as a persistent companion, not a tool you start fresh sessions with. The
   standard pattern's whole UX (a sidebar of many named, switchable threads, a "New Chat" button
   that explicitly starts over) is built for the opposite mental model: many separate, disposable
   conversations. Adopting it is a real UX decision, not a transparent infrastructure upgrade.
5. **Unverified whether `cl.Step` noise would clutter resumed history.** Since `Step.type` covers
   `tool`/`llm`/`retrieval` etc. as first-class persisted rows, whether the standard `on_chat_resume`
   replay flow cleanly hides our `thinking` steps or would surface them as visible clutter in the
   thread view is genuinely unverified - would need hands-on testing, not something answerable from
   docs/source alone.

### Where the standard pattern would still be a genuine win, even for one user
Independent of the multi-user angle: real separate, named, switchable conversations (instead of
one ever-growing continuously-resumed thread with no way to branch off or start a clean one on
purpose) is a legitimate reason to want this eventually, sidebar cosmetics aside. That value is
real regardless of who's using the app - it's the auth/schema/duplication *cost* that's specific to
being a single local user, not the sidebar's usefulness.

### Possible paths forward, roughly cheapest to most invasive
1. **Do nothing (status quo).** Matches Round 29's actual decision and this project's
   single-process/no-accounts design. Recommended default until/unless multiple distinct
   conversations become a real, felt need rather than a nice-to-have.
2. **Minimal adoption: hand-rolled `BaseDataLayer` over our own SQLite schema + invisible
   `header_auth_callback` + `@cl.on_chat_resume`**, as already recommended in
   [Chainlit Data Layer](Chainlit%20Data%20Layer.md) - but additionally, *stop* hand-rolling `last_thread_id`/`_replay_history` entirely and
   let Chainlit's own resume flow be the single source of truth for what's shown in the UI,
   keeping LangGraph's `SqliteSaver` purely for the LLM's own context (same id, two purposes, but
   no more manual replay code on our side). Smaller version of the full standard pattern - no
   Postgres, no cloud storage, still opts into real thread switching.
3. **Full official pattern (Postgres + Localstack/real cloud storage + real auth).** Only makes
   sense if this ever stops being "one local desktop process for one person" - not recommended
   under the current architecture; revisit only if that premise changes.

## Related
- [Chainlit Data Layer](Chainlit%20Data%20Layer.md)
- [G - Kathrena Agent Core](../Modules/G%20-%20Kathrena%20Agent%20Core.md)
- [K - Chat Interface](../Modules/K%20-%20Chat%20Interface.md)
- [Decisions Log](../Decisions%20Log.md) Round 29
- [Further Considerations](../Further%20Considerations.md)
