import { expect, test } from "@playwright/test";
import { installApiMocks, type MockState } from "./mockApi";

test.beforeEach(async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
});

test("contact form confirms the consultation request", async ({ page }) => {
  await page.goto("/lien-he");
  await expect(page.getByRole("heading", { level: 1, name: /LIÊN HỆ/ })).toBeVisible();
  await page.getByPlaceholder("Nguyễn Văn A").fill("Nguyen Van A");
  await page.getByPlaceholder("09xxxxxxxx").fill("0901234567");
  await page.getByRole("button", { name: "Đăng ký tư vấn" }).click();
  await expect(page.getByText("Đăng ký tư vấn thành công")).toBeVisible();
});

test("feedback form confirms the message was sent", async ({ page }) => {
  await page.goto("/gop-y");
  await expect(page.getByRole("heading", { name: "GÓP Ý" })).toBeVisible();
  await page.getByPlaceholder("Viết góp ý của bạn…").fill("Giao diện giỏ hàng dễ dùng hơn.");
  await page.getByRole("button", { name: "Gửi góp ý" }).click();
  await expect(page.getByText("Gửi góp ý thành công")).toBeVisible();
});
