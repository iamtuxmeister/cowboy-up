# Test App

Erlang/Cowboy web application.

## Quick start

```bash
sudo apt install inotify-tools
rebar3 as dev shell
```

Open http://localhost:8080

## Stack

- HTTP: Cowboy 2.10
- Templates: erlydtl
- CSS: basic
- Database: sqlite

## Adding a route

1. Add to `src/test_app_app.erl`: `{"/things/:id", thing_handler, []}`
2. Create `src/thing_handler.erl`
3. Create `priv/templates/thing.html`

## Models

```bash
cowboy-up model Book books title:text testament:text teachings:has_many:Teaching
cowboy-up model Teaching teachings book_id:belongs_to:Book title:text tag:many_to_many
```

## Database migrations

Add entries to `migrations()` in `src/test_app_db.erl`.

## Deploy

```bash
rebar3 release
sudo cp scripts/test_app.service /etc/systemd/system/
sudo systemctl enable --now test_app
```
