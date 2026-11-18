export type FadedWord = { word: string; opacity: number };
export type FadedElement = { name: string; opacity: number };
export type OpacityAtCapture = { headline: FadedWord[]; largest: FadedElement | null };
export type CitationCluster = { numbers: string[]; context: string };
export type Repeat = { what: string; count: number };
export type AnswerRepeats = { sentences: Repeat[]; pictures: Repeat[] };

export function opacityAtCapture(full: number): OpacityAtCapture {
  const opacityOf = (element: Element | null) => {
    let value = 1;
    for (let node = element; node; node = node.parentElement) value *= Number(getComputedStyle(node).opacity);
    return Math.round(value * 100) / 100;
  };
  const shown = (element: Element) => element.checkVisibility({ visibilityProperty: true }) && !element.closest('[aria-hidden="true"]');
  const headline: FadedWord[] = [];
  for (const heading of Array.from(document.querySelectorAll("h1")).filter(shown)) {
    const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const opacity = opacityOf(node.parentElement);
      if (opacity >= full) continue;
      for (const word of (node.textContent ?? "").split(/\s+/).filter(Boolean)) headline.push({ word, opacity });
    }
  }
  const onScreen = (rect: DOMRect) =>
    Math.max(0, Math.min(rect.right, innerWidth) - Math.max(rect.left, 0)) * Math.max(0, Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0));
  const textArea = (element: Element) =>
    Array.from(element.childNodes)
      .filter((child) => child.nodeType === Node.TEXT_NODE && (child.textContent ?? "").trim())
      .reduce((sum, child) => {
        const range = document.createRange();
        range.selectNodeContents(child);
        return sum + onScreen(range.getBoundingClientRect());
      }, 0);
  let largest: Element | null = null;
  let largestArea = 0;
  for (const element of Array.from(document.body.querySelectorAll("*"))) {
    const media = element.matches("img, video, canvas, picture, svg:not(svg svg)");
    const area = media ? onScreen(element.getBoundingClientRect()) : textArea(element);
    if (area <= largestArea || !shown(element)) continue;
    largest = element;
    largestArea = area;
  }
  const opacity = opacityOf(largest);
  if (!largest || opacity >= full) return { headline, largest: null };
  const testId = largest.getAttribute("data-testid");
  const text = (largest.textContent ?? largest.getAttribute("alt") ?? "").replace(/\s+/g, " ").trim().slice(0, 40);
  return { headline, largest: { name: `<${largest.tagName.toLowerCase()}${testId ? ` data-testid="${testId}"` : ""}> "${text}"`, opacity } };
}

export function citationClusters(): CitationCluster[] {
  const chip = '[data-testid="citation-chip"]';
  const nextChip = (element: Element) => {
    let node = element.nextSibling;
    while (node && node.nodeType === Node.TEXT_NODE && !(node.textContent ?? "").trim()) node = node.nextSibling;
    return node instanceof Element && node.matches(chip) ? node : null;
  };
  const plainText = (holder: Element | null) => {
    const parts: string[] = [];
    const walker = document.createTreeWalker(holder ?? document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) if (!node.parentElement?.closest(chip)) parts.push(node.textContent ?? "");
    return parts.join(" ").replace(/\s+/g, " ").trim().slice(0, 60);
  };
  const counted = new Set<Element>();
  const clusters: CitationCluster[] = [];
  for (const first of Array.from(document.querySelectorAll(chip))) {
    if (counted.has(first) || !first.checkVisibility()) continue;
    const run = [first];
    for (let next = nextChip(first); next; next = nextChip(next)) run.push(next);
    run.forEach((member) => counted.add(member));
    const numbers = run.map((member) => (member.textContent ?? "").match(/\d+/)?.[0] ?? "·");
    const numbered = numbers.filter((number) => number !== "·");
    if (new Set(numbered).size === numbered.length) continue;
    clusters.push({ numbers, context: plainText(first.closest('[data-testid="answer-sentence"]') ?? first.parentElement?.parentElement ?? null) });
  }
  return clusters;
}

export function answerRepeats(scope: string): AnswerRepeats {
  const tally = (values: string[]) => {
    const counts = new Map<string, number>();
    for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
    return [...counts].filter(([, count]) => count > 1).map(([what, count]) => ({ what, count }));
  };
  const pictureKey = (image: HTMLImageElement) => {
    const url = new URL(image.currentSrc || image.src, location.href);
    const wrapped = url.pathname.startsWith("/_next/image") ? url.searchParams.get("url") : null;
    const source = wrapped ? new URL(wrapped, location.href) : url;
    return `${source.host.toLowerCase()}${source.pathname.replace(/\/thumb(\/.+?)\/[^/]+$/, "$1")}`;
  };
  const sentences: string[] = [];
  const pictures: string[] = [];
  for (const answer of Array.from(document.querySelectorAll(scope))) {
    for (const sentence of Array.from(answer.querySelectorAll('[data-testid="answer-sentence"]')).filter((node) => node.checkVisibility())) {
      const text = (sentence.querySelector(":scope > span[lang]") ?? sentence).textContent ?? "";
      sentences.push(text.replace(/\s+/g, " ").trim());
    }
    for (const image of Array.from(answer.querySelectorAll("img")).filter((node) => node.checkVisibility() && (node.currentSrc || node.src))) {
      pictures.push(pictureKey(image));
    }
  }
  return { sentences: tally(sentences.filter(Boolean)), pictures: tally(pictures) };
}

export function emptyPictures(minSide: number): string[] {
  return Array.from(document.querySelectorAll("img"))
    .filter((image) => {
      const box = image.getBoundingClientRect();
      const failed = image.complete ? image.naturalWidth === 0 : image.loading !== "lazy";
      return box.width >= minSide && box.height >= minSide && image.checkVisibility() && failed;
    })
    .map((image) => (image.alt || image.currentSrc || image.src).slice(0, 80));
}

export function busyText(options: { citedSelector: string; pattern: string }): string[] {
  const busy = new RegExp(options.pattern);
  const found = new Set<string>();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent || parent.closest(`script, style, noscript, template, ${options.citedSelector}`) || !parent.checkVisibility()) continue;
    const text = (parent.textContent ?? "").replace(/\s+/g, " ").trim();
    if (busy.test(text)) found.add(text);
  }
  return [...found];
}

export function regionRunPx(options: { panel: string; marker: string }): number | null {
  const panel = document.querySelector(options.panel);
  if (!panel || !panel.checkVisibility()) return null;
  const top = panel.getBoundingClientRect().top;
  const marker = Array.from(panel.querySelectorAll("button, summary, h2, h3, a")).find((node) => (node.textContent ?? "").trim().startsWith(options.marker));
  const end = marker ? marker.getBoundingClientRect().top : panel.getBoundingClientRect().bottom;
  return Math.round(end - top);
}

export function shownTheme(): string | null {
  return document.documentElement.getAttribute("data-theme");
}
