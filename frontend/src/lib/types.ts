export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ExerciseListItem {
  id: number;
  name_en: string;
  name_vi: string;
  body_part: string;
  muscle_group?: string | null;
  muscle_group_id?: number | null;
  equipment: string;
  equipment_slugs?: string[];
  exercise_type?: string;
  exercise_type_label?: string | null;
  movement_role?: string | null;
  movement_pattern?: string | null;
  venue?: string | null;
  difficulty: number | string;
  difficulty_label?: string | null;
  notes_vi?: string | null;
  is_beginner_friendly: boolean;
  gif_url: string | null;
  image_url?: string | null;
  video_url?: string | null;
}

export interface ExerciseDetail extends ExerciseListItem {
  target_muscle: string;
  secondary_muscles: string[];
  muscle_group?: string | null;
  instruction_vi?: string | null;
  instruction_steps_vi?: string[] | null;
  instruction_en?: string | null;
  instruction_steps_en?: string[] | null;
  common_mistakes_vi?: string | null;
  tips_vi?: string | null;
  image_url?: string | null;
}

export interface FoodVitamins {
  [key: string]: number;
}

export interface Food {
  id: number;
  slug: string;
  name_vi: string;
  name_en: string | null;
  category_id: number | null;
  serving_size: string;
  serving_grams: number | null;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
  sugar_g: number | null;
  sodium_mg: number | null;
  is_verified: boolean;
  is_common: boolean;
  tags: string[];
  image_url: string | null;
  vitamins_json?: FoodVitamins | null;
  owner_user_id?: string | null;
  is_custom?: boolean;
  food_kind?: "ingredient" | "dish" | "packaged" | string;
  prep_state?: "raw" | "cooked" | "dry" | string | null;
  status?: string;
  kcal_100g?: number | null;
  protein_100g?: number | null;
  carbs_100g?: number | null;
  fat_100g?: number | null;
  fiber_100g?: number | null;
  sugar_100g?: number | null;
  sodium_100mg?: number | null;
  alcohol_100g?: number | null;
  macro_roles?: string[];
  meal_slots?: string[];
  is_complete_meal?: boolean | null;
  ai_eligible?: boolean;
  default_for_ai?: boolean;
  /** Geographic region for traditional dishes map */
  region_slug?: FoodRegionSlug | string | null;
  /** Map feature id: "01" Hà Nội, "79" TP.HCM, "hoang-sa", … */
  province_id?: string | null;
  description_vi?: string | null;
  source_ref?: string | null;
  confidence?: string | null;
  density_g_per_ml?: number | null;
  portions?: FoodPortionOption[];
}

export interface FoodPortionOption {
  label_vi: string;
  grams: number;
  is_default?: boolean;
  sort_order?: number;
}

export type FoodRegionSlug =
  | "mien-bac"
  | "mien-trung"
  | "mien-nam"
  | "hoang-sa"
  | "truong-sa";

export const FOOD_REGION_LABELS: Record<FoodRegionSlug, string> = {
  "mien-bac": "Miền Bắc",
  "mien-trung": "Miền Trung",
  "mien-nam": "Miền Nam",
  "hoang-sa": "Hoàng Sa",
  "truong-sa": "Trường Sa",
};

export interface Label {
  key: string;
  label_vi: string;
  id?: number;
  category?: string | null;
  name_en?: string | null;
  parent_id?: number | null;
  parent_slug?: string | null;
  is_filter_only?: boolean | null;
  image_url?: string | null;
  image_source?: string | null;
  image_attribution?: string | null;
}

export interface EquipmentImageItem {
  url: string;
  thumb: string;
  alt?: string;
}

export interface FoodCategory {
  id: number;
  slug: string;
  name_vi: string;
  sort_order: number;
}

export interface KnowledgeArticle {
  id: number;
  slug: string;
  title_vi: string;
  content_md: string;
  level: string;
  read_time_min: number | null;
  sort_order: number;
  is_published: boolean;
  seo_title?: string | null;
  seo_description?: string | null;
}

