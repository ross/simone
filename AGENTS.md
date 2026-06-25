# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Commands

All tooling lives in `script/` and operates against a `./env` virtualenv.

**First-time setup:**

```bash
./script/bootstrap   # creates env/, installs deps, downloads NLTK punkt_tab, symlinks pre-commit hook
```

**Day-to-day:**

```bash
./script/lint        # pycodestyle + pyflakes
./script/format      # black (line-length 80, skip-string-normalization, skip-magic-trailing-comma)
./script/format --check --quiet   # verify formatting without changing files
./script/test        # runs the full pre-commit gate: lint → format check → tests
```

**Running tests:**

```bash
./manage.py test                                          # all tests
./manage.py test slacker.tests.ClassName.method_name     # single test
```

Tests live in each app's `tests.py` (e.g. `slacker/tests.py`, `handler_about/tests.py`). The test settings activate automatically when `argv[1] == 'test'`.

**Manual handler invocation (no Slack required):**

```bash
./manage.py chat_command .ping
./manage.py chat_message "SOMETHING LOUD"
```

Both accept `--channel-type`, `--mentions`, `--sender`, etc. — see `handler/management/commands/base.py`. They drive the real dispatcher via `ConsoleContext`, so handlers execute exactly as in production.

**Production / Docker:**

```bash
./script/run           # collectstatic → migrate → gunicorn on :6444
./script/update-docker # build image and hot-swap container
```

**Dependency management:** `./script/update-requirements` regenerates `requirements.txt` using `proviso` based on the dependencies defined in `pyproject.toml`. Do **not** edit `requirements.txt` directly.

CI (`.github/workflows/main.yml`) runs `./script/bootstrap` then `./.git_hooks_pre-commit` on every PR, so the local `./script/test` gate must pass before pushing.

---

## Architecture

### Entry point

`simone/urls.py` is the startup entry point. On import it:

1. Calls `Registry.autoload()` — which uses Django's `autodiscover_modules('chat')` to import every installed app's `chat` module, causing handlers to self-register.
2. Creates a single `Dispatcher(Registry.handlers)` instance.
3. Starts a `Cron` background thread.
4. Derives Django URL patterns by combining `dispatcher.urlpatterns()` (which aggregates patterns from all listeners, like Slack) with the Django admin URLs (`/adm/`).

### Handler plugin system

Handlers are plain Python classes (no base class). A handler module must:

1. Define a class with a `config()` method and the relevant callback(s).
2. End with `Registry.register_handler(MyHandler())` to register at import time.

The `config()` dict keys that `Dispatcher` understands:

| Key | Type | Effect |
|---|---|---|
| `commands` | tuple of strings | Leader-prefixed phrases that trigger `handler.command(...)`. Use `Dispatcher.USER_PLACEHOLDER` / `CHANNEL_PLACEHOLDER` for `@user` / `#channel` tokens. |
| `messages` | bool | If True, every non-command message calls `handler.message(...)`. |
| `added` | bool | Called when simone is added to a channel. |
| `joined` | bool | Called when a user joins a channel. |
| `crons` | list of dicts | Each dict has `listener`, `channel`, and `when` (cron string). Validated by `cron-validator`; the `Cron` thread ticks once a minute. |

### Dispatch flow (`simone/dispatcher.py`)

Commands start with `.` (the leader char). `find_command_handler` greedily matches the longest registered phrase. On no match, Levenshtein distance suggests the closest known command. All dispatch methods run inside `transaction.atomic()` and suppress exceptions via `@dispatch` / `@dispatch_with_error_reporting`.

### Context abstraction (`simone/context.py`)

Handlers never call Slack APIs directly. They receive a `BaseContext` and call:

- `context.say(text, reply=False, to_user=False)` — post a message; `reply=True` threads it; `to_user=<user_id>` makes it ephemeral.
- `context.converse(texts, pauses=None)` — send a sequence with natural typing pauses.
- `context.react(emoji)` — add a reaction to the triggering message.
- `context.user_mention(user_id)` — format a user mention.

`SlackContext` (`slacker/listeners.py`) is the production impl; `ConsoleContext` is used in tests and management commands.

### Channel-type guards (`simone/handlers.py`)

Decorate handler methods to restrict by channel type:

- `@only_public` — PUBLIC channels only (default).
- `@only_channel_types(channel_types={...})` — explicit set of `ChannelType` values.
- `@exclude_private` — anywhere except PRIVATE.
- `@exclude_channel_types(channel_types={...})` — explicit exclusion.

A shared `requests.Session` (`session`, in `simone/handlers.py`) with a 5-second timeout and a `simone/0.0` user-agent is available to all handlers for HTTP calls.

### App layout

| Directory | Purpose |
|---|---|
| `simone/` | Django project: settings, dispatcher, context, handler registry |
| `slacker/` | Slack Bolt integration: `SlackListener`, `SlackContext`, `Channel` model |
| `handler/` | Catch-all app; `handler/chat/` holds many small command modules |
| `handler_about/` | `@user is …` / `who is @user` — stores facts in DB |
| `handler_loud/` | Learns and repeats LOUD MESSAGES |
| `handler_memory/` | `.rem` / `.remember` / `.forget` |
| `handler_responder/` | Scheduled/cron-based responder |
| `handler_sparkles/` | `.sparkle` command |

All handler apps are listed in `INSTALLED_APPS` (`simone/settings/__init__.py`).

### Settings

`simone/settings/__init__.py` delegates to `dev.py`, `prod.py`, or `test.py` based on the `ENV` env var (`dev` by default). Required env vars: `DJANGO_SECRET_KEY`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` (plus optional API keys for weather, stocks, images etc. — see `.git_hooks_pre-commit` for the full list). Note that if you run `./script/test` locally, `.git_hooks_pre-commit` automatically mocks all of these with default values so you do not need to manually export them.

For database setup, production uses MySQL/MariaDB. For local development, `dev.py` defaults to **SQLite** (`db/db.sqlite3`) making it easy to run locally without setup. However, `docker-compose.yml` provides a local MariaDB instance if you set `SIMONE_DB_NAME` in your environment.

### Custom test runner (`simone/test.py`)

`SimoneRunner` buffers per-test log output and appends it to failure messages, so failed tests show their logs without cluttering passing test output.

### Adding a new handler

1. Add a `chat.py` (or a file in an existing app's `chat/` package) with a handler class and `Registry.register_handler(...)`.
2. If the handler needs DB models, create a new Django app, add it to `INSTALLED_APPS`, and run `./manage.py makemigrations`.
3. If the handler requires new external dependencies, add them to `pyproject.toml` and run `./script/update-requirements` to regenerate `requirements.txt`.

### Code style

`black` at line-length 80, `--skip-string-normalization`, `--skip-magic-trailing-comma`. `pycodestyle` ignores `E203, E501, E741, W503`.
