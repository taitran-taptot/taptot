import BankTransferPayView from "@/components/BankTransferPayView";
import OrderSuccessView from "@/components/OrderSuccessView";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ "ket-qua"?: string }>;
}) {
  const params = await searchParams;
  if (params["ket-qua"] === "thanh-toan") return <BankTransferPayView />;
  return <OrderSuccessView />;
}
