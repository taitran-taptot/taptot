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

export interface KnowledgeSeries {
  id: number;
  slug: string;
  title_vi: string;
  description_vi: string | null;
  level: string;
  sort_order: number;
  is_published: boolean;
}

export interface KnowledgeArticle {
  id: number;
  series_id: number | null;
  slug: string;
  title_vi: string;
  content_md: string;
  level: string;
  read_time_min: number | null;
  sort_order: number;
  is_published: boolean;
  seo_description?: string | null;
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
  user_id: string;
  order_status: "placed" | "cancelled" | string;
  total_vnd: number;
  note: string | null;
  created_at: string | null;
  items?: ShopOrderItem[];
}

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
