export const CONTACT_HREF = "/lien-he";

export type TrainerRegion = "bac" | "trung" | "nam";

export type Trainer = {
  id: string;
  name: string;
  initials: string;
  role: string;
  bio: string;
  imageSrc: string | null;
  region: TrainerRegion;
  regionLabel: string;
  city: string;
};

export const TRAINER_REGIONS: { id: TrainerRegion | "all"; label: string }[] = [
  { id: "all", label: "Tất cả" },
  { id: "bac", label: "Miền Bắc" },
  { id: "trung", label: "Miền Trung" },
  { id: "nam", label: "Miền Nam" },
];

const ROLE = "Kết hợp với TAPTOT";

export const TRAINERS: Trainer[] = [
  {
    id: "nguyen-van-tien",
    name: "Nguyễn Văn Tiến",
    initials: "NT",
    role: ROLE,
    bio: "Với kinh nghiệm hơn 10 năm tập luyện thi đấu và huấn luyện cho hàng trăm học viên cải thiện hình thể và sức khỏe. Tôi mong muốn góp sức vào hành trình đạt được mục tiêu của bạn.",
    imageSrc: "/hlv-nguyen-van-tien.jpg",
    region: "nam",
    regionLabel: "Miền Nam",
    city: "TP. Hồ Chí Minh",
  },
  {
    id: "le-thi-hanh",
    name: "Lê Thị Hạnh",
    initials: "LH",
    role: ROLE,
    bio: "Tập chậm cho chắc form. Lịch vừa sức người mới, ăn món Bắc quen — không cần thực đơn xa lạ.",
    imageSrc: "/hlv-le-thi-hanh.jpg",
    region: "bac",
    regionLabel: "Miền Bắc",
    city: "Hà Nội",
  },
  {
    id: "hoang-duc-anh",
    name: "Hoàng Đức Anh",
    initials: "HA",
    role: ROLE,
    bio: "Đi cùng bạn từng buổi: khởi động kỹ, tăng dần, nghỉ đúng lúc. Tập ở nhà hay gym đều được.",
    imageSrc: "/hlv-hoang-duc-anh.jpg",
    region: "trung",
    regionLabel: "Miền Trung",
    city: "Đà Nẵng",
  },
  {
    id: "tran-minh-ngoc",
    name: "Trần Minh Ngọc",
    initials: "TN",
    role: ROLE,
    bio: "Giữ nhịp đều hơn là đốt sức. Gợi ý cơm, rau, cá — món miền Tây quen, dễ nấu tại nhà.",
    imageSrc: "/hlv-tran-minh-ngoc.jpg",
    region: "nam",
    regionLabel: "Miền Nam",
    city: "Cần Thơ",
  },
];

export const FEATURED_TRAINER = TRAINERS[0];
