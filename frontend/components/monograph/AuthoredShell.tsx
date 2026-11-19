import { NestedSlots, SlotRoot } from "@/components/monograph/BundleView";
import type { MonographDocument } from "@/lib/monographDocument";
import { bundleSources } from "@/lib/monographRenderKit";
import { componentBundles } from "@/lib/monographRenderLayout";

const SHELL_ID = "kv-main";

export function AuthoredShell({ document, shell }: { document: MonographDocument; shell: string }) {
  const natives = Object.keys(document.specs);
  const bundles = Object.assign({}, ...natives.map((label) => componentBundles(document, label)));
  return (
    <>
      <div id={SHELL_ID} dangerouslySetInnerHTML={{ __html: shell }} />
      {natives.length ? (
        <SlotRoot sources={bundleSources(document, bundles)} bundles={bundles}>
          <NestedSlots hostId={SHELL_ID} />
        </SlotRoot>
      ) : null}
    </>
  );
}
