import {
  CHALLENGE_BRANCHES,
  DIRECTION_COMING_SOON,
  FOUNDATION_NODES,
  SPECIALIZATION_BRANCHES,
  type DirectionSelection,
  type FamiliarizationPath,
} from "@/lib/directionTree";

export type DirectionNodeContent = {
  id: string;
  title: string;
  meta: string;
  kicker: string;
  intro: string[];
  image: string;
  benefits?: { title: string; body: string }[];
};

function imageFor(id: string) {
  return `/direction-tree/${id}.webp`;
}

const FOUNDATION_COPY: Record<string, { kicker: string; intro: string[]; meta?: string }> = {
  first_push_pull: {
    kicker: "Dành cho người mới hoàn toàn",
    intro: [
      "Nếu bạn là người làm công việc văn phòng, muốn cải thiện sức khỏe cho cuộc sống hàng ngày nhưng lại chưa có kinh nghiệm tập luyện, chưa từng hoặc rất ít vận động thì lịch tập này là dành cho bạn.",
      "Lộ trình nhập môn của TAPTOT sẽ giúp bạn làm quen với các động tác tập luyện đơn giản và xây nền cho thể lực bằng cách đi bộ nhẹ nhàng.",
    ],
  },
  basic_foundation: {
    kicker: "Sau khi đã quen form",
    intro: [
      "Sau khi đi qua lộ trình nhập môn hẳn là bạn đã chuẩn bị một nền tảng cơ bản để có thể tiếp tục tiến xa hơn không chỉ là duy trì lối sống lành mạnh.",
      "Vì vậy TAPTOT chuẩn bị giáo án và kiến thức giúp bạn phát triển sức mạnh nền tảng để bạn có thể chủ động hơn trong việc cải thiện vóc dáng.",
    ],
  },
  advanced_foundation: {
    kicker: "Hoàn thiện sức mạnh và thể lực",
    intro: [
      "Ở các lộ trình trước bạn hoàn toàn đã có đủ kiến thức để tự tin và cải thiện dáng của mình rồi.",
      "Vì thế TAPTOT tạo riêng lộ trình Nền tảng nâng cao này để dành cho những bạn có mong muốn tiếp tục trải nghiệm chuyên sâu hơn về các mảng tập luyện thể dục thể thao trong tương lai.",
    ],
  },
};

export type FoundationWizardIntro = {
  kicker: string;
  title: string;
  body: string;
  bullets: string[];
  note: string;
};

export const FOUNDATION_WIZARD_INTRO: Record<FamiliarizationPath, FoundationWizardIntro> = {
  first_push_pull: {
    kicker: "Dành cho người mới hoàn toàn",
    title: "Học cách tập trước khi tăng sức",
    body:
      "Giáo án này dành cho người chưa từng tập, hoặc chưa làm được một lần chống đẩy chuẩn hay kéo xà. Trong 60 ngày tại nhà, bạn học đẩy, kéo, squat và plank từ bài dễ trên tường, ghế và sàn — không cần bài test thể lực.",
    bullets: [
      "3 buổi mỗi tuần, khoảng 45 phút; ngày nghỉ có đi bộ nhẹ để khớp và gân kịp thích ứng.",
      "Bạn sẽ ra được form an toàn và một mốc kiểm tra cuối: chống đẩy, kéo (hoặc biến thể), squat, plank và đi/chạy 10 phút ở mức nhập môn.",
      "Cần tường, ghế hoặc bàn, và balo. Kéo người nằm từ tuần 3; xà siết bả vai từ tuần 5.",
    ],
    note:
      "Mốc ngày 59 là để xem bạn đã tới đâu, không phải cam kết ai cũng đạt đúng hạn. Tập đúng form, dừng khi đau nhói.",
  },
  basic_foundation: {
    kicker: "Sau khi đã quen form",
    title: "Biến bài cơ bản thành sức mạnh thật",
    body:
      "Giáo án này dành cho người đã qua nhập môn, hoặc đã làm được các biến thể sàn và muốn tăng lực thật — không chỉ “làm được động tác”. 60 ngày, 3 buổi mỗi tuần: chống đẩy sàn, kéo xà hoặc kéo người nằm, chuỗi sau và squat, tăng tải dần với balo 5–8 kg.",
    bullets: [
      "Bạn sẽ đẩy, kéo và squat chắc hơn, với số lần và tải ổn định hơn giai đoạn làm quen.",
      "Nền này mở cửa thử thách 100 ngày hoặc giáo án nền tảng nâng cao.",
      "Cần thể trọng, xà đơn, ghế và balo.",
    ],
    note: "Tăng tải khi form đã chắc. Dừng khi đau nhói.",
  },
  advanced_foundation: {
    kicker: "Hoàn thiện sức mạnh và thể lực",
    title: "Đủ khỏe để chơi thể thao và nhận thử thách dài",
    body:
      "Giáo án này dành cho người đã có sức mạnh nền và muốn lịch khó hơn, nhịp tăng tải rõ hơn. 60 ngày, 3 buổi mỗi tuần: sức mạnh tương đối, kiểm soát thân mình và tim mạch.",
    bullets: [
      "Bạn sẽ đẩy–kéo–chân–core và đi/chạy vững hơn, đủ nền để chơi thể thao hoặc nhận thử thách dài ngày.",
      "Từ đây có thể sang thử thách 100 ngày, hoặc chờ các nhánh chuyên sâu.",
      "Cần xà đơn, ghế, balo; dây band nếu có thì dùng thêm.",
    ],
    note: "Vẫn ưu tiên form trước số lần. Dừng khi đau nhói.",
  },
};

