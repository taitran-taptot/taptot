import { expect, test } from "@playwright/test";
import { installApiMocks, ORDER, PRODUCT, type MockState } from "./mockApi";

async function addKit(page: import("@playwright/test").Page) {
  await page.goto("/mua-dung-cu");
  await expect(page.getByRole("heading", { name: PRODUCT.name_vi }).first()).toBeVisible();
  await page.getByRole("button", { name: "Thêm vào giỏ" }).first().click();
  await expect(page.getByText(`Đã thêm ${PRODUCT.name_vi} vào giỏ`)).toBeVisible();
}

test("guest COD checkout reaches success and skips bank transfer", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await addKit(page);
  await page.goto("/gio-hang");
  await expect(page.getByRole("heading", { name: "Giỏ hàng & đặt hàng" })).toBeVisible();
  await expect(page.getByRole("radio", { name: /Thanh toán khi nhận hàng/ })).toBeChecked();

  await page.getByLabel("Họ và tên").fill("Nguyen Van A");
  await page.locator("#checkout-province select").selectOption({ index: 1 });
  await page.locator("#checkout-district select").selectOption({ index: 1 });
  await page.locator("#checkout-ward select").selectOption({ index: 1 });
  await page.getByLabel(/Số nhà, tên đường/).fill("12 Pho Hue");
  await page.locator("#shop-checkout-agree").check();

  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await expect(page.getByText("Số điện thoại phải gồm 10 chữ số")).toBeVisible();
  expect(state.orderPosts).toBe(0);
  expect(page.url()).not.toContain("thanh-toan");

  await page.getByLabel("Số điện thoại").fill("0901234567");
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await expect(page).toHaveURL(/\/don-hang\/thanh-cong/);
  expect(page.url()).not.toContain("thanh-toan");
  await expect(page.getByText("Đặt hàng thành công")).toBeVisible();
  await expect(page.getByText(ORDER.public_code)).toBeVisible();
  expect(state.orderPosts).toBe(1);
});

test("order lookup shows the public code", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await page.goto("/tra-cuu-don");
  await expect(page.getByRole("heading", { name: "Tra cứu đơn hàng" })).toBeVisible();
  await page.getByLabel(/Số điện thoại|Điện thoại/i).fill("0901234567");
  await page.getByLabel(/Mã đơn/i).fill(ORDER.public_code);
  await page.getByRole("button", { name: /Tra cứu/ }).click();
  await expect(page.getByText(ORDER.public_code).first()).toBeVisible();
  await expect(page.getByText("Chờ xác nhận").first()).toBeVisible();
});
