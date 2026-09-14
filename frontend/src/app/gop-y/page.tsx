import { redirect } from "next/navigation";

export const metadata = { title: "Góp ý — TAPTOT" };

/** Góp ý chỉ nằm trong khu vực tài khoản (panel phải). */
export default function FeedbackRedirectPage() {
  redirect("/tai-khoan/gop-y");
}