const CHALLENGE_COPY: Record<string, { kicker: string; intro: string[]; meta: string }> = {
  challenge_100: {
    kicker: "Thử thách sẵn sàng",
    meta: "100 ngày",
    intro: [
      "100 ngày thay đổi cơ thể: lịch dài, theo dõi số đo và sức mạnh, nhịp 3–4 buổi/tuần tùy bước sau.",
      "Phù hợp khi đã xây sức mạnh nền, hoặc muốn một mục tiêu rõ ràng hơn lịch làm quen.",
      "Bấm Tiếp tục để khai báo thể trạng và nhận lịch TAPTOT cho thử thách này.",
    ],
  },
  fitness_advanced: {
    kicker: "Thử thách sẵn sàng",
    meta: "12 tuần · 4–6 buổi",
    intro: [
      "Đầu vào chính là cửa ra nền tảng nâng cao — test camera 5 môn trước khi tạo lịch.",
      "12 tuần cố định, 4–6 buổi/tuần. Nam Đạt tốt nghiệp: 30 chống / 12 xà / 50 squat / plank 2:30 / 2,0 km. Nữ: 10 / 4 / 40 / 2:00 / 1,7 km.",
      "Test chính thức chỉ vào ngày cuối tuần 12 tại Kiểm tra thể lực.",
    ],
  },
};

const BRANCH_COPY: Record<
  string,
  { kicker: string; intro: string[]; benefits: { title: string; body: string }[] }
> = {
  gym: {
    kicker: "Chuyên sâu",
    intro: [
      "Gym là từ viết tắt của gymnasium, chỉ hoạt động rèn luyện thể chất và cơ bắp tại phòng tập sử dụng các trang thiết bị như máy chạy, tạ và giàn tập.",
    ],
    benefits: [
      {
        title: "Cải thiện vóc dáng",
        body: "Giúp tăng cơ, giảm mỡ và duy trì thân hình săn chắc.",
      },
      {
        title: "Tăng sức khỏe",
        body: "Nâng cao sức bền, sự dẻo dai và hạn chế các bệnh mạn tính.",
      },
      {
        title: "Giải tỏa căng thẳng",
        body: "Giúp tinh thần thoải mái và ngủ ngon hơn sau giờ làm việc.",
      },
    ],
  },
  calisthenic: {
    kicker: "Chuyên sâu",
    intro: [
      "Calisthenic là phương pháp rèn luyện bằng chính trọng lượng cơ thể — chống đẩy, kéo xà, plank, động tác tĩnh và động — ít phụ thuộc máy tập.",
    ],
    benefits: [
      {
        title: "Kiểm soát thân mình",
        body: "Học cách giữ thăng bằng, siết core và chuyển động gọn, đúng form.",
      },
      {
        title: "Tập mọi nơi",
        body: "Chỉ cần sàn, tường hoặc xà; phù hợp nhà, công viên hay khi đi xa.",
      },
      {
        title: "Sức mạnh chức năng",
        body: "Đẩy, kéo và chống đỡ cơ thể giúp sinh hoạt hàng ngày nhẹ hơn.",
      },
    ],
  },
  martial: {
    kicker: "Chuyên sâu",
    intro: [
      "Võ thuật là hệ thống kỹ năng đối kháng và tự vệ — từ võ Việt đến boxing, Muay, BJJ hay MMA — kết hợp thể lực, phản xạ và kỷ luật.",
    ],
    benefits: [
      {
        title: "Phản xạ và tự vệ",
        body: "Rèn tốc độ ra quyết định, khoảng cách và kỹ năng bảo vệ bản thân.",
      },
      {
        title: "Kỷ luật",
        body: "Nhịp tập rõ, tôn trọng đối tác và thói quen kiên trì từng buổi.",
      },
      {
        title: "Thể lực toàn thân",
        body: "Tim mạch, sức mạnh và dẻo dai được kéo cùng lúc trong sparring và kỹ thuật.",
      },
    ],
  },
  sport: {
    kicker: "Chuyên sâu",
    intro: [
      "Thể thao là hoạt động chơi hoặc thi đấu theo luật — bóng, vợt, bơi, chạy — lấy kỹ năng, đồng đội và niềm vui vận động làm trục.",
    ],
    benefits: [
      {
        title: "Tim mạch",
        body: "Di chuyển liên tục giúp bền hơi và hồi phục nhanh hơn trong đời sống.",
      },
      {
        title: "Phối hợp",
        body: "Mắt–tay–chân và không gian sân được luyện mỗi lần chơi.",
      },
      {
        title: "Tinh thần đồng đội",
        body: "Giao tiếp, tin đồng đội và giữ nhịp chung khi tập hoặc thi đấu.",
      },
    ],
  },
  other: {
    kicker: "Chuyên sâu",
    intro: [
      "Nhóm này gồm pilates, yoga và dance: tập trung linh hoạt, core, nhịp thở và kiểm soát chuyển động hơn là tạ nặng.",
    ],
    benefits: [
      {
        title: "Dẻo dai",
        body: "Mở biên độ khớp và giảm cứng người sau giờ ngồi lâu.",
      },
      {
        title: "Thăng bằng và core",
        body: "Ổn định thân mình, hỗ trợ lưng và tư thế hàng ngày.",
      },
      {
        title: "Giảm căng thẳng",
        body: "Hơi thở và nhịp chậm giúp đầu óc lắng sau công việc.",
      },
    ],
  },
  hybrid: {
    kicker: "Chuyên sâu",
    intro: [
      "Hybrid kết hợp sức mạnh, thể trọng và điều hòa trong cùng một lộ trình, thay vì chỉ theo một môn.",
    ],
    benefits: [
      {
        title: "Tố chất đủ mảng",
        body: "Vừa đẩy–kéo–chân, vừa bền hơi, không lệch một phía.",
      },
      {
        title: "Ít nhàm",
        body: "Đổi dạng bài giữa tuần nên dễ giữ thói quen lâu hơn.",
      },
      {
        title: "Linh hoạt mục tiêu",
        body: "Có thể nghiêng sức mạnh, dáng hoặc sức bền tùy giai đoạn.",
      },
    ],
  },
};

