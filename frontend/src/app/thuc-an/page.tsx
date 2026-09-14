import FoodLibrary from "@/components/FoodLibrary";

export const metadata = {
  title: "Thư viện thực phẩm Việt — TAPTOT",
  description:
    "Thịt, rau, cơm, trứng — tra calo theo 100g và theo khẩu phần quen (1 chén, 1 quả).",
};

export default function FoodsPage() {
  return <FoodLibrary cookBase="/cach-nau" />;
}
