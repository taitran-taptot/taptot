export type KnowledgeReadWhen = "before" | "when-needed" | "experienced";

export type KnowledgeStage = {
  key: string;
  title: string;
  slugs: string[];
};

export type KnowledgePath = {
  key: string;
  index: string;
  title: string;
  subtitle: string;
  readWhen: KnowledgeReadWhen;
  readLabel: string;
  stages: KnowledgeStage[];
};

export const KNOWLEDGE_PATHS: KnowledgePath[] = [
  {
    key: "nen-tang",
    index: "01",
    title: "Nền tảng tập luyện",
    subtitle: "Hiểu cơ thể, dụng cụ và kỹ thuật",
    readWhen: "before",
    readLabel: "Đọc trước khi bắt đầu",
    stages: [
      {
        key: "chuan-bi",
        title: "Hiểu cơ thể và chuẩn bị tập luyện",
        slugs: [
          "xac-dinh-muc-tieu-tap-luyen",
          "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
          "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
          "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
          "tap-tai-nha-chon-va-su-dung-dung-cu-an-toan",
        ],
      },
      {
        key: "ky-thuat",
        title: "Học cách thực hiện bài tập",
        slugs: [
          "khoi-dong-warm-up-van-dong-khop-mobility",
          "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
          "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
          "theo-doi-dau-va-dau-hieu-can-kham",
          "cach-doc-lich-tap-quy-uoc-buoi-tap",
        ],
      },
    ],
  },
  {
    key: "lich-tap",
    index: "02",
    title: "Xây dựng lịch tập",
    subtitle: "Volume, overload, theo dõi tiến bộ",
    readWhen: "when-needed",
    readLabel: "Đọc khi cần",
    stages: [
      {
        key: "chuong-trinh",
        title: "Xây dựng và phát triển chương trình tập",
        slugs: [
          "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency",
          "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
          "theo-doi-tien-bo-va-nhat-ky-tap-luyen",
          "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
          "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
          "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
          "nhung-sai-lam-pho-bien-khi-moi-tap",
        ],
      },
    ],
  },
  {
    key: "dinh-duong",
    index: "03",
    title: "Dinh dưỡng và phục hồi",
    subtitle: "Calo, macro, giấc ngủ, cardio",
    readWhen: "when-needed",
    readLabel: "Đọc khi cần",
    stages: [
      {
        key: "an-uong",
        title: "Dinh dưỡng và thể lực",
        slugs: [
          "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
          "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
          "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
          "uoc-luong-khau-phan-va-an-uong-thuc-te",
          "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
          "cardio-cho-suc-khoe-va-giam-mo",
          "thuc-pham-bo-sung-theo-muc-do-bang-chung",
        ],
      },
    ],
  },
  {
    key: "toi-uu",
    index: "04",
    title: "Tối ưu hóa tập luyện",
    subtitle: "RIR, periodization, kỹ thuật nâng cao",
    readWhen: "experienced",
    readLabel: "Dành cho người đã có kinh nghiệm",
    stages: [
      {
        key: "trung-cap",
        title: "Tối ưu hóa chương trình tập luyện",
        slugs: [
          "toi-uu-progressive-overload-nang-cao",
          "rpe-va-rir-trong-tung-set",
          "quan-ly-volume-theo-nhom-co",
          "deload-dung-thoi-diem",
          "periodization-co-ban",
          "mind-muscle-connection-nang-cao",
          "ky-thuat-drop-set-superset-rest-pause",
          "carb-cycling-co-ban",
          "refeed-va-diet-break",
        ],
      },
    ],
  },
];

const READ_BADGE: Record<KnowledgeReadWhen, string> = {
  before: "badge-easy",
  "when-needed": "badge-mid",
  experienced: "badge-hard",
};

export function knowledgeReadBadge(when: KnowledgeReadWhen) {
  return READ_BADGE[when];
}

export function articleCode(title: string) {
  return /^(\d+\.\d+)\s*/.exec(title.trim())?.[1] ?? null;
}

export function articleSlugsInOrder() {
  return KNOWLEDGE_PATHS.flatMap((path) => path.stages.flatMap((stage) => stage.slugs));
}

/** Display number in learning order, starting at 1.0. */
export function displayCodeForSlug(slug: string) {
  const index = articleSlugsInOrder().indexOf(slug);
  return index < 0 ? null : `1.${index}`;
}

export function pathForSlug(slug: string | null) {
  if (!slug) return null;
  return KNOWLEDGE_PATHS.find((path) => path.stages.some((stage) => stage.slugs.includes(slug))) ?? null;
}
