import { ChangedComponents } from "@/components/review/ChangedComponents";
import { DrawnPair } from "@/components/review/DrawnPair";
import { PageChangeLines } from "@/components/review/PageChangeLines";
import { ScopeDecision } from "@/components/review/ScopeDecision";
import type { ProposalDocuments } from "@/components/review/useProposalDocuments";
import type { ChapterChanges, PageAction, PageProposalView, PageScope } from "@/lib/pageProposalContract";
import { changedCount, chapterCounts, chapterPictures, chapterScope, emptyWords } from "@/lib/pageProposalView";

type Decide = (scope: PageScope, action: PageAction, words: string) => Promise<string | null>;

export function ChapterChangeList({ view, docs, onDecide }: { view: PageProposalView; docs: ProposalDocuments; onDecide: Decide }) {
  if (!view.chapters.length) {
    return <p className="max-w-measure font-ui text-ui text-ink-2">Nothing on the page changes in words, components or pictures; its parts are listed below.</p>;
  }
  return (
    <ol className="grid gap-8" data-testid="chapter-change-list">
      {view.chapters.map((chapter) => (
        <li key={chapter.key}>
          <ChapterBlock view={view} chapter={chapter} docs={docs} onDecide={onDecide} />
        </li>
      ))}
    </ol>
  );
}

function ChapterBlock({ view, chapter, docs, onDecide }: { view: PageProposalView; chapter: ChapterChanges; docs: ProposalDocuments; onDecide: Decide }) {
  const pair = chapterPictures(view, chapter.key);
  const more = changedCount(chapter) - chapter.changes.length;
  return (
    <section className="grid gap-4 border-t border-ink-1 pt-4" data-testid="chapter-changes" data-chapter={chapter.key}>
      <div className="grid gap-1">
        <h4 className="font-ui text-h4 text-ink-1">{chapter.title}</h4>
        <p className="font-ui text-label text-ink-3">{chapterCounts(chapter)}</p>
      </div>
      {pair ? <DrawnPair pair={pair} empty={emptyWords(view)} /> : null}
      <PageChangeLines changes={chapter.changes} />
      {more > 0 ? <p className="font-ui text-label text-ink-3">{`And ${more} more changes, drawn in the chapter's pictures.`}</p> : null}
      <ChangedComponents view={view} chapter={chapter} docs={docs} onDecide={onDecide} />
      <ScopeDecision view={view} scope={chapterScope(chapter.key)} title={`Decide the chapter ${chapter.title}`} onDecide={onDecide} />
    </section>
  );
}
