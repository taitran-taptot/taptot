import { expect, test } from "@playwright/test";
import { installApiMocks, PLAN, type MockState } from "./mockApi";

test("a wrong gift code stays on the challenge gate", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await page.goto("/batdau");
  await page.getByRole("radio", { name: "Thử thách 100 ngày thay đổi cơ thể" }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await page.locator("#challenge-gift-code").fill("TT00000000");
  await page.getByRole("button", { name: "Dùng mã và tiếp tục" }).click();
  await expect(page.getByText("Mã không đúng")).toBeVisible();
  await expect(page.locator("#ai-height")).toHaveCount(0);
  expect(page.url()).not.toContain("thanh-toan");
});

test("shared plan exports a PDF", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await page.goto(`/lich/${PLAN.share_token}`);
  await expect(page.getByText(PLAN.title_vi)).toBeVisible();
  const exported = page.waitForResponse(
    (res) => res.url().includes(`/plans/share/${PLAN.share_token}/export`) && res.status() === 200,
  );
  await page.getByRole("button", { name: "Xuất PDF" }).click();
  await exported;
  await expect(page.getByText("Xuất file thất bại.")).toHaveCount(0);
});
