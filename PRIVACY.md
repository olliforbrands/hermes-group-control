# Privacy and data handling

## What is stored

When enabled, this plugin writes to **your local machine only**:

- Group JID and optional display name
- Per-message: sender JID/name, text body, timestamp, message type
- Copied media files under `~/.hermes/group-control/media/`

Data is **not** sent to the plugin author or any third party by this plugin.

## Who can access the archive

Anyone with filesystem access to your Hermes home directory (`~/.hermes/`) can read `group-control/data.db` and media files. Protect your server/account accordingly.

## WhatsApp allowlist

Full group archiving requires `WHATSAPP_ALLOWED_USERS=*` in `.env`, which allows **any** WhatsApp sender to reach your gateway (not only group members you list). Combined with `observe` mode, the bot still does not reply unless you set a group to `mention` mode.

Review [Hermes security docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md) before exposing a bot publicly.

## Legal notice

Archiving group chats may implicate:

- WhatsApp Terms of Service (unofficial clients/bridges)
- Consent and notification requirements in your jurisdiction
- Workplace or community policies

You are responsible for informing participants and complying with applicable law. This plugin provides tooling only, not legal advice.

## Deletion

To remove archived data:

```bash
rm -rf ~/.hermes/group-control/
```

Disabling the plugin in `config.yaml` stops new writes but does not delete existing files.
