# Privacy Policy — Muse Cashback Connector

Effective: September 30, 2026

The Muse Cashback Connector ("the service") is a trip ledger operated by Vincent Yao.
It records purchases where your Muse agent armed cashback attribution through your
own Rakuten Rewards account. There is no company, no employees, and no data sale —
your data is never sold, shared, or used for advertising.

## What the service stores

- **Your trip records** — only what you (via your agent) choose to log: merchant
  name, the cashback rate shown at activation, order reference, amount, currency,
  and free-text notes.
- **Token hashes** — when you link, the service mints a personal bearer token and
  stores only its SHA-256 hash. The raw token is never stored.
- **Rate-limit counters** — anonymous per-IP request counts used to prevent abuse.

## What the service never sees

- Your Rakuten account, credentials, or cashback balance.
- Your payment methods, card numbers, or purchase details beyond what is logged.
- Your browsing history. The service cannot observe your browser or your shopping.

## How data is kept

Trip data is isolated per user token: one token can never read another token's
trips. Data lives on the service's host and is retained until you delete it.

## Deletion

You can permanently delete all of your data at any time via
`DELETE /v1/account` with your bearer token. There is no recovery after deletion.

## Contact

Questions: open an issue at
https://github.com/yellowchicken280/muse-cashback-connector/issues
