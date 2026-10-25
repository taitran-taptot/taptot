# Vietfit main-flow test inventory

Scope: event discount -> shop/cart -> COD checkout -> admin fulfillment -> redeem code -> generated plan.

## Execution conventions

- Priority: `P0` data loss, money, authorization, oversell, one-time token; `P1` main business behavior; `P2` compatibility and UX.
- Layers: `UNIT`, `API`, `DB`, `UI`, `E2E`, `LOAD`.
- Every execution must retain request/response, relevant DB rows, stock before/after, and UI evidence for failures.
- PostgreSQL is mandatory for locking/race cases. SQLite results are compatibility results only.
- Known product gaps are recorded as defects; they are not treated as passed behavior.

## Test data packs

- `USR`: guest, customer, HLV, admin without step-up, admin with step-up, downgraded admin.
- `PRD`: each of the three supported kits; active/inactive; price 0/normal; stock 0/1/2/200/201.
- `EVT`: push-up sessions at 0/1/20/21/50/51/500 reps; plank at 54.999/55/60 seconds; expired/finished sessions.
- `TKT`: valid 5/10/15%, expired, forged, used, concurrently submitted.
- `ORD`: every fulfillment status plus legacy `placed`; COD and bank transfer; guest and account.
- `RDM`: `unused`, `processing` fresh/stale, `redeemed`, `void`, invalid, and reusable QA code `1`.
- `GEN`: each kit, weak/strong baseline, 2-6 sessions, 30/45/60 minutes, gain/lose goal, sufficient/thin food and exercise pools.

## Event and discount ticket

- `EVT-001 P1 E2E`: push-up happy path issues the correct signed ticket.
- `EVT-002 P1 API`: discount boundaries 0/1/20/21/50/51/500.
- `EVT-003 P1 API`: negative and over-500 reps are rejected.
- `EVT-004 P0 API`: rep rate below/equal/above 1.2 reps/second.
- `EVT-005 P1 E2E`: plank success at 55 and 60 seconds gives 10%.
- `EVT-006 P1 API`: plank below 55 seconds is rejected.
- `EVT-007 P1 API`: missing, expired, already-finished session and duplicate finish.
- `EVT-008 P0 API`: forged signature/type/JTI and expired ticket are rejected.
- `EVT-009 P0 DB`: two concurrent finishes cannot issue two usable tickets.
- `EVT-010 P0 DB`: two concurrent checkouts cannot consume one ticket twice.
- `EVT-011 P1 UI`: denied/missing/busy camera and form-loss recovery.
- `EVT-012 P1 UI`: reload/back/tab close and missing sessionStorage.
- `EVT-013 P0 E2E`: UI fallback discount never changes the backend payable amount.

## Catalog and cart

- `CRT-001 P1 E2E`: list/detail of all three active kits.
- `CRT-002 P1 API`: inactive, missing, zero-price and zero-stock products.
- `CRT-003 P1 UI`: broken image/gallery/video fallback.
- `CRT-004 P1 UNIT`: guest add/increment/decrement/remove/count.
- `CRT-005 P1 UNIT`: corrupt/non-array localStorage and invalid IDs/quantities.
- `CRT-006 P1 API`: account cart add/set/delete and stock limit.
- `CRT-007 P0 DB`: concurrent account-cart writes preserve the unique user/product row.
- `CRT-008 P1 E2E`: guest cart merges additively into account cart.
- `CRT-009 P0 E2E`: skipped merge lines remain recoverable instead of being silently deleted.
- `CRT-010 P1 E2E`: price, active state, or stock changes between catalog and checkout.

## COD checkout and order integrity

- `CHK-001 P0 E2E`: guest COD creates one order and decrements stock once.
- `CHK-002 P0 E2E`: account COD uses/clears server cart.
- `CHK-003 P1 E2E`: multiple products/quantities snapshot name and price.
- `CHK-004 P0 DB`: one redeem code is issued per purchased unit.
- `CHK-005 P1 API`: COD uses `payment_status=cod`; bank transfer uses `awaiting_transfer`.
- `CHK-006 P1 API`: required recipient and administrative-area fields.
- `CHK-007 P1 API`: name boundary 1/2/120/121 and address 2/3/500/501.
- `CHK-008 P1 API`: note boundary 0/500/501.
- `CHK-009 P1 API`: phone normalization and 9/10/11-digit invalid cases.
- `CHK-010 P1 API`: unknown payment method is rejected.
- `CHK-011 P1 DB`: discount floor rounding and zero-total behavior.
- `CHK-012 P0 API`: invalid/expired/used ticket leaves order, stock and codes unchanged.
- `CHK-013 P0 API`: stock 0/1/exact/one-short and inactive/deleted product.
- `CHK-014 P0 API`: duplicate product lines cannot bypass aggregate stock validation.
- `CHK-015 P0 API`: total 200/201 redeem-code limit is atomic.
- `CHK-016 P0 DB`: DB failure before commit rolls back order/items/stock/ticket/codes.
- `CHK-018 P0 E2E`: double click, refresh, back and retry use one idempotency key and return one order.
- `CHK-019 P0 DB`: two buyers of the last unit produce one order only.
- `CHK-020 P0 DB`: checkout racing admin stock/deactivation does not oversell.
- `CHK-021 P0 DB`: checkout racing cancel keeps stock and codes consistent.
- `CHK-022 P0 API`: client-supplied name/price/discount fields are ignored.
- `CHK-023 P1 API`: huge/negative/zero/string/float quantity handling.
- `CHK-024 P0 LOAD`: large item payload is bounded and cannot exhaust code generation.

