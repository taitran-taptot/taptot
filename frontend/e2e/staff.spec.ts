import { expect, test, type Page } from "@playwright/test";
import { installApiMocks, type MockState } from "./mockApi";

async function login(page: Page, email: string) {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await page.goto("/dang-nhap");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill("Secret12");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
}

test("public signup stays closed", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await page.goto("/dang-ky");
  await expect(page.getByRole("heading", { name: "Đăng ký đã đóng" })).toBeVisible();
});

test("admin sees stats and orders", async ({ page }) => {
  await login(page, "admin@example.com");
  await expect(page).toHaveURL(/\/tai-khoan\/quan-tri/);
  await expect(page.getByRole("button", { name: "Thống kê" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Quản trị đơn hàng" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Thống kê shop" })).toBeVisible();
});

test("coach sees only own plan tabs", async ({ page }) => {
  await login(page, "hlv@example.com");
  await expect(page).toHaveURL(/\/tai-khoan$/);
  await expect(page.getByRole("button", { name: "Lịch của tôi" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Bài tập của tôi" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Đổi mật khẩu" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Thống kê" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Quản trị đơn hàng" })).toHaveCount(0);
});

test("collaborator sees only the promo tab", async ({ page }) => {
  await login(page, "ctv@example.com");
  await expect(page).toHaveURL(/\/tai-khoan$/);
  await expect(page.getByRole("button", { name: "Mã giảm giá" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Đổi mật khẩu" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Mã giảm giá" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Lịch của tôi" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Quản trị đơn hàng" })).toHaveCount(0);
});
