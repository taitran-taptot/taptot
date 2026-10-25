import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  checkoutIdempotencyKey,
  clearCheckoutIdempotencyKey,
} from "./checkoutIdempotency";

class MemoryStorage {
  private values = new Map<string, string>();

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }

  removeItem(key: string) {
    this.values.delete(key);
  }
}

describe("checkoutIdempotency", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {});
    vi.stubGlobal("sessionStorage", new MemoryStorage());
    vi.stubGlobal("crypto", {
      randomUUID: vi
        .fn()
        .mockReturnValueOnce("11111111-1111-4111-8111-111111111111")
        .mockReturnValueOnce("22222222-2222-4222-8222-222222222222")
        .mockReturnValueOnce("33333333-3333-4333-8333-333333333333"),
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("reuses the key for the same canonical payload", () => {
    const first = checkoutIdempotencyKey({
      phone: "0901234567",
      items: [{ product_id: 1, quantity: 2 }],
    });
    const replay = checkoutIdempotencyKey({
      items: [{ quantity: 2, product_id: 1 }],
      phone: "0901234567",
    });
    expect(replay).toBe(first);
  });

  it("rotates the key when checkout data changes", () => {
    const first = checkoutIdempotencyKey({
      payment_method: "cod",
      items: [{ product_id: 1, quantity: 1 }],
    });
    const changed = checkoutIdempotencyKey({
      payment_method: "cod",
      items: [{ product_id: 1, quantity: 2 }],
    });
    expect(changed).not.toBe(first);
  });

  it("keeps the key until the successful request clears it", () => {
    const first = checkoutIdempotencyKey({ items: [{ product_id: 1, quantity: 1 }] });
    clearCheckoutIdempotencyKey("another-key");
    expect(checkoutIdempotencyKey({ items: [{ product_id: 1, quantity: 1 }] })).toBe(first);

    clearCheckoutIdempotencyKey(first);
    expect(checkoutIdempotencyKey({ items: [{ product_id: 1, quantity: 1 }] })).not.toBe(first);
  });
});
