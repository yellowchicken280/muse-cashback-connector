# Muse Cashback Connector (Flavor 2: bring-your-own)

Earn Rakuten cashback on everything your Muse AI agent buys for you — using **your own** Rakuten Rewards account. No middleman, no new account, no money moving through anyone's hands.

## Why

Meta's Muse is becoming a shopping agent. Every purchase it makes on your behalf is currently unattributed GMV — no cashback, no rewards, nothing. This connector arms your own Rakuten Rewards affiliate attribution before Muse checks out, so the cashback flows to you.

## How it works

1. You shop through Muse as normal ("find me X", "buy Y").
2. Before heading to the merchant, Muse routes through your Rakuten account: looks up the merchant, activates cash back, and follows the affiliate redirect.
3. Muse verifies the attribution markers on the merchant landing page, then completes your purchase in the same browser session.
4. Cashback accrues to your Rakuten account like any other Rakuten trip.

The full chain was validated live on Macy's on 2026-09-30: Rakuten interstitial → LinkShare redirect → merchant landing with affiliate params intact. Details in `references/validated-flow.md`.

## The rate-transparency catch

During testing I found that Rakuten's homepage advertised **10%** cash back at Macy's, but the activation interstitial showed **2% activated**. The connector always surfaces the **activated** rate — the one shown immediately before redirection — and flags any mismatch. Never trust the homepage rate.

## Setup

1. Add this folder as a custom connector in Muse (unlisted — no review needed).
2. Sign into your Rakuten account once in Muse's browser.
3. Shop. Before each purchase, Muse reports the merchant, the activated rate, and confirms attribution is armed.

You never type your Rakuten password into chat — sign-in happens through the browser's secure flow.

## Limitations (honest)

- Covers browser-session purchases only. Pure API checkout paths with no browser session aren't covered.
- Only merchants on Rakuten earn cashback; everything else proceeds normally.
- Cashback crediting itself happens on Rakuten's side on their usual schedule — this connector arms attribution, it doesn't guarantee Rakuten's payout timing.
- This is a prototype, not a native Meta × Rakuten integration. A first-party version (the Bilt × Rakuten model) would be strictly better — this is the version anyone can use today.

## What's next

- A hosted publisher-model version (I become the affiliate publisher, users get cashback through me) — bigger swing, startup-shaped, on hold pending publisher approvals.
- A one-page partnership proposal for Meta × Rakuten is in this repo's parent folder.

Built by Vinny Yao, UC Berkeley. Incoming Google SWE intern, Summer 2027.