export function contentIdForSelection(selection: DirectionSelection): string {
  if (selection.kind === "foundation") return selection.path;
  if (selection.kind === "challenge") return selection.offer;
  if (selection.leaf) return `${selection.branch}-${selection.leaf}`;
  return selection.branch;
}

export function contentForSelection(
  selection: DirectionSelection,
  durationLabel?: string,
): DirectionNodeContent {
  const id = contentIdForSelection(selection);

  if (selection.kind === "foundation") {
    const node = FOUNDATION_NODES.find((item) => item.key === selection.path);
    const copy = FOUNDATION_COPY[selection.path];
    return {
      id,
      title: node?.label_vi ?? "Lộ trình nền",
      meta: durationLabel || copy?.meta || "",
      kicker: copy?.kicker ?? "Lộ trình nền",
      intro: copy?.intro ?? [node?.blurb_vi ?? ""],
      image: imageFor(id),
    };
  }

  if (selection.kind === "challenge") {
    const node = CHALLENGE_BRANCHES.find((item) => item.key === selection.offer);
    const copy = CHALLENGE_COPY[selection.offer];
    return {
      id,
      title: node?.label_vi ?? "Thử thách",
      meta: copy?.meta ?? "Thử thách",
      kicker: copy?.kicker ?? (node?.ready ? "Sẵn sàng" : "Sắp ra mắt"),
      intro: copy?.intro ?? [node?.label_vi ?? ""],
      image: imageFor(id),
    };
  }

  const branch = SPECIALIZATION_BRANCHES.find((item) => item.key === selection.branch);
  if (selection.leaf) {
    const leaf = branch?.leaves.find((item) => item.id === selection.leaf);
    const title = leaf?.label_vi ?? "Sắp ra mắt";
    return {
      id,
      title,
      meta: leaf?.label_en ?? branch?.label_vi ?? "Chuyên sâu",
      kicker: "Chuyên sâu",
      intro: [
        `${title} thuộc nhánh ${branch?.label_vi ?? "chuyên sâu"}.`,
      ],
      image: imageFor(id),
    };
  }

  const copy = BRANCH_COPY[selection.branch];
  return {
    id,
    title: branch?.label_vi ?? "Chuyên sâu",
    meta: "Nhánh chuyên sâu",
    kicker: copy?.kicker ?? "Sắp ra mắt",
    intro: copy?.intro ?? [DIRECTION_COMING_SOON],
    benefits: copy?.benefits,
    image: imageFor(id),
  };
}
