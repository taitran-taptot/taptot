import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";
import AppShell from "@/components/AppShell";
import { BRAND_NAME, BRAND_SLOGAN } from "@/lib/brand";

const beVietnam = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: `${BRAND_NAME} — ${BRAND_SLOGAN}`,
  description:
    `${BRAND_SLOGAN} Thử thách 100 ngày (14 tuần, 3 pha) hoặc tạo lịch 1 tháng. Lịch tập vừa sức, gợi ý ăn từ nguyên liệu tươi: thịt, rau, cơm, khoai.`,
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className={`${beVietnam.className} antialiased`} suppressHydrationWarning>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
