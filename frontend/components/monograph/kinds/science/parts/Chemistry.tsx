import { Fragment, type ReactNode } from "react";

import type { AtomTable, Equation, EquationLine, Species } from "@/lib/componentSpecsScienceParts";

import { RichText } from "./Drawing";
import { Tick } from "./icons";

type RenderUnit = (ref: string) => ReactNode;

export function SpeciesTerm({ term }: { term: Species }) {
  return (
    <span className="sp">
      <b>
        <RichText runs={term.formula} />
      </b>
      {term.name !== null ? <small>{term.name}</small> : null}
    </span>
  );
}

function Terms({ terms }: { terms: Species[] }) {
  return terms.map((term, index) => (
    <Fragment key={index}>
      {index > 0 ? <span className="op">+</span> : null}
      <SpeciesTerm term={term} />
    </Fragment>
  ));
}

export function EquationLineView({ line }: { line: EquationLine }) {
  return (
    <div className="eq-line">
      <span className="side">
        <Terms terms={line.reactants} />
      </span>
      <span className="side prod">
        <span className="op arrow">→</span>
        <Terms terms={line.products} />
      </span>
    </div>
  );
}

function Grouped({ term, sign }: { term: Species; sign: string }) {
  return (
    <span className="grp">
      <span className="op">{sign}</span>
      <SpeciesTerm term={term} />
    </span>
  );
}

export function GroupedLine({ line, label }: { line: EquationLine; label: string }) {
  const [first, ...more] = line.reactants;
  return (
    <div className="eq-line eq-sm" role="group" aria-label={label}>
      <span className="side">
        <SpeciesTerm term={first} />
        {more.map((term, index) => <Grouped key={index} term={term} sign="+" />)}
      </span>
      <span className="side">
        {line.products.map((term, index) => <Grouped key={index} term={term} sign={index === 0 ? "→" : "+"} />)}
      </span>
    </div>
  );
}

function AtomCount({ table, renderUnit }: { table: AtomTable; renderUnit: RenderUnit }) {
  return (
    <table className="atoms">
      <caption>{table.caption}</caption>
      <thead>
        <tr>{table.head.map((unit) => <th key={unit} scope="col">{renderUnit(unit)}</th>)}</tr>
      </thead>
      <tbody>
        {table.rows.map((row) => (
          <tr key={row.element}>
            <th scope="row">{renderUnit(row.element)}</th>
            <td>{renderUnit(row.left)}</td>
            <td>{renderUnit(row.right)}</td>
            <td className="ok">
              <Tick />
              <span className="vh">balanced</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function EquationView({ equation, renderUnit }: { equation: Equation; renderUnit: RenderUnit }) {
  return (
    <div className={equation.style ? `eq ${equation.style}` : "eq"} role="group" aria-label={equation.label}>
      <EquationLineView line={equation.line} />
      {equation.atoms ? (
        <div className="eq-foot">
          <AtomCount table={equation.atoms} renderUnit={renderUnit} />
          {equation.notes.length ? (
            <div className="eq-notes">{equation.notes.map((unit) => <p key={unit} className="eq-note">{renderUnit(unit)}</p>)}</div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function TickedCount({ count }: { count: string }) {
  return (
    <p className="eq-count">
      <span className="ok">
        <Tick />
      </span>
      {count}
    </p>
  );
}
