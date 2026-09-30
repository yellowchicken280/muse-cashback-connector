# Connecting the Cashback Connector to Muse

This connector installs as a **custom connector** — Meta doesn't review these;
your Muse builds the client directly from the public spec. No approval needed.

## What it is

A tiny service (stdlib-only Python, no dependencies) that does two jobs:

1. **Trip ledger API** — records every purchase where Rakuten cashback
   attribution was armed (merchant, activated rate, order ref). Your private
   record of what the agent did.
2. **Self-describing spec** — serves `openapi.json` and `llms.txt` so Muse can
   build the connector from one URL.

It does NOT talk to Rakuten's servers and does NOT confirm cashback was
credited. Crediting happens on Rakuten's side, on their schedule.

## Deploy (one time)

You need the server reachable at a public HTTPS URL so your Muse can call it.
Any always-on host with Python 3 works (a VPS, Railway, Render, etc.).

On the host:

```bash
git clone https://github.com/yellowchicken280/muse-cashback-connector
cd muse-cashback-connector/connector
export CASHBACK_CONNECTOR_TOKEN="$(openssl rand -hex 32)"   # your private token
python3 server.py   # listens on 0.0.0.0:8000; PORT env to change
```

Skip the env var and the server generates a token on first run, saves it to
`data/.token` (chmod 600), and prints it. Either way: **the token is the only
credential — keep it to yourself.**

Verify it's up: `https://YOUR-HOST/v1/status` should return `{"ok": true, ...}`.

## Connect in Muse

In any Muse chat, say:

> Build a custom connector from https://YOUR-HOST/openapi.json.
> Authenticate with bearer token <your token>.

Muse fetches the spec, stores your token in its secure credential store, and
reads `llms.txt` for the workflow rules (activated-rate check, same-session
discipline, trip logging). Then shop normally — before each purchase it routes
through your Rakuten account, verifies attribution, and logs the trip.

Sign into Rakuten once in Muse's browser when it asks. You never type your
Rakuten password into chat.

## Checking your trips

Ask Muse: "list my cashback trips" — it calls `GET /v1/trips`. Remember:
a logged trip means attribution was **armed**, not that Rakuten **credited**
cashback. If a trip is missing from Rakuten's account page after their usual
posting window, that's a Rakuten support question, not a connector bug.

## Submitting to the directory (optional)

A public directory listing requires Meta's review (functional, security,
legal) via the submission form at muse.ai/platform. That's a separate process
from this custom-connector setup and isn't required to use it yourself.
