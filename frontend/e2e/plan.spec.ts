import { expect, test } from "@playwright/test";
import { installApiMocks, PLAN, type MockState } from "./mockApi";

test("wizard creates a plan without opening the bank-transfer page", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await page.goto("/batdau");
  await page.getByRole("radio", { name: "Thử thách 100 ngày thay đổi cơ thể" }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();

  await page.locator("#challenge-gift-code").fill("TT7K3MP2QX");
  await page.getByRole("button", { name: "Dùng mã và tiếp tục" }).click();
  await expect(page).toHaveURL(/\/batdau\/TT-7K3M-P2QX/);
  await expect(page.locator("#ai-height")).toBeVisible();

  await page.locator("#ai-height").fill("170");
  await page.locator("#ai-weight").fill("70");
  await page.getByRole("button", { name: "Nam", exact: true }).click();
  await page.getByRole("button", { name: "Giảm cân" }).click();
  await page.getByRole("button", { name: /Gợi ý/ }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();

  await expect(page.getByRole("heading", { name: "Bạn đang có dụng cụ nào?" })).toBeVisible();
  await page.getByRole("button", { name: /Xà đơn treo tường/ }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();

  await page.getByRole("button", { name: "Kiểm tra thể lực" }).click();
  await page.locator("#kit-test-floor_pushup").fill("12");
  await page.locator("#kit-test-bar_pullup").fill("3");
  await page.locator("#kit-test-plank").fill("40");
  await page.locator("#kit-test-bw_squat").fill("20");
  await page.getByRole("button", { name: "Xác nhận" }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await page.getByRole("button", { name: "Tiếp tục" }).click();
  await page.getByRole("button", { name: "Mở kho thực phẩm" }).click();
  await page.getByRole("button", { name: /Ức gà/ }).click();
  await page.getByRole("button", { name: /Trứng gà/ }).click();
  await page.getByRole("button", { name: "Tinh bột" }).click();
  await page.getByRole("button", { name: /Cơm trắng/ }).click();
  await page.getByRole("button", { name: /^Bún/ }).click();
  await page.getByRole("button", { name: "Rau", exact: true }).click();
  await page.getByRole("button", { name: /Rau muống/ }).click();
  await page.getByRole("button", { name: /Cải ngọt/ }).click();
  await page.getByRole("button", { name: /Lưu lựa chọn/ }).click();
  await page.getByRole("button", { name: "Bắt đầu" }).click();

  await page.locator("#ai-gen-age").check();
  await page.locator("#ai-gen-agree").check();
  await page.getByRole("button", { name: "Nhận lịch" }).click();

  await expect(page).toHaveURL(new RegExp(`/lich/${PLAN.share_token}`), { timeout: 30_000 });
  expect(page.url()).not.toContain("thanh-toan");
  await expect(page.getByText(PLAN.title_vi).first()).toBeVisible();
});

test("shared plan page shows the plan title", async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
  await page.goto(`/lich/${PLAN.share_token}`);
  await expect(page.getByText(PLAN.title_vi).first()).toBeVisible();
});
