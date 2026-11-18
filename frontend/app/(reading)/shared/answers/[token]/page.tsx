import type { Metadata } from "next";

import { SharedAnswerScreen } from "@/components/learn/SharedScreens";

export const metadata: Metadata = { title: "Shared answer", robots: { index: false, follow: false } };

export default async function SharedAnswerPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <SharedAnswerScreen token={token} />;
}
