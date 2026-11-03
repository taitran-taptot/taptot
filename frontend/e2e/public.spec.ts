import { expect, test } from "@playwright/test";
import { installApiMocks, type MockState } from "./mockApi";

const PAGES: { path: string; heading: string }[] = [
  { path: "/", heading: "mang thói quen sống lành mạnh" },
  { path: "/bai-tap", heading: "Kho bài tập" },
  { path: "/thuc-an", heading: "Kho thực phẩm Việt" },
  { path: "/cach-nau", heading: "Cách nấu món ăn ngon" },
  { path: "/kien-thuc", heading: "Kho kiến thức" },
  { path: "/may-tinh-calo", heading: "Máy tính calo" },
  { path: "/ve-taptot", heading: "TAPTOT" },
  { path: "/sukien", heading: "SỰ KIỆN" },
  { path: "/thu-thach-100-ngay", heading: "THỬ THÁCH 100 NGÀY" },
];

test.beforeEach(async ({ page }) => {
  const state: MockState = { user: null, orderPosts: 0 };
  await installApiMocks(page, state);
});

for (const item of PAGES) {
  test(`public page ${item.path} renders`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.goto(item.path);
    await expect(page.getByRole("heading", { name: new RegExp(item.heading, "i") }).first()).toBeVisible();
    expect(errors, errors.join("\n")).toEqual([]);
  });
}
