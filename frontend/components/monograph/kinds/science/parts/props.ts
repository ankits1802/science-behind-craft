const KEPT = /^(data-|aria-)/;
const RENAMED: Record<string, string> = { class: "className", for: "htmlFor", tabindex: "tabIndex" };

const camel = (name: string) => name.replace(/-([a-z])/g, (_, letter: string) => letter.toUpperCase());

export function propName(name: string): string {
  if (name in RENAMED) return RENAMED[name];
  return KEPT.test(name) ? name : camel(name);
}

export function styleObject(css: string): Record<string, string> {
  const style: Record<string, string> = {};
  for (const declaration of css.split(";")) {
    const colon = declaration.indexOf(":");
    const name = declaration.slice(0, colon).trim();
    if (colon < 0 || !name) continue;
    style[name.startsWith("--") ? name : camel(name)] = declaration.slice(colon + 1).trim();
  }
  return style;
}

export function reactProps(attrs: Record<string, string> | undefined): Record<string, unknown> {
  const props: Record<string, unknown> = {};
  for (const [name, value] of Object.entries(attrs ?? {})) {
    props[propName(name)] = name === "style" ? styleObject(value) : value;
  }
  return props;
}

export const swatchStyle = (token: string) => ({ background: `var(${token})` });

export const PUBCHEM = (cid: number) => `https://pubchem.ncbi.nlm.nih.gov/compound/${cid}`;
