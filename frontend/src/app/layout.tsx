import type { Metadata } from "next";
import { Lora, Nunito_Sans } from "next/font/google";
import "./globals.css";
import AppShell from "@/components/AppShell";
import { BRAND_NAME, BRAND_SLOGAN } from "@/lib/brand";

const nunito = Nunito_Sans({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-nunito",
  display: "swap",
});

const lora = Lora({
  subsets: ["latin", "vietnamese"],
  weight: ["500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-lora",
  display: "swap",
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
    <html lang="vi" className={`${nunito.variable} ${lora.variable} ${nunito.className} antialiased`} suppressHydrationWarning>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
