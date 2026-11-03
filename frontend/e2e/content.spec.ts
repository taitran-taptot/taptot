import { expect, test } from "@playwright/test";
import { installApiMocks, type MockState } from "./mockApi";

test.beforeEach(async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
});

test("calorie calculator shows a daily target", async ({ page }) => {
  await page.goto("/may-tinh-calo");
  await expect(page.getByRole("heading", { name: "Máy tính calo" })).toBeVisible();
  const numbers = page.getByRole("spinbutton");
  await numbers.nth(0).fill("25");
  await numbers.nth(1).fill("170");
  await numbers.nth(2).fill("70");
  await page.getByRole("button", { name: "Tính toán ngay" }).click();
  await expect(page.getByText("kcal / ngày")).toBeVisible();
});

test("exercise and food libraries show one mocked result", async ({ page }) => {
  await page.goto("/bai-tap");
  await expect(page.getByText("Chống đẩy").first()).toBeVisible();

  await page.goto("/thuc-an");
  await expect(page.getByRole("heading", { name: "Kho thực phẩm Việt" })).toBeVisible();
  await expect(page.getByText("Ức gà").first()).toBeVisible();
});

test("cooking post opens from the list", async ({ page }) => {
  await page.goto("/cach-nau");
  await page.getByRole("link", { name: /Cơm gà/ }).click();
  await expect(page).toHaveURL(/mon=com-ga/);
  await expect(page.getByRole("heading", { name: "Cơm gà" })).toBeVisible();
});

test("knowledge article opens from its path", async ({ page }) => {
  await page.goto("/kien-thuc");
  await page.getByRole("link", { name: /Nền tảng tập luyện/ }).click();
  await page.getByRole("link", { name: /Xác định mục tiêu tập luyện/ }).first().click();
  await expect(page.getByRole("heading", { name: /Xác định mục tiêu tập luyện/ })).toBeVisible();
});

test("traditional dish path lands on the food library", async ({ page }) => {
  await page.goto("/mon-truyen-thong");
  await expect(page).toHaveURL(/\/thuc-an$/);
  await expect(page.getByRole("heading", { name: "Kho thực phẩm Việt" })).toBeVisible();
  await expect(page.getByText("Ức gà").first()).toBeVisible();
});

const EVENT_PAGES: { path: string; heading: string; url: RegExp }[] = [
  { path: "/sukien/chongday-giamgia", heading: "Quy tắc sự kiện", url: /chongday-giamgia/ },
  { path: "/sukien/plank-giamgia", heading: "Quy tắc sự kiện", url: /plank-giamgia/ },
  { path: "/kiemtratheluc", heading: "SỰ KIỆN", url: /\/sukien$/ },
];

for (const item of EVENT_PAGES) {
  test(`event page ${item.path} renders without starting the camera`, async ({ page }) => {
    await page.goto(item.path);
    await expect(page).toHaveURL(item.url);
    await expect(page.getByRole("heading", { name: new RegExp(item.heading, "i") }).first()).toBeVisible();
  });
}

const LEGAL_PAGES: { path: string; heading: string }[] = [
  { path: "/khieu-nai", heading: "Khiếu nại" },
  { path: "/dieu-khoan", heading: "Điều khoản sử dụng" },
  { path: "/chinh-sach-ban-hang", heading: "Chính sách bán hàng" },
  { path: "/chinh-sach-thanh-toan", heading: "Thanh toán và hoàn tiền" },
  { path: "/chinh-sach-bao-mat", heading: "Chính sách bảo mật" },
  { path: "/thong-tin-don-vi", heading: "Thông tin đơn vị" },
];

for (const item of LEGAL_PAGES) {
  test(`legal page ${item.path} renders`, async ({ page }) => {
    await page.goto(item.path);
    await expect(page.getByRole("heading", { name: item.heading, level: 1 })).toBeVisible();
  });
}
