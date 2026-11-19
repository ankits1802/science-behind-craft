import { UnitView } from "@/components/monograph/UnitView";
import type { MonographDocument, MonographUnit } from "@/lib/monographDocument";
import { nodeElements } from "@/lib/monographRenderElements";
import type { ChapterPlan, Passage, PassagePiece, UnitRole } from "@/lib/monographRenderLayout";

type Drawn = { as: string; className?: string };

const ROLE_DRAWING: Readonly<Record<Exclude<UnitRole, "text">, Drawn>> = {
  numeral: { as: "p", className: "chapter-no in-main" },
  kicker: { as: "p", className: "kicker sec-kicker" },
  title: { as: "h2", className: "t-h2" },
  lede: { as: "p", className: "t-lede" },
  label: { as: "p", className: "kicker" }
};

const TEXT_DRAWING: Readonly<Record<string, Drawn>> = {
  h3: { as: "h3", className: "font-reading text-h3 mt-8" },
  h4: { as: "h4", className: "font-ui text-h4 mt-6" },
  blockquote: { as: "blockquote", className: "font-reading text-quote italic" }
};

export const MARGIN_LABEL = "Sources in this passage";

function drawing(unit: MonographUnit, role: UnitRole): Drawn {
  if (role !== "text") return ROLE_DRAWING[role];
  return TEXT_DRAWING[unit.tag] ?? { as: "p", className: "t-body" };
}

type PieceProps = { document: MonographDocument; chapter: ChapterPlan; piece: PassagePiece; titled: boolean };

function Piece({ document, chapter, piece, titled }: PieceProps) {
  const { units, sources } = document.content;
  if (piece.kind === "list") {
    return <ul className="kv-list">{piece.refs.map((ref) => <li key={ref}>{nodeElements(units[ref].nodes, sources)}</li>)}</ul>;
  }
  if (piece.kind === "terms") {
    return <dl className="kv-terms">{piece.refs.map((ref) => <UnitView key={ref} unit={units[ref]} sources={sources} />)}</dl>;
  }
  const unit = units[piece.ref];
  const drawn = drawing(unit, piece.role);
  const id = piece.role === "title" && titled ? `${chapter.key}-h` : undefined;
  return <UnitView unit={unit} sources={sources} as={drawn.as} className={drawn.className} id={id} />;
}

function firstTitle(passage: Passage): string | null {
  const found = passage.pieces.find((piece) => piece.kind === "unit" && piece.role === "title");
  return found && found.kind === "unit" ? found.ref : null;
}

type PassageProps = { document: MonographDocument; chapter: ChapterPlan; passage: Passage };

function MarginNotes({ document, passage }: Omit<PassageProps, "chapter">) {
  const { units, sources } = document.content;
  if (!passage.notes.length) return null;
  return (
    <aside className="margin note" aria-label={MARGIN_LABEL}>
      <ul>
        {passage.notes.map((note) => (
          <li key={note.ref} data-g={note.source}>
            {nodeElements(units[note.ref].nodes, sources)}
          </li>
        ))}
      </ul>
    </aside>
  );
}

export function needsNumeral(passage: Passage, number: number | null): boolean {
  return passage.head && number !== null && !passage.pieces.some((piece) => piece.kind === "unit" && piece.role === "numeral");
}

function Spread({ document, chapter, passage }: PassageProps) {
  const title = passage.head ? firstTitle(passage) : null;
  return (
    <div className={passage.head ? "spread railed sec-head" : "spread"}>
      {passage.head && chapter.number !== null ? (
        <div className="rail">
          <span className="numeral">{chapter.number}</span>
        </div>
      ) : null}
      <div className="main prose">
        {needsNumeral(passage, chapter.number) ? <p className="chapter-no in-main">{chapter.number}</p> : null}
        {passage.pieces.map((piece, at) => (
          <Piece key={piece.kind === "unit" ? piece.ref : `${piece.kind}-${at}`} document={document} chapter={chapter} piece={piece} titled={piece.kind === "unit" && piece.ref === title} />
        ))}
      </div>
      <MarginNotes document={document} passage={passage} />
    </div>
  );
}

export function MonographPassage({ document, chapter, passage }: PassageProps) {
  const title = passage.head ? firstTitle(passage) : null;
  const spread = <Spread document={document} chapter={chapter} passage={passage} />;
  return (
    <div className="bx bx-pt">
      <div className="screen">
        {passage.head ? (
          <section className="sec wrap" aria-labelledby={title ? `${chapter.key}-h` : undefined}>
            {spread}
          </section>
        ) : (
          <div className="wrap kv-passage">{spread}</div>
        )}
      </div>
    </div>
  );
}
