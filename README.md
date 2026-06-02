# group-control (Hermes plugin)

Bare-minimum WhatsApp **group** archive for Hermes:

- Saves every group message + media to `~/.hermes/group-control/`
- Default **observe**: never replies (even @mentions), zero LLM on ingest
- **mention** mode: archive + Hermes replies only when @mentioned
- Hermes never reads this DB when replying

## Setup

1. Install:

```bash
git clone https://github.com/BenitoJD/hermes-group-control.git \
  ~/.hermes/plugins/group-control
```

2. Add to `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - group-control

group_control:
  db_path: ~/.hermes/group-control/data.db
  media_dir: ~/.hermes/group-control/media
  media_max_mb: 50
  default_mode: observe
  admins:
    - "15551234567"   # your WhatsApp number (country code, no +)

gateway:
  platforms:
    whatsapp:
      extra:
        require_mention: false
```

3. In `~/.hermes/.env`:

```bash
WHATSAPP_ALLOWED_USERS=*
```

Required so **all** group members' messages reach the plugin (not just allowlisted senders).

4. Enable and restart:

```bash
hermes plugins enable group-control
hermes gateway restart
```

## Commands (`/gc`)

Run **inside a WhatsApp group**. Works in **observe** and **mention** mode — the bot replies with a short confirmation (no LLM).

| Command | Effect |
|---------|--------|
| `/gc mode observe` | Archive only; bot never replies |
| `/gc mode mention` | Archive + bot replies when @mentioned |

**Who can run `/gc`:** phone numbers listed in `group_control.admins` (Hermes config — **not** WhatsApp group admins). If `admins` is empty, anyone in the group can run `/gc`.

Switching to the same mode again returns e.g. `Already in observe mode.`

## Data layout

- `~/.hermes/group-control/data.db` — SQLite (`groups`, `messages`)
- `~/.hermes/group-control/media/` — copied media files

## Tests

```bash
cd ~/.hermes/hermes-agent && pytest tests/plugins/test_group_control.py -q
```

## Limits

- Groups only (not DMs)
- Bridge may drop bursts (queue ~100)
- Group `chatName` from bridge may be JID prefix, not real title
- Stickers/locations/polls not captured by bridge today
