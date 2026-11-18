import type { Metadata } from "next";

import { AppearancePreview } from "@/app/design/AppearancePreview";
import { CitationSection } from "@/app/design/CitationSection";
import { BrandSection, ButtonsSection, RowsSection } from "@/app/design/ControlsSection";
import { EvidenceSection } from "@/app/design/EvidenceSection";
import { FormsSection } from "@/app/design/FormsSection";
import { LabelSection } from "@/app/design/LabelSection";
import { MotionSection } from "@/app/design/MotionSection";
import { PlatesSection } from "@/app/design/PlatesSection";
import { StatusSection } from "@/app/design/StatusSection";
import { BrandLockup } from "@/components/BrandMark";

export const metadata: Metadata = {
  title: "Design system",
  description: "Every KalaVigyan primitive in every state, drawn from the components the pages use.",
  robots: { index: false, follow: false }
};

export default function DesignPage() {
  return (
    <div className="min-h-dvh bg-ground text-ink-1">
      <header className="border-b border-ink-1">
        <div className="mx-auto grid max-w-content gap-6 px-4 pt-7 pb-6 sm:px-6 md:px-10 rail:px-12 xl:px-16">
          <BrandLockup />
          <div className="grid gap-3">
            <h1 className="max-w-[16ch] font-headline text-h1">Alum and indigo, the primitives</h1>
            <p className="max-w-measure font-reading text-lede text-ink-2">Every control, label, plate, citation and state the pages are built from, drawn by the real components.</p>
          </div>
          <AppearancePreview />
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-content px-4 sm:px-6 md:px-10 rail:px-12 xl:px-16">
        <BrandSection />
        <ButtonsSection />
        <RowsSection />
        <FormsSection />
        <CitationSection />
        <EvidenceSection />
        <LabelSection />
        <PlatesSection />
        <StatusSection />
        <MotionSection />
      </main>
    </div>
  );
}
