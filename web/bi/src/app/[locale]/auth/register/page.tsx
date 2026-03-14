import { redirect } from "next/navigation";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function RegisterV2({ params }: Props) {
  const { locale } = await params;
  redirect(`/${locale}/auth/login`);
}
