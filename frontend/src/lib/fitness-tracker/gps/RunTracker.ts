import { haversineMeters } from "../math/geometry";

const MAX_ACCURACY_M = 20;
const MIN_STEP_M = 0.5;

export type RunSnapshot = {
  distanceKm: number;
  speedKmh: number;
  paceMinPerKm: number | null;
  elapsedSec: number;
  pointCount: number;
  lastAccuracyM: number | null;
};

type GeoPoint = { lat: number; lon: number; at: number };

export class RunTracker {
  private watchId: number | null = null;
  private distanceM = 0;
  private lastAccepted: GeoPoint | null = null;
  private lastRaw: GeoPoint | null = null;
  private startedAt: number | null = null;
  private lastAccuracyM: number | null = null;
  private instantKmh = 0;
  private pointCount = 0;
  private readonly now: () => number;

  constructor(now: () => number = () => Date.now()) {
    this.now = now;
  }

  start(): void {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      throw new Error("Trình duyệt không hỗ trợ GPS.");
    }
    if (this.watchId != null) return;
    this.startedAt = this.now();
    this.watchId = navigator.geolocation.watchPosition(
      (pos) => this.onPosition(pos),
      () => {
        /* keep last snapshot; UI can show a stale warning */
      },
      { enableHighAccuracy: true, maximumAge: 1000, timeout: 15000 },
    );
  }

  stop(): void {
    if (this.watchId != null && typeof navigator !== "undefined") {
      navigator.geolocation.clearWatch(this.watchId);
    }
    this.watchId = null;
  }

  reset(): void {
    this.stop();
    this.distanceM = 0;
    this.lastAccepted = null;
    this.lastRaw = null;
    this.startedAt = null;
    this.lastAccuracyM = null;
    this.instantKmh = 0;
    this.pointCount = 0;
  }

  ingestForTest(lat: number, lon: number, accuracy: number, at = this.now()): void {
    this.onPosition({
      coords: { latitude: lat, longitude: lon, accuracy } as GeolocationCoordinates,
      timestamp: at,
    } as GeolocationPosition);
  }

  getSnapshot(): RunSnapshot {
    const elapsedSec = this.startedAt == null ? 0 : Math.max(0, (this.now() - this.startedAt) / 1000);
    const km = this.distanceM / 1000;
    const pace = km > 0.01 && elapsedSec > 0 ? elapsedSec / 60 / km : null;
    return {
      distanceKm: km,
      speedKmh: this.instantKmh,
      paceMinPerKm: pace,
      elapsedSec,
      pointCount: this.pointCount,
      lastAccuracyM: this.lastAccuracyM,
    };
  }

  private onPosition(pos: GeolocationPosition): void {
    const accuracy = pos.coords.accuracy;
    this.lastAccuracyM = accuracy;
    if (accuracy > MAX_ACCURACY_M) return;
    const next: GeoPoint = {
      lat: pos.coords.latitude,
      lon: pos.coords.longitude,
      at: typeof pos.timestamp === "number" ? pos.timestamp : this.now(),
    };
    this.lastRaw = next;
    if (!this.lastAccepted) {
      this.lastAccepted = next;
      this.pointCount = 1;
      return;
    }
    const step = haversineMeters(this.lastAccepted.lat, this.lastAccepted.lon, next.lat, next.lon);
    if (step < MIN_STEP_M) return;
    const dtH = (next.at - this.lastAccepted.at) / 3_600_000;
    this.instantKmh = dtH > 0 ? step / 1000 / dtH : 0;
    this.distanceM += step;
    this.lastAccepted = next;
    this.pointCount += 1;
  }
}
