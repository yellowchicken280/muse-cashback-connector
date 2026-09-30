---
name: "cashback-routing"
description: "Earn cashback on Muse-driven shopping by routing purchases through your own Rakuten Rewards account. Use when the user is shopping, comparing, or buying anything through Muse's browser."
---

# Cashback Routing

## Purpose
Make every Muse browser purchase earn cashback by arming the user's own Rakuten Rewards affiliate attribution before checkout. Bring-your-own-account: no shared credentials, no middleman, no money movement.

## Workflow
1. **Check sign-in.** In the browser session, confirm the user is signed into rakuten.com. If not, start the secure browser sign-in flow. Never ask for the password in chat.
2. **Look up the merchant.** Search Rakuten for the merchant the user wants to buy from. Note the listed cashback rate.
3. **Activate and read the ACTIVATED rate.** Click through the merchant. On the "Activating Cash Back" interstitial, read the rate shown there — this is the source of truth, not the homepage rate. See `references/validated-flow.md` for why.
4. **Verify the redirect.** Follow the affiliate redirect to the merchant. Confirm attribution markers on the landing URL (LinkShare `click.linksynergy.com` hop, `clickid`/`cjevent` params, or Rakuten publisher text).
5. **Stay in the same session.** Do all shopping and checkout in that same browser session. Don't open a fresh tab/window mid-flow or navigate away and back — attribution lives in cookies set at redirect time.
6. **Report before purchase.** Tell the user: merchant, activated rate, attribution armed. Get on with the purchase.

## Output Contract
Before any purchase completes, the user sees: merchant name, the **activated** cashback rate, and confirmation that attribution is armed. If the homepage rate and activated rate differ, flag the mismatch explicitly and use the activated rate.

## Operating Rules
- The activated rate always wins over the homepage/advertised rate. Surface any discrepancy to the user.
- Same-session rule: the click-through, shopping, and checkout must share one browser session.
- Never add items to a cart or start checkout during testing or validation — arming attribution only.
- If the merchant isn't on Rakuten, say so plainly and proceed with the purchase normally.
- Covers browser-session purchases only. API or agent checkout paths with no browser session are out of scope.
- Rakuten credentials go through the secure browser sign-in only. Never in chat, never in files.
