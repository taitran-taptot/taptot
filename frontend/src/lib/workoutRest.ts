/** Default rest between sets (seconds) — keep in sync with api/app/services/workout_rest.py */

const REST_COMPOUND_SEC = 180;
const REST_ISOLATION_SEC = 90;
const REST_CONDITIONING_SEC = 90;
const REST_MOBILITY_SEC = 60;
const REST_CARDIO_SEC = 0;
const REST_MAIN_DEFAULT_SEC = REST_ISOLATION_SEC;

function defaultRestSeconds(movementRole: string | null | undefined): number {
  const role = (movementRole || "").trim().toLowerCase();
  if (role === "compound" || role === "resistance") return REST_COMPOUND_SEC;
  if (role === "isolation") return REST_ISOLATION_SEC;
  if (role === "conditioning") return REST_CONDITIONING_SEC;
  if (role === "cardio") return REST_CARDIO_SEC;
  if (role === "mobility") return REST_MOBILITY_SEC;
  return REST_MAIN_DEFAULT_SEC;
}

export function defaultRestForSection(
  section: string | null | undefined,
  movementRole?: string | null,
): number {
  const sec = (section || "main").trim().toLowerCase();
  if (sec === "cardio") return REST_CARDIO_SEC;
  if (movementRole) return defaultRestSeconds(movementRole);
  if (sec === "warmup" || sec === "cooldown") return REST_MOBILITY_SEC;
  return REST_MAIN_DEFAULT_SEC;
}
