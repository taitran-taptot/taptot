/** Guest shop cart in localStorage; merge into server cart after login. */

export type GuestCartLine = { product_id: number; quantity: number };

const KEY = "taptot.guest_cart.v1";
export const CART_CHANGED_EVENT = "taptot:cart-changed";

function emitCartChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(CART_CHANGED_EVENT));
}

export function getGuestCart(): GuestCartLine[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as GuestCartLine[];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((x) => ({
        product_id: Number(x.product_id),
        quantity: Math.max(0, Math.floor(Number(x.quantity) || 0)),
      }))
      .filter((x) => x.product_id > 0 && x.quantity > 0);
  } catch {
    return [];
  }
}

export function setGuestCart(items: GuestCartLine[]) {
  if (typeof window === "undefined") return;
  const cleaned = items
    .map((x) => ({
      product_id: Number(x.product_id),
      quantity: Math.max(0, Math.floor(Number(x.quantity) || 0)),
    }))
    .filter((x) => x.product_id > 0 && x.quantity > 0);
  localStorage.setItem(KEY, JSON.stringify(cleaned));
  emitCartChanged();
}

export function clearGuestCart() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(KEY);
  emitCartChanged();
}

export function guestCartCount(): number {
  return getGuestCart().reduce((sum, i) => sum + i.quantity, 0);
}

export function addGuestCartItem(productId: number, quantity = 1): GuestCartLine[] {
  const items = getGuestCart();
  const found = items.find((i) => i.product_id === productId);
  if (found) found.quantity += quantity;
  else items.push({ product_id: productId, quantity });
  setGuestCart(items);
  return items;
}

export function setGuestCartQty(productId: number, quantity: number): GuestCartLine[] {
  let items = getGuestCart();
  if (quantity <= 0) {
    items = items.filter((i) => i.product_id !== productId);
  } else {
    const found = items.find((i) => i.product_id === productId);
    if (found) found.quantity = quantity;
    else items.push({ product_id: productId, quantity });
  }
  setGuestCart(items);
  return items;
}
