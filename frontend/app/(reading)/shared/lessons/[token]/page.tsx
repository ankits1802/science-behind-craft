import type { Metadata } from "next";

import { SharedLessonScreen } from "@/components/learn/SharedScreens";

export const metadata: Metadata = { title: "Shared lesson", robots: { index: false, follow: false } };

export default async function SharedLessonPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <SharedLessonScreen token={token} />;
}
