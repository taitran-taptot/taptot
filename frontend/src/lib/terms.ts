import {
  LEGAL_BRAND,
  LEGAL_CONTACT_EMAIL,
  TERMS_HREF,
  type LegalSection,
} from "@/lib/legalMeta";

export { TERMS_HREF };
export type { LegalSection };

export const TERMS_TITLE = "Điều khoản sử dụng và miễn trừ trách nhiệm y tế";
export const TERMS_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 23 tháng 09 năm 2026.";
export const TERMS_VERSION = "2026-09-23-legal";

export const TERMS_INTRO =
  `Chào mừng bạn đến với nền tảng cung cấp công cụ tạo lịch tập, gợi ý chế độ dinh dưỡng và phân phối phụ kiện thể thao của ${LEGAL_BRAND} (sau đây gọi chung là "Hệ thống" hoặc "Chúng tôi").`;

export const TERMS_AGREEMENT =
  "Bằng việc truy cập, tạo tài khoản, điền bảng khảo sát thể trạng, thực hiện thanh toán hoặc sử dụng bất kỳ nội dung, lịch tập, thực đơn nào do Hệ thống xuất ra, bạn xác nhận rằng bạn đã đọc, hiểu rõ và hoàn toàn đồng ý tuân thủ toàn bộ các điều khoản dưới đây cũng như Chính sách bảo mật của Hệ thống.";

export const TERMS_AGE_CHECKBOX =
  "Tôi xác nhận từ đủ 18 tuổi (hoặc từ đủ 16 tuổi đã có sự đồng ý của người giám hộ), hoàn toàn đủ điều kiện sức khỏe để vận động.";

export const TERMS_AGREE_CHECKBOX =
  "Tôi đã đọc, hiểu và đồng ý với Điều khoản dịch vụ, Miễn trừ trách nhiệm y tế và Chính sách bảo mật của hệ thống.";

