import katex from "katex";
import "katex/contrib/mhchem";

export function chemistryTex(equation: string): string {
  const trimmed = equation.trim();
  if (/^\\ce\{[\s\S]*\}$/.test(trimmed)) return trimmed;
  return `\\ce{${trimmed.replace(/[{}]/g, "")}}`;
}

export function renderChemistry(equation: string, displayMode: boolean): string {
  return katex.renderToString(chemistryTex(equation), {
    displayMode,
    throwOnError: false,
    trust: false,
    strict: "ignore",
    output: "htmlAndMathml",
    maxExpand: 200,
    maxSize: 20
  });
}
