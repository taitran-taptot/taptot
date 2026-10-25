# Vietfit main-flow test report

Date: 2026-10-24  
Scope: event discount -> product/cart -> COD order -> admin fulfillment -> redeem code -> generated plan  
Verdict: **Not ready for production sign-off**

## What was executed

### Main-flow and P0 integrity regression

Command:

```text
python -m pytest tests/test_main_flow_regression.py tests/test_shop_checkout.py
tests/test_redeem_codes.py tests/test_fam_gen_guards.py
tests/test_workout_generation_integration.py tests/test_gen_queue.py
tests/test_auth_guest_security.py -q
```

Result after the critical-flow fixes: **104 passed, 1 expected failure, 0 unexpected failures**.

The integrated regression verifies:

- Push-up event session and 10% ticket.
- Guest COD checkout, discount floor calculation, order/item snapshot and stock.
- Redeem-code issuance without exposing the code in the public checkout response.
- Admin-visible code and forward happy-path fulfillment.
- Code reservation/consumption and plan share token.
- 201-code rollback, phone normalization and stale reservation recovery.
- Generator exception/missing plan ID release the reserved code.
- Existing redeem, queue, guest-security, cancel and checkout suites.
- Duplicate product lines are aggregated before stock validation.
- Checkout retries reuse one order through `Idempotency-Key`.
- Plan persistence and redeem-code consumption finalize in one transaction.
- Public tracking requires the exact phone + public-code pair.

The three fixed critical defects are now normal passing assertions:

- `KNOWN-CHK-014`: fixed.
- `KNOWN-CHK-018`: fixed.
- `KNOWN-GEN-007`: fixed.

The remaining expected failure is unrelated to this fix:

- `KNOWN-ADM-008`: admin fulfillment transition matrix is not enforced.

### Frontend regression

Full Vitest result: **180 passed, 0 failed** across 26 files.

Focused checkout helper result: **10 passed, 0 failed**.

New guest-cart tests verify:

- Add, increment, set, remove and count.
- Invalid ID/quantity sanitization and fractional quantity flooring.
- Corrupt/non-array localStorage recovery.
- Clear and server-side rendering safety.
- Stable idempotency key for an unchanged payload.
- Key rotation after checkout data changes and cleanup only after success.

### Full backend regression

The unfiltered command cannot collect because
`tests/test_export_schedule_matrix.py` imports the missing module
`export_schedule_matrix_xlsx`.

After excluding only that collector, result was:

- **1259 passed**
- **16 failed**
- **1 expected failure**

Failures outside this main flow are mostly catalog/search/seed drift. Relevant failures:

- `tests/test_auth_cookies.py::test_hlv_cannot_write_admin_foods`: expected 403, received 201.
- Two familiarization request expectation failures affect adjacent generation behavior.

The authorization failure reproduces alone: **8 passed, 1 failed** in
`tests/test_auth_cookies.py`. The current route deliberately uses
`require_staff_write`, while the test expects admin-only access. This is a
policy mismatch requiring a product/security decision; it must not be silently
accepted as either a test bug or an authorization bug.

### Lint

- New frontend test file: clean.
- IDE diagnostics for all new files: clean.
- Repository-wide frontend lint is not a usable gate yet:
  **95 errors and 494 warnings**, including generated MediaPipe files.

## Fixed defects and remaining risks

### Fixed in this change

1. **Duplicate checkout lines (`KNOWN-CHK-014`)**
   - Quantities are aggregated by product before row locking and stock validation.
   - A valid duplicate payload creates one order item with the summed quantity.

2. **Checkout idempotency (`KNOWN-CHK-018`)**
   - The API requires `Idempotency-Key`.
   - Same actor/key/fingerprint replays the original order; a changed payload returns 409.
   - The frontend keeps the key across retry/timeout and clears it after success.

3. **Plan/code atomicity (`KNOWN-GEN-007`)**
   - Generated plan persistence and code consumption now share one final commit.
   - Completion failure rolls back the generated plan and releases the reservation when possible.
   - Cancellation locks order redeem-code rows before collecting linked plans.

4. **Phone-only order tracking**
   - The API and UI now require phone + public code and return one matching order only.
   - Phone-only list behavior was removed.

### Remaining high risks

5. **Fulfillment transitions are unrestricted (`KNOWN-ADM-008`)**
   - API accepts `awaiting_confirm -> completed` and reverse transitions.
   - UI restrictions do not protect direct API calls or concurrent admins.
   - Required fix: enforce a transition map in the service under row lock.

6. **Event ticket checkout race is not proven safe**
   - Ticket session is not explicitly row-locked before it is marked used.
   - Requires a two-transaction PostgreSQL test and likely a conditional update/unique consumption rule.

7. **HLV food-write authorization policy conflicts with its regression test**
   - Current endpoint accepts HLV through `require_staff_write`; test expects admin-only.
   - Required action: decide the intended policy, then align route, UI and tests.

### Medium

8. Guest-cart merge can delete local lines skipped by the backend.
9. `health_note` is stored in UI state but generation sends `null`.
10. There is no operational COD payment collection state, shipment tracking, audit history or actor.
11. Redeem codes are valid immediately after checkout, before payment/delivery.
12. Tracking and event endpoints need distributed rate-limit verification.
13. Repository schema SQL and startup `ensure` migrations are not a single deterministic source.

## Environment limitations

- PostgreSQL locking/race cases were not executable: no PostgreSQL test service is configured and Docker is unavailable on this machine.
- Browser/camera E2E and multi-browser accessibility were not executable: the repository has no Playwright harness/browser dependency, and the backend default requires unavailable local PostgreSQL.
- Load p95/p99 was not executed without a production-like database and multi-worker deployment.
- These cases remain in `main-flow-test-inventory.md`; they are not reported as passed.

## Release gate

Do not sign off the flow until:

1. The remaining fulfillment transition expected failure is fixed.
2. The HLV food-write policy is resolved.
3. PostgreSQL proves last-unit stock, one-ticket, one-code-reservation and cancel/generate races.
4. PostgreSQL validates checkout idempotency and cancel/finalize locking under real concurrent transactions.
5. A browser E2E environment validates the real camera, checkout, admin and wizard journey.
6. The missing backend test module and repository-wide lint gate are repaired.
