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
  benefits?: { title: string; body: string }[];
};

const FOUNDATION_COPY: Record<string, { kicker: string; intro: string[]; meta?: string }> = {
  first_push_pull: {
    kicker: "Dành cho người mới hoàn toàn",
    intro: [
      "Nếu bạn là người làm công việc văn phòng, muốn cải thiện sức khỏe cho cuộc sống hàng ngày nhưng lại chưa có kinh nghiệm tập luyện, chưa từng hoặc rất ít vận động thì lịch tập này là dành cho bạn.",
      "Lộ trình nhập môn của TAPTOT sẽ giúp bạn làm quen với các động tác tập luyện đơn giản và xây nền cho thể lực bằng cách đi bộ nhẹ nhàng.",
    ],
  },
};

export type FoundationWizardIntro = {
  kicker: string;
  title: string;
  sections: { label: string; body: string }[];
};

export const FOUNDATION_WIZARD_INTRO: Record<FamiliarizationPath, FoundationWizardIntro> = {
  first_push_pull: {
    kicker: "Dành cho người mới hoàn toàn",
    title:
      "Học cách tập trước khi tham gia thử thách hoặc tham gia các giáo trình tập luyện khác của TAPTOT",
    sections: [
      {
        label: "Đối tượng",
        body:
          "Giáo án này dành cho người chưa từng tập, hoặc chưa làm được một lần chống đẩy chuẩn hay kéo xà. Trong 60 ngày tại nhà, bạn làm quen các bài tập đẩy, kéo, squat và plank từ bài dễ trên tường, ghế và sàn.",
      },
      {
        label: "Thời lượng",
        body:
          "3 buổi mỗi tuần, khoảng 30-45 phút mỗi buổi; ngày nghỉ có thể đi bộ nhẹ để khớp và gân kịp thích ứng.",
      },
      {
        label: "Đầu ra",
        body:
          "Khóa này sẽ giúp bạn có thể thực hiện các động tác như chống đẩy, kéo xà nằm, squat và plank đủ để làm nền tảng cho các thử thách, khóa tập luyện tiếp theo của TAPTOT.",
      },
    ],
  },
};

const CHALLENGE_COPY: Record<string, { kicker: string; intro: string[]; meta: string }> = {
  challenge_100: {
    kicker: "Thử thách sẵn sàng",
    meta: "",
    intro: [
      "TAPTOT xây dựng lộ trình 100 ngày thay đổi này nhắm mục đích cung cấp cho mọi người một lộ trình cá nhân hóa, đa dạng hóa bài tập theo dụng cụ tập luyện.",
      "Lộ trình sẽ cung cấp những kiến thức cơ bản về tập luyện và chế độ dinh dưỡng giúp người tập sau lộ trình có thể tự đặt mục tiêu tăng cân giảm cân đơn giản.",
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
        body: "Học cách giữ thăng bằng, cảm nhận chuyển động cơ thể.",
      },
      {
        title: "Tập mọi nơi",
        body: "Tập luyện mọi địa điểm và không cần quá nhiều dụng cụ.",
      },
      {
        title: "Sức mạnh chức năng",
        body: "Cải thiện cơ bắp sức khỏe giúp sinh hoạt hàng ngày nhẹ nhàng hơn.",
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
      "Những nhánh tập luyện như thể thao, võ thuật, hybrid, pilates, yoga,... — các hướng TAPTOT sẽ mở trong tương lai.",
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
  };
}
