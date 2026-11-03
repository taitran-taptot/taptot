import { expect, test, type Page } from "@playwright/test";
import { installApiMocks, ORDER, PRODUCT, type MockState } from "./mockApi";

function pushupTicket() {
  const part = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${part({ alg: "none" })}.${part({
    type: "pushup_ticket",
    reps: 25,
    percent: 10,
    kind: "pushup",
  })}.sig`;
}

async function addKit(page: Page) {
  await page.goto("/mua-dung-cu");
  await page.getByRole("button", { name: "Thêm vào giỏ" }).first().click();
  await expect(page.getByText(`Đã thêm ${PRODUCT.name_vi} vào giỏ`)).toBeVisible();
}

async function fillCheckout(page: Page) {
  await page.getByLabel("Họ và tên").fill("Nguyen Van A");
  await page.getByLabel("Số điện thoại").fill("0901234567");
  await page.locator("#checkout-province select").selectOption({ index: 1 });
  await page.locator("#checkout-district select").selectOption({ index: 1 });
  await page.locator("#checkout-ward select").selectOption({ index: 1 });
  await page.getByLabel(/Số nhà, tên đường/).fill("12 Pho Hue");
  await page.locator("#shop-checkout-agree").check();
}

test("product detail adds the band to the guest cart", async ({ page }) => {
  await installApiMocks(page, { user: null, orderPosts: 0 });
  await page.goto(`/mua-dung-cu/${PRODUCT.slug}`);
  await expect(page).toHaveURL(/\/mua-dung-cu\/day-khang-luc/);
  await expect(page.getByRole("heading", { name: PRODUCT.name_vi })).toBeVisible();
  await page.getByRole("button", { name: "Thêm vào giỏ" }).click();
  await expect(page.getByText(`Đã thêm ${PRODUCT.name_vi} vào giỏ`)).toBeVisible();
  await page.goto("/gio-hang");
  await expect(page.getByText(PRODUCT.name_vi).first()).toBeVisible();
});

test("guest can raise quantity and then empty the cart", async ({ page }) => {
  await installApiMocks(page, { user: null, orderPosts: 0 });
  await addKit(page);
  await page.goto("/gio-hang");
  await expect(page.getByText("1", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Tăng số lượng" }).click();
  await expect(page.getByText("2", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Xóa" }).click();
  await expect(page.getByText("Giỏ hàng trống")).toBeVisible();
});

test("promo code rejects a bad code and discounts a COD order", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await addKit(page);
  await page.goto("/gio-hang");

  await page.getByPlaceholder("MAGIAMGIA").fill("SAI");
  await page.getByRole("button", { name: "Áp dụng" }).click();
  await expect(page.getByText("Mã không hợp lệ")).toBeVisible();

  await page.getByPlaceholder("MAGIAMGIA").fill("CTV10");
  await page.getByRole("button", { name: "Áp dụng" }).click();
  await expect(page.getByText("Giảm mã CTV10")).toBeVisible();
  await expect(page.getByText(/450\.000/)).toBeVisible();
  await expect(page.getByRole("radio", { name: /Thanh toán khi nhận hàng/ })).toBeChecked();

  await fillCheckout(page);
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await expect(page).toHaveURL(/\/don-hang\/thanh-cong/);
  expect(page.url()).not.toContain("thanh-toan");
  expect(state.lastCheckout).toMatchObject({ payment_method: "cod", promo_code: "CTV10" });
});

test("pushup ticket shows a COD discount and stays off the transfer page", async ({ page }) => {
  await installApiMocks(page, { user: null, orderPosts: 0 });
  await page.addInitScript((ticket) => {
    sessionStorage.setItem("taptot_pushup_discount", ticket);
  }, pushupTicket());
  await addKit(page);
  await page.goto("/gio-hang");
  await expect(page.getByText("Giảm 10% thử thách chống đẩy")).toBeVisible();
  await expect(page.getByText("Giảm thử thách chống đẩy")).toBeVisible();
  await expect(page.getByRole("radio", { name: /Thanh toán khi nhận hàng/ })).toBeChecked();
  expect(page.url()).not.toContain("thanh-toan");
});

test("unknown order lookup says the order was not found", async ({ page }) => {
  await installApiMocks(page, { user: null, orderPosts: 0, trackNotFound: true });
  await page.goto("/tra-cuu-don");
  await page.getByLabel(/Số điện thoại|Điện thoại/i).fill("0901234567");
  await page.getByLabel(/Mã đơn/i).fill(ORDER.public_code);
  await page.getByRole("button", { name: /Tra cứu/ }).click();
  await expect(page.getByText("Không tìm thấy đơn hàng. Kiểm tra lại số điện thoại và mã đơn.")).toBeVisible();
});