export interface CookingIngredient {
  food_slug: string | null;
  grams: number | null;
  amount_label: string | null;
  note?: string | null;
  name_vi?: string | null;
  image_url?: string | null;
  calories?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
}

export interface CookedMacros {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g?: number | null;
  grams?: number | null;
  kcal_100g?: number | null;
  protein_100g?: number | null;
  carbs_100g?: number | null;
  fat_100g?: number | null;
  fiber_100g?: number | null;
}

export interface YieldPortion {
  k: number;
  n: number;
  label: string;
  grams: number;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g?: number | null;
}

export interface CookingPost {
  id: number;
  slug: string;
  title_vi: string;
  excerpt: string | null;
  content_md: string;
  cover_image_url: string | null;
  is_published: boolean;
  published_at: string | null;
  author_user_id?: string | null;
  sort_order: number;
  dish_slug?: string | null;
  servings?: number;
  yield_grams?: number | null;
  grams_per_serving?: number | null;
  group_slug?: string | null;
  group_vi?: string | null;
  dish_name_vi?: string | null;
  dish_serving_grams?: number | null;
  dish_calories?: number | null;
  batch_calories?: number | null;
  serving_calories?: number | null;
  batch_macros?: CookedMacros | null;
  serving_macros?: CookedMacros | null;
  cooked_per_100g?: CookedMacros | null;
  yield_portions?: YieldPortion[];
  nutrition_note?: string | null;
  source_url?: string | null;
  source_title?: string | null;
  yield_note?: string | null;
  ingredients?: CookingIngredient[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ShopProduct {
  id: number;
  slug: string;
  name_vi: string;
  description_vi: string | null;
  price_vnd: number;
  stock_qty: number;
  image_url: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ShopCartItem {
  product_id: number;
  name_vi: string;
  price_vnd: number;
  stock_qty: number;
  image_url: string | null;
  is_active: boolean;
  quantity: number;
  line_total_vnd: number;
}

export interface ShopCart {
  items: ShopCartItem[];
  total_vnd: number;
}

export interface ShopOrderItem {
  id: number;
  product_id: number | null;
  name_vi: string;
  unit_price_vnd: number;
  quantity: number;
  line_total_vnd: number;
}

export interface ShopOrder {
  id: number;
  user_id: string | null;
  public_code?: string | null;
  order_status: string;
  fulfillment_status?: string;
  total_vnd: number;
  shipping_fee_vnd?: number;
  note: string | null;
  recipient_name?: string | null;
  phone?: string | null;
  province_code?: string | null;
  province_name?: string | null;
  district_code?: string | null;
  district_name?: string | null;
  ward_code?: string | null;
  ward_name?: string | null;
  address_line?: string | null;
  payment_method?: string | null;
  payment_status?: string | null;
  discount_percent?: number;
  discount_vnd?: number;
  created_at: string | null;
  items?: ShopOrderItem[];
  gift_codes?: {
    id: number;
    code: string;
    status: string;
    plan_id?: number | null;
  }[];
  bank_transfer?: {
    bank_name?: string | null;
    bank_bin?: string | null;
    account_number?: string | null;
    account_name?: string | null;
    transfer_content: string;
    amount_vnd: number;
    qr_image_url?: string | null;
  };
}

export type ShopCheckoutPayload = {
  note?: string | null;
  recipient_name: string;
  phone: string;
  province_code: string;
  province_name: string;
  district_code: string;
  district_name: string;
  ward_code: string;
  ward_name: string;
  address_line: string;
  payment_method: "cod" | "bank_transfer";
  items?: { product_id: number; quantity: number }[];
  pushup_ticket?: string | null;
};

export type Gender = "male" | "female";
/** Weight goals are mutually exclusive; Calculator still uses gain_muscle. */
export type Goal = "lose_weight" | "maintain" | "gain_muscle" | "gain_weight";
export type WeightGoal = "lose_weight" | "maintain" | "gain_weight";
export type ExtraGoal =
  | "strength"
  | "endurance"
  | "mental_health"
  | "heartbreak_recovery"
  | "physique";
export type Activity = "sedentary" | "light" | "moderate" | "active" | "very_active";
