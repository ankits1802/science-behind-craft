import { AuthoredShell } from "@/components/monograph/AuthoredShell";
import { ComponentSlot } from "@/components/monograph/ComponentSlot";
import { KitScript } from "@/components/monograph/KitScript";
import { KitShellTail } from "@/components/monograph/KitShellTail";
import { MonographMasthead } from "@/components/monograph/MonographMasthead";
import { MonographPassage } from "@/components/monograph/MonographPassage";
import { MonographRail } from "@/components/monograph/MonographRail";
import { KitPreferences } from "@/components/monograph/ReaderSettings";
import { SourceList } from "@/components/monograph/SourceList";
import { MONOGRAPH_KIT_CSS, type MonographDocument } from "@/lib/monographDocument";
import { pagePlan, type ChapterBlock, type ChapterPlan, type MastheadPlan } from "@/lib/monographRenderLayout";

function BlockView({ document, chapter, block }: { document: MonographDocument; chapter: ChapterPlan; block: ChapterBlock }) {
  if (block.kind === "passage") return <MonographPassage document={document} chapter={chapter} passage={block} />;
  if (block.kind === "component") return <ComponentSlot document={document} label={block.label} />;
  return <SourceList document={document} />;
}

function blockKey(block: ChapterBlock, at: number): string {
  return block.kind === "component" ? block.label : `${block.kind}-${at}`;
}

export function MonographChapter({ document, chapter, masthead }: { document: MonographDocument; chapter: ChapterPlan; masthead: MastheadPlan | null }) {
  return (
    <section className="kv-ch" id={chapter.key} data-ch={chapter.index} data-label={chapter.label} aria-label={chapter.label}>
      {masthead ? <MonographMasthead document={document} masthead={masthead} /> : null}
      {chapter.blocks.map((block, at) => (
        <BlockView key={blockKey(block, at)} document={document} chapter={chapter} block={block} />
      ))}
    </section>
  );
}

export function MonographPage({ document }: { document: MonographDocument }) {
  const plan = pagePlan(document);
  return (
    <div className="kv-monograph ms-[calc(50%-50vw)] w-screen" data-subject={`${document.subjectKind}:${document.subjectSlug}`} data-version={document.version}>
      <link rel="stylesheet" href={MONOGRAPH_KIT_CSS} precedence="default" />
      <MonographRail chapters={plan.chapters} />
      {document.shell !== null ? (
        <AuthoredShell document={document} shell={document.shell} />
      ) : (
        <div id="kv-main">
          {plan.chapters.map((chapter) => (
            <MonographChapter key={chapter.key} document={document} chapter={chapter} masthead={chapter.index === 0 ? plan.masthead : null} />
          ))}
        </div>
      )}
      <KitShellTail document={document} />
      <KitPreferences />
      <KitScript />
    </div>
  );
}
