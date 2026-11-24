import type { Metadata } from "next";

import { AppearancePreview } from "@/app/design/AppearancePreview";
import { KitSheet } from "@/app/design/kit/KitSheet";
import { BrandLockup } from "@/components/BrandMark";

export const metadata: Metadata = {
  title: "The figure kit",
  description: "Every part of the figure kit in every depicted material, drawn by the components the pages use.",
  robots: { index: false, follow: false }
};

export default function KitSheetPage() {
  return (
    <div className="min-h-dvh bg-ground text-ink-1">
      <header className="border-b border-ink-1">
        <div className="mx-auto grid max-w-content gap-6 px-4 pt-7 pb-6 sm:px-6 md:px-10 rail:px-12 xl:px-16">
          <BrandLockup />
          <div className="grid gap-3">
            <h1 className="max-w-[16ch] font-headline text-h1">The figure kit</h1>
            <p className="max-w-measure font-reading text-lede text-ink-2">The parts a composed diagram is drawn from, in every form and every depicted material, with the four layouts they are set in.</p>
          </div>
          <AppearancePreview />
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-content px-4 sm:px-6 md:px-10 rail:px-12 xl:px-16">
        <KitSheet />
      </main>
    </div>
  );
}