export const TERMS_SECTIONS: LegalSection[] = [
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
    title: "Miễn trừ trách nhiệm pháp lý (trong phạm vi pháp luật cho phép)",
    paragraphs: [
      "Trong phạm vi tối đa mà pháp luật Việt Nam cho phép, Chúng tôi, các sáng lập viên, nhân sự vận hành, cộng tác viên chuyên môn và các bên liên kết được miễn trừ khỏi trách nhiệm bồi thường thiệt hại (dù trực tiếp hay gián tiếp) phát sinh từ:",
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
    title: "Dịch vụ AI và độ chính xác nội dung",
    paragraphs: [
      "Hệ thống có thể dùng thuật toán và dịch vụ AI (bao gồm nhà cung cấp bên thứ ba) để gợi ý bài tập, thực đơn, lời khuyên hoặc nội dung liên quan. Kết quả mang tính tham khảo, có thể sai sót hoặc không phù hợp với từng cá nhân.",
      "Chỉ số calo, macro và dữ liệu dinh dưỡng lấy từ catalog/tham khảo; có thể lệch so với thực tế chế biến hoặc nguồn khác. Bạn tự chịu trách nhiệm khi áp dụng.",
      "Ảnh trong kho thực phẩm, món ăn và lịch tập chủ yếu mang tính minh họa; nhiều ảnh được tạo bằng công cụ AI và không phải ảnh chụp món thật. Chỉ số dinh dưỡng không phụ thuộc vào hình ảnh minh họa.",
    ],
  },
  {
    id: "6",
    title: "Tài khoản, lịch khách và liên kết chia sẻ",
    paragraphs: [
      "Bạn chịu trách nhiệm bảo mật thông tin đăng nhập và mọi hoạt động diễn ra dưới tài khoản của mình.",
      "Mọi lịch tập bị xóa tự động sau khoảng 110 ngày kể từ khi tạo, kể cả khi đã đăng nhập hoặc đã lưu vào tài khoản. Sau khi hết hạn, nội dung có thể không còn truy cập được.",
      "Mỗi lịch có thể có liên kết chia sẻ công khai (ví dụ đường dẫn dạng /lich/…). Bất kỳ ai có liên kết đều có thể xem nội dung lịch. Bạn không nên chia sẻ liên kết nếu không muốn người khác xem dữ liệu trên lịch đó. Hệ thống không chịu trách nhiệm khi liên kết bị lan truyền ngoài ý muốn của bạn.",
    ],
  },
  {
    id: "7",
    title: "Hành vi bị cấm",
    paragraphs: [
      "Khi sử dụng Hệ thống, bạn cam kết không:",
    ],
    bullets: [
      "Thu thập, sao chép hàng loạt hoặc khai thác trái phép kho bài tập, thực phẩm, kiến thức hay API.",
      "Phá hoại, làm quá tải, xâm nhập trái phép hoặc can thiệp vào hoạt động của Hệ thống.",
      "Gửi spam, nội dung bất hợp pháp, hoặc gian lận thông tin độ tuổi, mã ưu đãi, mã redeem hay kết quả thử thách.",
      "Sử dụng dịch vụ vào mục đích thương mại hóa lại lịch tập/thực đơn của người khác mà không được phép.",
    ],
  },
  {
    id: "8",
    title: "Huấn luyện viên và nội dung bên thứ ba",
    paragraphs: [
      "Một số hồ sơ huấn luyện viên trên nền tảng mang tính minh họa hoặc giới thiệu. Việc bạn gửi form liên hệ HLV không tự động tạo quan hệ lao động, đại diện hay bảo lãnh giữa TAPTOT và huấn luyện viên.",
      "Chúng tôi không đảm bảo chất lượng, chứng chỉ hay kết quả huấn luyện của bên thứ ba. Mọi thỏa thuận dịch vụ trực tiếp với HLV do bạn và HLV tự chịu trách nhiệm.",
    ],
  },
  {
    id: "9",
    title: "Sở hữu trí tuệ và quyền sử dụng lịch cá nhân",
    paragraphs: [
      "Giao diện, thuật toán, catalog bài tập/thực phẩm, kiến thức và thương hiệu thuộc quyền của Chúng tôi hoặc bên cấp phép, trừ khi có ghi chú khác.",
      "Mỗi bộ lịch tập và thực đơn được tạo gắn với tài khoản hoặc phiên của bạn phục vụ mục đích sử dụng cá nhân. Bạn không được sao chép, bán lại hoặc thương mại hóa giáo án cho bên thứ ba tập theo như sản phẩm của mình.",
      "Hệ thống không chịu trách nhiệm đối với bên thứ ba tiếp cận và sử dụng tài liệu không chính chủ qua liên kết chia sẻ hoặc sao chép trái phép.",
    ],
  },
  {
    id: "10",
    title: "Giới hạn trách nhiệm thương mại",
    paragraphs: [
      "Ngoài miễn trừ liên quan sức khỏe nêu trên, trong phạm vi pháp luật cho phép, tổng trách nhiệm bồi thường của Chúng tôi đối với mọi khiếu nại phát sinh từ hoặc liên quan đến việc sử dụng dịch vụ (không bao gồm nghĩa vụ bắt buộc theo luật bảo vệ người tiêu dùng) không vượt quá tổng số tiền bạn đã thực tế thanh toán cho Chúng tôi trong mười hai (12) tháng liền trước sự kiện phát sinh khiếu nại, hoặc bằng không (0) nếu bạn chưa thanh toán khoản nào.",
      "Chúng tôi không chịu trách nhiệm đối với thiệt hại gián tiếp, mất lợi nhuận, mất dữ liệu hoặc thiệt hại mang tính hệ quả trong phạm vi pháp luật cho phép loại trừ.",
    ],
  },
  {
    id: "11",
    title: "Chấm dứt và thay đổi điều khoản",
    paragraphs: [
      "Chúng tôi có thể tạm ngưng hoặc chấm dứt quyền truy cập nếu bạn vi phạm điều khoản, gây rủi ro bảo mật hoặc theo yêu cầu pháp lý.",
      `Chúng tôi có thể cập nhật điều khoản theo thời gian. Phiên bản hiện hành được ghi nhận bằng mã phiên bản (hiện tại: ${TERMS_VERSION}) và ngày cập nhật trên trang này. Việc bạn tiếp tục sử dụng sau khi điều khoản mới có hiệu lực đồng nghĩa với việc chấp nhận bản cập nhật, trừ khi pháp luật yêu cầu hình thức đồng ý khác.`,
      `Mọi thắc mắc về điều khoản xin gửi về ${LEGAL_CONTACT_EMAIL}.`,
    ],
  },
  {
    id: "12",
    title: "Luật áp dụng và Giải quyết tranh chấp",
    paragraphs: [
      "Các điều khoản này được điều chỉnh và giải thích theo quy định của pháp luật nước Cộng hòa Xã hội Chủ nghĩa Việt Nam.",
      "Mọi tranh chấp phát sinh từ hoặc liên quan đến việc sử dụng dịch vụ trước hết sẽ được giải quyết thông qua thương lượng thiện chí giữa các bên. Trường hợp không đạt được thỏa thuận, vụ việc sẽ được đưa ra Tòa án có thẩm quyền tại nơi Bên cung cấp dịch vụ đặt trụ sở kinh doanh để giải quyết.",
    ],
  },
];
