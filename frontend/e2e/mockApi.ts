import type { Page, Route } from "@playwright/test";

export const PRODUCT = {
  id: 1,
  slug: "resistance-band",
  name_vi: "Dây kháng lực",
  description_vi: "Bộ dây",
  price_vnd: 500_000,
  stock_qty: 10,
  image_url: null,
  is_active: true,
};

export const ORDER = {
  id: 41,
  public_code: "TAPTOT-E2E01",
  order_status: "awaiting_confirm",
  payment_method: "cod",
  payment_status: "cod",
  total_vnd: 500_000,
  phone: "0901234567",
  items: [{ id: 1, name_vi: PRODUCT.name_vi, quantity: 1, price_vnd: PRODUCT.price_vnd }],
};

export const PLAN = {
  id: 7,
  title_vi: "Lịch tập E2E",
  description_vi: "Lịch thử",
  source: "ai",
  share_token: "e2e-plan",
  challenge_100_days: true,
  days: [
    {
      day_number: 1,
      title_vi: "Ngày 1",
      split_role: "full",
      exercises: [],
      meals: [],
    },
  ],
  insights: { challenge_100_days: true, sessions_per_week: 3 },
};

const EMPTY_PAGE = { items: [], total: 0, page: 1, page_size: 20, pages: 1 };

const EMPTY_STATS = {
  year: 2026,
  month: null,
  kpis: {
    plans_generated: 0,
    plans_admin_created: 0,
    plans_hlv_created: 0,
    orders_count: 0,
    orders_gmv_vnd: 0,
    orders_collected_vnd: 0,
    users_new: 0,
    challenge_paid_vnd: 0,
    redeem_used: 0,
    redeem_unused: 0,
    pushup_completed: 0,
  },
  months: [],
  hlv_accounts: [],
  open_orders: { awaiting_confirm: 0, awaiting_transfer: 0 },
  shop: {
    grain: "month",
    series: [],
    products: [],
    kpis: {
      orders: 0,
      cancelled: 0,
      cancel_rate: 0,
      units: 0,
      gross_vnd: 0,
      discount_vnd: 0,
      discount_orders: 0,
      discount_order_rate: 0,
      net_vnd: 0,
      aov_vnd: 0,
      collected_vnd: 0,
      shipping_vnd: 0,
      unique_customers: 0,
      repeat_customers: 0,
    },
    pushup: {
      sessions_completed: 0,
      discount_orders: 0,
      discount_vnd: 0,
      by_percent: { "5": 0, "10": 0, "15": 0, other: 0 },
    },
  },
};

export type MockState = {
  user: {
    id: string;
    email: string;
    display_name: string;
    role: string;
    email_verified: boolean;
  } | null;
  orderPosts: number;
  trackNotFound?: boolean;
  lastCheckout?: { payment_method?: string; promo_code?: string };
};

