export const TERMS_HREF = "/dieu-khoan";
export const TERMS_TITLE = "Điều khoản sử dụng và miễn trừ trách nhiệm y tế";
export const TERMS_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 08 tháng 09 năm 2026.";
export const TERMS_VERSION = "2026-09-08";

export const TERMS_INTRO =
  'Chào mừng bạn đến với nền tảng cung cấp công cụ tạo lịch tập, gợi ý chế độ dinh dưỡng và phân phối phụ kiện thể thao của chúng tôi (sau đây gọi chung là "Hệ thống" hoặc "Chúng tôi").';

export const TERMS_AGREEMENT =
  "Bằng việc truy cập, tạo tài khoản, điền bảng khảo sát thể trạng, thực hiện thanh toán hoặc sử dụng bất kỳ nội dung, lịch tập, thực đơn nào do Hệ thống xuất ra, bạn xác nhận rằng bạn đã đọc, hiểu rõ và hoàn toàn đồng ý tuân thủ toàn bộ các điều khoản dưới đây.";

export const TERMS_AGE_CHECKBOX =
  "Tôi xác nhận từ đủ 18 tuổi (hoặc từ đủ 16 tuổi đã có sự đồng ý của người giám hộ), hoàn toàn đủ điều kiện sức khỏe để vận động.";

export const TERMS_AGREE_CHECKBOX =
  "Tôi đã đọc, hiểu và đồng ý với Điều khoản dịch vụ và Miễn trừ trách nhiệm y tế của hệ thống.";