## Tracking and public-data exposure

- `TRK-001 P1 E2E`: exact phone and public code return the correct order.
- `TRK-002 P1 API`: wrong phone/code and malformed code do not reveal existence.
- `TRK-003 P1 API`: code matching is case-insensitive.
- `TRK-004 P0 API`: phone-only tracking is rejected; phone + public code returns exactly one order.
- `TRK-005 P0 API`: public responses never include redeem codes or internal fields.
- `TRK-006 P0 SECURITY`: phone enumeration and public-code brute force are rate limited.
- `TRK-007 P0 SECURITY`: order PII requires an accepted verification policy.
- `TRK-008 P1 SECURITY`: XSS/SQL injection strings remain inert.

## Admin catalog and fulfillment

- `ADM-001 P0 API`: guest/user/HLV cannot read or mutate shop admin resources.
- `ADM-002 P0 API`: admin writes require fresh step-up cookie.
- `ADM-003 P0 API`: role downgrade invalidates authorization from an old token.
- `ADM-004 P0 API`: CSRF rejects missing/foreign Origin and Referer.
- `ADM-005 P1 UI`: order pagination, status filter, empty and large result sets.
- `ADM-006 P1 API`: UTC+7 day boundaries and reversed date range.
- `ADM-007 P1 API`: bulk status with 1/100/101, duplicate and missing IDs.
- `ADM-008 P0 API`: only forward fulfillment transitions are accepted.
- `ADM-009 P0 DB`: two admins updating one order cannot silently lose an update.
- `ADM-010 P0 API`: only awaiting/legacy placed orders can be cancelled.
- `ADM-011 P0 DB`: repeated/concurrent cancel restores stock exactly once.
- `ADM-012 P0 DB`: cancel voids unused/processing/redeemed codes and deletes only linked plans.
- `ADM-013 P1 API`: product price/stock non-negative and slug unique.
- `ADM-014 P1 API`: gallery deduplication and maximum 12 URLs.
- `ADM-015 P1 API`: protected kit slugs cannot be bypassed by rename then delete.
- `ADM-016 P1 E2E`: activation cover contains each code and valid QR target.

## Redeem code and generation

- `GEN-001 P1 API`: canonical/lowercase/compact code formats.
- `GEN-002 P1 API`: invalid/void/redeemed/processing code eligibility.
- `GEN-003 P1 API`: QA code `1` is reusable and never persisted/consumed.
- `GEN-004 P0 DB`: only one concurrent reservation wins.
- `GEN-005 P0 DB`: stale reservation is reclaimed; old token cannot complete.
- `GEN-006 P0 API`: generation exception releases code and queue slot.
- `GEN-007 P0 DB`: persisted plan and consumed code are atomic.
- `GEN-008 P0 DB`: cancellation during generation cannot leave an orphan plan.
- `GEN-009 P1 API`: age/height/weight lower and upper boundaries.
- `GEN-010 P1 API`: home/equipment/experience/session count/minutes validation.
- `GEN-011 P1 UI`: all four fitness tests, meal pool and consent are required.
- `GEN-012 P0 E2E`: health note reaches the API and injury filtering.
- `GEN-013 P1 DB`: each kit produces compatible exercises and gear coverage.
- `GEN-014 P1 DB`: weak pull/push baselines apply skill gates.
- `GEN-015 P1 DB`: 2-6 sessions and 30/45/60 minute policies.
- `GEN-016 P1 DB`: three phases expand to 14 weeks with deloads at 4/8/14.
- `GEN-017 P1 DB`: gain/lose nutrition uses only catalog foods.
- `GEN-018 P1 DB`: plan/day/exercise/meal/snapshot persistence is complete.
- `GEN-019 P1 E2E`: guest plan access, login claim and four-month expiry.
- `GEN-020 P0 LOAD`: five active jobs; sixth waits or returns 429 after 60 seconds.
- `GEN-021 P1 UI`: progress minimum, long-running state, error and manual retry.
- `GEN-022 P1 API`: runtime uses deterministic picks; OpenAI metadata is not an oracle.

## Non-functional matrix

- `NFT-001 P1 LOAD`: catalog, tracking, checkout, admin list and generation p95/p99.
- `NFT-002 P0 SECURITY`: horizontal/vertical authorization and JWT replay.
- `NFT-003 P0 SECURITY`: secrets and PII are absent from logs.
- `NFT-004 P1 UI`: Chrome/Edge/Firefox/Safari desktop and mobile.
- `NFT-005 P1 UI`: slow/offline network and storage restrictions.
- `NFT-006 P2 UI`: keyboard, focus, labels, status announcements and contrast.
- `NFT-007 P1 DB`: fresh schema equals startup-upgraded schema.
- `NFT-008 P1 DB`: PostgreSQL/SQLite behavior and legacy `placed` compatibility.

## Automated coverage map

- Existing backend: `api/tests/test_pushup_challenge.py`, `test_shop_checkout.py`, `test_redeem_codes.py`, `test_auth_guest_security.py`, `test_gen_queue.py`, and workout-generation suites.
- Added main-flow regression: `api/tests/test_main_flow_regression.py`.
- Frontend utilities: `frontend/src/lib/guestCart.test.ts` and existing gift-code/fitness tests.
- Cases that require PostgreSQL, a browser camera, multiple processes, or sustained load remain execution-environment cases and are reported separately.
