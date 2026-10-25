import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  addGuestCartItem,
  clearGuestCart,
  getGuestCart,
  guestCartCount,
  setGuestCart,
  setGuestCartQty,
} from "./guestCart";

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

describe("guestCart", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", new MemoryStorage());
    vi.stubGlobal("window", { dispatchEvent: vi.fn() });
    vi.stubGlobal(
      "CustomEvent",
      class {
        constructor(public type: string) {}
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("adds, increments, sets and removes a product", () => {
    expect(addGuestCartItem(7, 2)).toEqual([{ product_id: 7, quantity: 2 }]);
    expect(addGuestCartItem(7, 3)).toEqual([{ product_id: 7, quantity: 5 }]);
    expect(guestCartCount()).toBe(5);
    expect(setGuestCartQty(7, 1)).toEqual([{ product_id: 7, quantity: 1 }]);
    expect(setGuestCartQty(7, 0)).toEqual([]);
  });

  it("sanitizes invalid IDs, quantities and fractions", () => {
    setGuestCart([
      { product_id: -1, quantity: 2 },
      { product_id: 1, quantity: -2 },
      { product_id: 2, quantity: 3.9 },
      { product_id: Number.NaN, quantity: 1 },
    ]);
    expect(getGuestCart()).toEqual([{ product_id: 2, quantity: 3 }]);
  });

  it("recovers from corrupt or non-array localStorage", () => {
    localStorage.setItem("taptot.guest_cart.v1", "{broken");
    expect(getGuestCart()).toEqual([]);
    localStorage.setItem("taptot.guest_cart.v1", JSON.stringify({ product_id: 1 }));
    expect(getGuestCart()).toEqual([]);
  });

  it("clears persisted cart and behaves safely during SSR", () => {
    setGuestCart([{ product_id: 1, quantity: 2 }]);
    clearGuestCart();
    expect(getGuestCart()).toEqual([]);

    vi.stubGlobal("window", undefined);
    expect(getGuestCart()).toEqual([]);
    expect(guestCartCount()).toBe(0);
  });
});
