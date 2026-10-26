import {
  LEGAL_BRAND,
  LEGAL_CONTACT_EMAIL,
  TERMS_HREF,
  type LegalSection,
} from "@/lib/legalMeta";

export { TERMS_HREF };
export type { LegalSection };

export const TERMS_TITLE = "Điều khoản sử dụng và miễn trừ trách nhiệm y tế";
export const TERMS_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 25 tháng 10 năm 2026.";
export const TERMS_VERSION = "2026-10-25";

export const TERMS_INTRO =
  `Chào mừng bạn đến với ${LEGAL_BRAND} (sau đây gọi chung là "Hệ thống" hoặc "Chúng tôi"). Hệ thống cung cấp công cụ tạo lịch tập, gợi ý chế độ dinh dưỡng, bài viết kiến thức thể hình, kiểm tra thể lực và gian hàng phụ kiện thể thao do chính Chúng tôi bán.`;

export const TERMS_AGREEMENT =
  "Bằng việc truy cập, tạo tài khoản, điền bảng khảo sát thể trạng, đặt mua phụ kiện hoặc sử dụng lịch tập, thực đơn và nội dung khác do Hệ thống xuất ra, bạn xác nhận rằng bạn đã đọc, hiểu và đồng ý các điều khoản này cùng Chính sách bảo mật. Khi đặt hàng phụ kiện, bạn cũng đồng ý Chính sách bán hàng và Chính sách thanh toán, hoàn tiền.";

export const TERMS_AGE_CHECKBOX =
  "Tôi xác nhận từ đủ 18 tuổi (hoặc từ đủ 16 tuổi đã có sự đồng ý của người giám hộ), hoàn toàn đủ điều kiện sức khỏe để vận động.";

export const TERMS_AGREE_CHECKBOX =
  "Tôi đã đọc, hiểu và đồng ý với Điều khoản dịch vụ cùng Chính sách bảo mật của hệ thống.";