export const TERMS_SECTIONS: {
  id: string;
  title: string;
  paragraphs: string[];
  bullets?: string[];
}[] = [
  {
    id: "1",
    title: "Giới hạn độ tuổi và Năng lực hành vi dân sự",
    paragraphs: [
      "Hệ thống chỉ phục vụ người dùng từ đủ 18 tuổi trở lên có đầy đủ năng lực hành vi dân sự theo quy định của pháp luật Việt Nam.",
      "Trường hợp người dùng từ đủ 16 tuổi đến dưới 18 tuổi, việc đăng ký và sử dụng dịch vụ bắt buộc phải có sự đồng ý, giám sát và bảo lãnh của cha, mẹ hoặc người giám hộ hợp pháp. Bằng việc bấm xác nhận, người dùng cam kết đã nhận được sự đồng thuận này.",
      "Hệ thống từ chối cung cấp dịch vụ và không chịu trách nhiệm đối với bất kỳ cá nhân nào dưới 16 tuổi cố tình gian lận thông tin độ tuổi để sử dụng nền tảng.",
    ],
  },
  {
    id: "2",
    title: "Bản chất dịch vụ – Không thay thế chẩn đoán y khoa",
    paragraphs: [
      "Tính chất tham khảo: Toàn bộ lịch tập luyện, thực đơn ăn uống, chỉ số calo, tỷ lệ dinh dưỡng (Macronutrients) và các hướng dẫn do Hệ thống tự động khởi tạo đều dựa trên các thuật toán tính toán và dữ liệu tham khảo phổ quát cho người có thể trạng bình thường.",
      "Không phải lời khuyên y tế: Thông tin do Hệ thống cung cấp KHÔNG PHẢI là lời khuyên y khoa, phác đồ điều trị, đơn thuốc hay chẩn đoán bệnh lý. Hệ thống không đóng vai trò là cơ sở khám chữa bệnh hay chuyên gia y tế.",
      "Khuyến cáo kiểm tra sức khỏe: Trước khi bắt đầu bất kỳ chương trình tập luyện cường độ cao hoặc thay đổi chế độ dinh dưỡng nào, bạn có trách nhiệm tự đi khám hoặc tham vấn ý kiến của bác sĩ chuyên khoa, đặc biệt nếu bạn có tiền sử hoặc đang mắc các bệnh lý liên quan đến: tim mạch, huyết áp, hô hấp, tiểu đường, thoát vị đĩa đệm, tổn thương cơ xương khớp hoặc đang trong giai đoạn thai kỳ/hậu sản.",
    ],
  },
  {
    id: "3",
    title: "Tự nguyện chấp nhận rủi ro thể chất",
    paragraphs: [
      "Bạn thừa nhận rằng mọi hoạt động thể dục thể thao, đặc biệt là tập tạ (Resistance Training) và vận động kháng lực, luôn đi kèm những rủi ro cố hữu bao gồm nhưng không giới hạn ở: căng cơ, bong gân, rách cơ, chấn thương khớp, gãy xương, kiệt sức, choáng ngất hoặc các sự cố tim mạch nghiêm trọng khác.",
      "Bạn hoàn toàn tự nguyện lựa chọn áp dụng các bài tập và tự đánh giá ngưỡng chịu đựng, giới hạn sức khỏe của bản thân tại từng thời điểm tập luyện.",
      "Bạn có trách nhiệm dừng ngay lập tức mọi bài tập nếu cảm thấy đau nhức bất thường, tức ngực, khó thở, chóng mặt hoặc buồn nôn, và kịp thời tìm kiếm sự trợ giúp y tế cần thiết.",
    ],
  },
  {
    id: "4",
    title: "Miễn trừ trách nhiệm pháp lý toàn diện",
    paragraphs: [
      "Trong phạm vi tối đa mà pháp luật cho phép, Chúng tôi, các sáng lập viên, nhân sự vận hành, cộng tác viên chuyên môn và các bên liên kết được miễn trừ hoàn toàn khỏi mọi trách nhiệm bồi thường thiệt hại (dù trực tiếp hay gián tiếp) phát sinh từ:",
    ],
    bullets: [
      "Bất kỳ chấn thương thể xác, suy giảm sức khỏe, tổn thất tinh thần hay tai nạn nào xảy ra trong quá trình bạn tự thực hiện theo lịch tập hoặc chế độ dinh dưỡng do Hệ thống gợi ý.",
      "Việc bạn thực hiện sai kỹ thuật động tác, sử dụng mức tạ vượt quá khả năng kiểm soát, không khởi động kỹ hoặc tập luyện trong môi trường thiếu an toàn mà không có sự giám sát trực tiếp của huấn luyện viên có mặt tại chỗ.",
      "Việc bạn cố ý cung cấp thông tin sai lệch về tình trạng sức khỏe, bệnh nền, cân nặng, chiều cao hoặc độ tuổi trong bảng khảo sát ban đầu dẫn đến việc Hệ thống xuất lịch tập không phù hợp.",
      "Các sản phẩm phụ kiện tập luyện bị sử dụng sai hướng dẫn kỹ thuật hoặc hao mòn tự nhiên do vượt tải trọng an toàn.",
    ],
  },
  {
    id: "5",
    title: "Cá nhân hóa và Bản quyền nội dung",
    paragraphs: [
      "Mỗi bộ lịch tập và thực đơn được tạo ra gắn liền với định danh (Họ tên, Số điện thoại/Email) của người dùng đăng ký. Tài liệu này chỉ phục vụ mục đích sử dụng cá nhân của chính bạn.",
      "Nghiêm cấm mọi hành vi sao chép, thương mại hóa, bán lại hoặc chia sẻ giáo án này cho bên thứ ba tập luyện theo. Hệ thống không chịu bất kỳ trách nhiệm nào đối với những bên thứ ba tiếp cận và sử dụng tài liệu không chính chủ.",
    ],
  },
  {
    id: "6",
    title: "Luật áp dụng và Giải quyết tranh chấp",
    paragraphs: [
      "Các điều khoản này được điều chỉnh và giải thích theo quy định của pháp luật nước Cộng hòa Xã hội Chủ nghĩa Việt Nam.",
      "Mọi tranh chấp phát sinh từ hoặc liên quan đến việc sử dụng dịch vụ trước hết sẽ được giải quyết thông qua thương lượng thiện chí giữa các bên. Trường hợp không đạt được thỏa thuận, vụ việc sẽ được đưa ra Tòa án có thẩm quyền tại nơi Bên cung cấp dịch vụ đặt trụ sở kinh doanh để giải quyết.",
    ],
  },
];
