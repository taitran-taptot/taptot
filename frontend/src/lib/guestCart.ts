/** Guest shop cart in localStorage; merge into server cart after login. */

export type GuestCartLine = { product_id: number; quantity: number };

const KEY = "taptot.guest_cart.v1";
export const CART_CHANGED_EVENT = "taptot:cart-changed";

function cleanLine(x: Partial<GuestCartLine>): GuestCartLine | null {
  const product_id = Number(x.product_id);
  const quantity = Math.max(0, Math.floor(Number(x.quantity) || 0));
  if (!product_id || product_id < 1 || quantity < 1) return null;
  return { product_id, quantity };
}

function mergeLines(lines: GuestCartLine[]): GuestCartLine[] {
  const totals = new Map<number, number>();
  const order: number[] = [];
  for (const line of lines) {
    if (!totals.has(line.product_id)) order.push(line.product_id);
    totals.set(line.product_id, (totals.get(line.product_id) || 0) + line.quantity);
  }
  return order.map((product_id) => ({ product_id, quantity: totals.get(product_id) || 0 }));
}

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
    return mergeLines(parsed.map((x) => cleanLine(x)).filter((x): x is GuestCartLine => x !== null));
  } catch {
    return [];
  }
}

export function setGuestCart(items: GuestCartLine[]) {
  if (typeof window === "undefined") return;
  const cleaned = mergeLines(
    items.map((x) => cleanLine(x)).filter((x): x is GuestCartLine => x !== null),
  );
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
  const incoming = cleanLine({ product_id: productId, quantity });
  if (!incoming) return items;
  const found = items.find((i) => i.product_id === incoming.product_id);
  if (found) found.quantity += incoming.quantity;
  else items.push(incoming);
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
    else {
      const line = cleanLine({ product_id: productId, quantity });
      if (line) items.push(line);
    }
  }
  setGuestCart(items);
  return items;
}