export const TERMS_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Giới hạn độ tuổi và năng lực hành vi dân sự",
    paragraphs: [
      "Hệ thống chỉ phục vụ người dùng từ đủ 18 tuổi trở lên có đầy đủ năng lực hành vi dân sự theo quy định của pháp luật Việt Nam.",
      "Trường hợp người dùng từ đủ 16 tuổi đến dưới 18 tuổi, việc đăng ký và sử dụng dịch vụ cần có sự đồng ý của cha, mẹ hoặc người giám hộ hợp pháp. Ô xác nhận trên Hệ thống là lời cam kết của người dùng, không thay thế văn bản đồng ý của người giám hộ. Chúng tôi có thể từ chối cung cấp dịch vụ nếu không đủ căn cứ về sự đồng ý này.",
      "Hệ thống từ chối cung cấp dịch vụ cho người dưới 16 tuổi. Chúng tôi không chịu trách nhiệm đối với việc cố tình khai sai độ tuổi, trong phạm vi pháp luật cho phép.",
    ],
  },
  {
    id: "2",
    title: "Bản chất dịch vụ — không thay thế chẩn đoán y khoa",
    paragraphs: [
      "Lịch tập, thực đơn, chỉ số calo, tỷ lệ dinh dưỡng và bài viết kiến thức được tạo từ quy tắc nội bộ và dữ liệu tham khảo cho người có thể trạng thông thường. Kết quả mang tính tham khảo cho việc tự tập luyện và tự ăn uống.",
      "Thông tin này không phải lời khuyên y khoa, phác đồ điều trị, đơn thuốc hay chẩn đoán bệnh. Hệ thống không phải cơ sở khám chữa bệnh và không phải phòng tập hay cơ sở huấn luyện tại chỗ.",
      "Chúng tôi không cam kết bạn sẽ giảm một số kilogram nhất định, đạt một chỉ số cơ thể nhất định, hoặc có kết quả giống người khác trong một khoảng thời gian cố định.",
      "Trước khi tập cường độ cao hoặc đổi chế độ ăn, bạn tự tham vấn bác sĩ nếu có bệnh tim mạch, huyết áp, hô hấp, tiểu đường, thoát vị đĩa đệm, chấn thương cơ xương khớp, hoặc đang mang thai hay hậu sản.",
    ],
  },
  {
    id: "3",
    title: "Tự nguyện chấp nhận rủi ro thể chất",
    paragraphs: [
      "Tập luyện, nhất là tập tạ và vận động kháng lực, có rủi ro cố hữu như căng cơ, bong gân, rách cơ, chấn thương khớp, gãy xương, kiệt sức, choáng hoặc sự cố tim mạch.",
      "Bạn tự chọn bài tập, tự đánh giá sức chịu đựng của mình và tự chịu trách nhiệm về kỹ thuật, mức tạ, khởi động và môi trường tập khi không có người hướng dẫn đứng cạnh.",
      "Hãy dừng bài tập nếu đau bất thường, tức ngực, khó thở, chóng mặt hoặc buồn nôn, và tìm trợ giúp y tế khi cần.",
    ],
  },
  {
    id: "4",
    title: "Giới hạn trách nhiệm trong phạm vi pháp luật cho phép",
    paragraphs: [
      "Trong phạm vi pháp luật Việt Nam cho phép, Chúng tôi không bồi thường thiệt hại phát sinh từ việc bạn tự tập theo lịch, tự áp dụng thực đơn, tập sai kỹ thuật, dùng mức tạ quá sức, tập ở nơi thiếu an toàn, hoặc khai sai tuổi, cân nặng, chiều cao hay tình trạng sức khỏe khiến lịch không còn phù hợp.",
      "Phụ kiện bị hỏng vì dùng sai hướng dẫn, vượt tải trọng an toàn hoặc hao mòn tự nhiên cũng thuộc phạm vi này. Hàng lỗi do nhà sản xuất, giao sai hàng hoặc không đúng mô tả được xử lý theo Chính sách bán hàng.",
      "Các giới hạn trên không loại trừ trách nhiệm bắt buộc của bên bán theo Luật Bảo vệ quyền lợi người tiêu dùng, không xóa trách nhiệm đối với hàng hóa khuyết tật, hàng không đúng mô tả hoặc thiệt hại do lỗi của Chúng tôi, và không hạn chế quyền khiếu nại, yêu cầu cơ quan nhà nước hoặc khởi kiện của bạn.",
    ],
  },
  {
    id: "5",
    title: "Độ chính xác nội dung và hình minh họa",
    paragraphs: [
      "Lịch tập và thực đơn được lập bằng quy tắc và dữ liệu có sẵn của Hệ thống. Nội dung có thể chưa phù hợp với từng người. Bạn tự quyết định có áp dụng hay không.",
      "Chỉ số calo và thành phần dinh dưỡng lấy từ kho tham khảo, có thể lệch so với món bạn nấu hoặc nguồn khác.",
      "Ảnh trong kho thực phẩm, món ăn và lịch tập chủ yếu để minh họa. Một số ảnh được tạo bằng công cụ tạo ảnh và không phải ảnh chụp món thật. Chỉ số dinh dưỡng không phụ thuộc vào hình minh họa.",
    ],
  },
  {
    id: "6",
    title: "Tài khoản, lịch và liên kết chia sẻ",
    paragraphs: [
      "Bạn giữ bí mật thông tin đăng nhập và chịu trách nhiệm về hoạt động dưới tài khoản của mình.",
      "Lịch tập bị xóa sau 4 tháng dương lịch kể từ ngày tạo, kể cả khi đã gắn tài khoản. Sau thời điểm đó, nội dung có thể không còn xem được. Lịch mẫu công khai được Hệ thống ghim có thể không áp dụng thời hạn này.",
      "Mỗi lịch có thể có liên kết chia sẻ. Ai có liên kết đều có thể xem nội dung lịch. Chỉ gửi liên kết cho người bạn muốn cho xem. Chúng tôi không chịu trách nhiệm nếu bạn tự phát tán liên kết.",
    ],
  },
  {
    id: "7",
    title: "Hành vi bị cấm",
    paragraphs: ["Khi dùng Hệ thống, bạn không:"],
    bullets: [
      "Thu thập, sao chép hàng loạt hoặc khai thác trái phép kho bài tập, thực phẩm, kiến thức hay API.",
      "Phá hoại, làm quá tải, xâm nhập trái phép hoặc can thiệp vào hoạt động của Hệ thống.",
      "Gửi spam, nội dung trái pháp luật, hoặc gian lận độ tuổi, mã ưu đãi, mã redeem hay kết quả thử thách.",
      "Bán lại hoặc đưa lịch tập, thực đơn của người khác ra thị trường như sản phẩm của mình khi chưa được phép.",
    ],
  },
  {
    id: "8",
    title: "Liên hệ huấn luyện viên",
    paragraphs: [
      "Form liên hệ huấn luyện viên chỉ ghi nhận yêu cầu của bạn để Chúng tôi phản hồi. Việc gửi form không tạo hợp đồng huấn luyện, quan hệ lao động, đại diện hay bảo lãnh giữa bạn, TAPTOT và bất kỳ huấn luyện viên nào.",
      "Hệ thống hiện không phải sàn để huấn luyện viên mở gian hàng hay tự bán dịch vụ. Chúng tôi không bảo đảm chứng chỉ, chất lượng buổi tập hay kết quả của người mà bạn có thể liên hệ ngoài Hệ thống.",
    ],
  },
  {
    id: "9",
    title: "Sở hữu trí tuệ và quyền dùng lịch cá nhân",
    paragraphs: [
      "Giao diện, quy tắc tạo lịch, kho bài tập, kho thực phẩm, bài viết và thương hiệu thuộc Chúng tôi hoặc bên đã cấp phép, trừ khi có ghi chú khác.",
      "Lịch tập và thực đơn tạo cho bạn chỉ để bạn tự dùng. Bạn không được sao chép, bán lại hoặc biến giáo án đó thành sản phẩm thương mại cho người khác tập theo.",
      "Chúng tôi không chịu trách nhiệm với bên thứ ba xem hoặc sao chép nội dung qua liên kết mà bạn đã chia sẻ.",
    ],
  },
  {
    id: "10",
    title: "Giới hạn trách nhiệm đối với giao dịch",
    paragraphs: [
      "Ngoài mục sức khỏe ở trên, trong phạm vi pháp luật cho phép, tổng số tiền Chúng tôi bồi thường cho một khiếu nại phát sinh từ việc dùng dịch vụ không vượt quá số tiền bạn đã trả cho Chúng tôi trong 12 tháng liền trước sự việc. Nếu bạn chưa trả khoản nào, mức này bằng không.",
      "Mức trần này không áp dụng cho nghĩa vụ bắt buộc theo luật bảo vệ người tiêu dùng, hàng khuyết tật, hàng không đúng mô tả, hoặc thiệt hại do lỗi cố ý của Chúng tôi. Điều khoản này không cấm bạn khiếu nại hoặc khởi kiện.",
      "Thiệt hại gián tiếp, mất lợi nhuận hoặc mất dữ liệu chỉ bị loại trừ trong phần pháp luật cho phép loại trừ.",
    ],
  },
  {
    id: "11",
    title: "Chấm dứt và thay đổi điều khoản",
    paragraphs: [
      "Chúng tôi có thể tạm ngừng hoặc chấm dứt quyền truy cập nếu bạn vi phạm điều khoản, gây rủi ro bảo mật, hoặc khi cơ quan nhà nước yêu cầu.",
      `Chúng tôi có thể sửa điều khoản. Phiên bản hiện tại: ${TERMS_VERSION}. Ngày sửa ghi ở đầu trang. Bạn tiếp tục dùng dịch vụ sau khi bản mới có hiệu lực nghĩa là bạn đã biết nội dung mới, trừ khi pháp luật yêu cầu hình thức đồng ý khác.`,
      `Thắc mắc về điều khoản gửi về ${LEGAL_CONTACT_EMAIL}. Cách gửi khiếu nại nằm ở trang Khiếu nại.`,
    ],
  },
  {
    id: "12",
    title: "Luật áp dụng và tranh chấp",
    paragraphs: [
      "Điều khoản này được hiểu theo pháp luật nước Cộng hòa Xã hội Chủ nghĩa Việt Nam.",
      "Tranh chấp được thương lượng trước. Nếu không thỏa thuận được, vụ việc đưa ra Tòa án Việt Nam có thẩm quyền theo luật. Khi trụ sở đăng ký chưa được điền trên trang Thông tin đơn vị, thẩm quyền tòa án xác định theo quy định pháp luật, không theo một địa chỉ giả định.",
    ],
  },
];
