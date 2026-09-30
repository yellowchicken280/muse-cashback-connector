# Connecting the Cashback Connector to Muse

This connector installs as a **custom connector** — Meta doesn't review these;
your Muse builds the client directly from the public spec. No approval needed.

## What it is

A tiny service (stdlib-only Python, no dependencies) that does two jobs:

1. **Trip ledger API** — records every purchase where Rakuten cashback
   attribution was armed (merchant, activated rate, order ref). Each user mints
   their own token; data is fully isolated per user.
2. **Self-describing spec** — serves `openapi.json` and `llms.txt` so Muse can
   build the connector from one URL.

It does NOT talk to Rakuten's servers and does NOT confirm cashback was
credited. Crediting happens on Rakuten's side, on their schedule.

## Deploy (one time)

You need the server reachable at a public HTTPS URL so Muse can call it.
Any always-on host with Python 3 works.

**Option A — Docker (easiest):**

```bash
git clone https://github.com/yellowchicken280/muse-cashback-connector
cd muse-cashback-connector
docker build -t cashback-connector .
docker run -d -p 8000:8000 -v cashback-data:/app/data --name cashback cashback-connector
```

**Option B — plain Python:**

```bash
git clone https://github.com/yellowchicken280/muse-cashback-connector
cd muse-cashback-connector/connector
python3 server.py   # listens on 0.0.0.0:8000; PORT env to change
```

**Private mode (optional):** set `CASHBACK_LINK_SECRET` to a random string
before starting. Then `POST /v1/link` requires that secret — only people you
give it to can create accounts. Leave it unset for open registration
(rate-limited: 10 tokens/hour per IP).

Verify it's up: `https://YOUR-HOST/v1/status` should return `{"ok": true, ...}`.

## Connect in Muse

In any Muse chat, say:

> Build a custom connector from https://YOUR-HOST/openapi.json.

Muse fetches the spec, calls `POST /v1/link` to mint your personal token,
stores it in its secure credential store, and reads `llms.txt` for the workflow
rules (activated-rate check, same-session discipline, trip logging). Then shop
normally — before each purchase it routes through your Rakuten account,
verifies attribution, and logs the trip to your private ledger.

Sign into Rakuten once in Muse's browser when it asks. You never type your
Rakuten password into chat.

## Checking your trips / deleting data

- Ask Muse: "list my cashback trips" — it calls `GET /v1/trips`.
- Ask Muse: "delete my cashback data" — it calls `DELETE /v1/account`.

Remember: a logged trip means attribution was **armed**, not that Rakuten
**credited** cashback. If a trip is missing from Rakuten's account page after
their usual posting window, that's a Rakuten support question, not a connector
bug.

## Submitting to the directory (optional)

A public directory listing requires Meta's review (functional, security,
legal) via the submission form at muse.ai/platform. This build is designed for
it: per-user tokens, per-user data isolation (only hashes stored), rate
limiting, and a data-deletion endpoint. Submitting is a separate step the
account owner does themselves.