function food(id: number, name: string, roles: string[]) {
  return {
    id,
    slug: `food-${id}`,
    name_vi: name,
    serving_size: "100g",
    calories: 100,
    protein_g: roles.includes("protein") ? 20 : 2,
    carbs_g: roles.includes("carb") ? 20 : 2,
    fat_g: 1,
    tags: roles,
    macro_roles: roles,
    food_kind: "ingredient",
    status: "active",
  };
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

export async function installApiMocks(page: Page, state: MockState) {
  await page.addInitScript(() => {
    try {
      localStorage.setItem("taptot_intro_dismissed", "1");
    } catch {
      /* ignore */
    }
  });

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api\/v1/, "");
    const method = route.request().method();

    if (path === "/auth/login" && method === "POST") {
      const body = route.request().postDataJSON() as { email?: string };
      const email = body.email || "staff@example.com";
      const role = email.startsWith("admin")
        ? "admin"
        : email.startsWith("ctv")
          ? "ctv"
          : "hlv";
      state.user = {
        id: "11111111-1111-4111-8111-111111111111",
        email,
        display_name: role,
        role,
        email_verified: true,
      };
      return json(route, state.user);
    }

    if (path === "/auth/me") {
      if (!state.user) return json(route, { detail: "Unauthorized" }, 401);
      return json(route, state.user);
    }

    if (path === "/auth/refresh") {
      return json(route, { detail: "Unauthorized" }, 401);
    }

    if (path.includes("/shop/products/slug/")) {
      return json(route, PRODUCT);
    }

    if (path === "/shop/products") {
      return json(route, { ...EMPTY_PAGE, items: [PRODUCT], total: 1 });
    }

    if (path.startsWith("/shop/promo-codes/")) {
      const code = decodeURIComponent(path.slice("/shop/promo-codes/".length));
      if (code.toUpperCase() === "CTV10") {
        return json(route, { code: "CTV10", discount_percent: 10 });
      }
      return json(route, { detail: "Mã không hợp lệ" }, 404);
    }

    if (path === "/shop/orders" && method === "POST") {
      state.orderPosts += 1;
      const body = route.request().postDataJSON() as { payment_method?: string; promo_code?: string };
      state.lastCheckout = { payment_method: body.payment_method, promo_code: body.promo_code };
      return json(
        route,
        { ...ORDER, payment_method: body.payment_method || "cod" },
        201,
      );
    }

    if (path === "/shop/orders/track" && method === "POST") {
      if (state.trackNotFound) return json(route, { detail: "Order not found" }, 404);
      return json(route, ORDER);
    }

    if (path.startsWith("/shop/redeem-codes/lookup")) {
      const code = (url.searchParams.get("code") || "").replace(/-/g, "");
      const valid = code === "TT7K3MP2QX";
      return json(route, {
        valid,
        status: valid ? "unused" : "invalid",
        product_name_vi: PRODUCT.name_vi,
        code: url.searchParams.get("code") || "",
      });
    }

    if (path === "/ai/generate-workout-schedule" && method === "POST") {
      return json(route, {
        share_token: PLAN.share_token,
        view_path: `/lich/${PLAN.share_token}`,
        title_vi: PLAN.title_vi,
        code_applied: true,
      });
    }

    if (path === `/plans/share/${PLAN.share_token}/export` && method === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: "%PDF-1.4\n% e2e\n",
      });
    }

    if (path === `/plans/share/${PLAN.share_token}`) {
      return json(route, PLAN);
    }

    if (path === "/feedback" && method === "POST") {
      return json(route, { ok: true });
    }

    if (path === "/contact/trainer" && method === "POST") {
      return json(route, { ok: true });
    }

    if (path.startsWith("/admin/stats")) {
      return json(route, EMPTY_STATS);
    }

    if (path.startsWith("/my-plans")) {
      return json(route, []);
    }

    if (path.startsWith("/collaborator/promo/stats")) {
      return json(route, {
        order_count: 0,
        total_vnd: 0,
        discount_vnd: 0,
        label: "Hôm nay",
        orders: { items: [], total: 0, page: 1, page_size: 10, pages: 1 },
      });
    }

    if (path.startsWith("/collaborator/promo")) {
      return json(route, {
        code: "CTV10",
        discount_percent: 10,
        order_count: 0,
        discount_vnd: 0,
        items: [],
        total: 0,
      });
    }

    if (path.startsWith("/search/exercises")) {
      return json(route, {
        ...EMPTY_PAGE,
        items: [
          {
            id: 9,
            name_vi: "Chống đẩy",
            name_en: "Push-up",
            body_part: "chest",
            muscle_group: "Ngực",
            equipment: "Không dụng cụ",
            difficulty: 1,
            is_beginner_friendly: true,
            gif_url: null,
            is_active: true,
          },
        ],
        total: 1,
      });
    }

    if (path.startsWith("/food-categories")) {
      return json(route, EMPTY_PAGE);
    }

    if (path.startsWith("/cooking-posts/")) {
      return json(route, {
        id: 3,
        slug: "com-ga",
        title_vi: "Cơm gà",
        excerpt: "Cơm gà nhà",
        content_md: "Nấu cơm, xé thịt gà.",
        ingredients: [],
      });
    }

    if (path.startsWith("/cooking-posts")) {
      return json(route, {
        ...EMPTY_PAGE,
        items: [{ id: 3, slug: "com-ga", title_vi: "Cơm gà", group_slug: "mon-com-gia-dinh" }],
        total: 1,
      });
    }

    if (path.startsWith("/knowledge-articles")) {
      return json(route, {
        ...EMPTY_PAGE,
        items: [
          {
            id: 4,
            slug: "xac-dinh-muc-tieu-tap-luyen",
            title_vi: "Xác định mục tiêu tập luyện",
            is_published: true,
            content_md: "Chọn một mục tiêu rõ trước khi xếp lịch tập trong nhiều tuần.",
          },
        ],
        total: 1,
      });
    }

    if (path.startsWith("/search/foods")) {
      const role = url.searchParams.get("macro_role") || "protein";
      const foods =
        role === "carb"
          ? [food(3, "Cơm trắng", ["carb"]), food(4, "Bún", ["carb"])]
          : role === "produce"
            ? [food(5, "Rau muống", ["produce"]), food(6, "Cải ngọt", ["produce"])]
            : [food(1, "Ức gà", ["protein"]), food(2, "Trứng gà", ["protein"])];
      return json(route, { ...EMPTY_PAGE, items: foods, total: foods.length });
    }

    if (
      path.startsWith("/search/") ||
      path.startsWith("/knowledge") ||
      path.startsWith("/cooking-posts") ||
      path.startsWith("/site/")
    ) {
      return json(route, EMPTY_PAGE);
    }

    return json(route, {});
  });
}
