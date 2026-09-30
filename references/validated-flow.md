# Validated flow — Rakuten → merchant attribution

Live browser test, 2026-09-30. Signed in, no purchase made (validation only — nothing added to cart, no checkout started).

## The chain (Macy's)
1. Rakuten merchant page → click "Shop Now"
2. **"Activating Cash Back" interstitial** — shows the rate being activated
3. `click.linksynergy.com` redirect (LinkShare affiliate hop)
4. Merchant landing URL carrying affiliate markers: `clickid`, `cjevent`, `cjdata`, plus publisher text naming "Ebates Performance Marketing, Inc. dba Rakuten Rewards"
5. Merchant sets first-party click cookies; affiliate params may disappear from the URL on deeper pages (observed on a Macy's product page) — attribution has moved into the cookie by then, which is expected behavior

Test product page:
`https://www.macys.com/shop/product/sanctuary-womens-autumn-edit-plaid-sleeveless-midi-dress?ID=27723355&CategoryID=5449`

## The rate discrepancy (important)
- Rakuten homepage advertised Macy's at **10% Cash Back**
- The activation interstitial displayed **"2% Cash Back Activated"**

Any integration must surface and rely on the **activated rate shown immediately before redirection**, never the homepage rate. The skill's Output Contract enforces this.

## Session notes
- Signing in did not change the redirect structure; it enables cashback to accrue to the user's account
- No CAPTCHA, bot check, or access block encountered; two promotional dialogs dismissed
- Actual cashback crediting was not tested (no purchase made)
