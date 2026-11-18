import type { NativeName } from "@/lib/editorialText";
import type { Citation, SourceRef } from "@/lib/types";

function source(id: string, title: string, publisher: string, year: number | null, reliability: SourceRef["reliability"], url: string | null = null): SourceRef {
  return { id, kind: "OTHER", title, authors: [], year, doi: null, url, publisher, licence: null, attribution: null, reliability };
}

export const SOURCES: SourceRef[] = [
  source("aj-s01", "GI Journal No. 188: Kutch Ajrakh", "GI Registry", 2023, "A", "https://search.ipindia.gov.in/GIRPublicSearch/"),
  source("aj-s14", "Ajrakh", "MAP Academy (Impart)", 2022, "B", "https://mapacademy.io/article/ajrakh/"),
  source("tx-s02", "Natural Colorants: Historical, Processing and Sustainable Prospects", "Natural Products and Bioprospecting", 2017, "A"),
  source("tx-s05", "Microbial Communities Associated With Indigo Fermentation That Thrive in Anaerobic Alkaline Environments", "Frontiers in Microbiology", 2018, "A"),
  source("tx-s01", "Indian Block-Printed Textiles: Past and Present", "Textile Society of America", null, "C"),
  source("tx-s37", "Dyeing cotton fabrics is an ancient Indian art", "The Hindu", 1992, "D")
];

export const SOURCES_BY_ID = new Map(SOURCES.map((entry) => [entry.id, entry]));

export const NUMBERS = new Map(SOURCES.map((entry, index) => [entry.id, index + 1]));

function cite(id: string, sourceId: string, quote: string | null, locator: string | null, level: Citation["level"] = "PROVISIONAL"): Citation {
  return { id, claimId: `claim-${id}`, sourceId, quote, locator, context: null, evidence: quote === null ? "INFERRED" : "QUOTED", level };
}

export const GREEN_TO_BLUE: Citation[] = [
  cite("c1", "aj-s14", "The dyed cloth emerges a bright green that slowly turns blue once the dye oxidises.", "paragraph 7"),
  cite("c2", "aj-s01", "At first bright green, the cloth rapidly becomes blue as oxygen meets the dye particles on the fibres.", "Application 1050, method of production, p. 12", "VERIFIED"),
  cite("c3", "aj-s01", "At first bright green, the cloth rapidly becomes blue as oxygen meets the dye particles on the fibres.", "Application 1050, method of production, p. 12", "VERIFIED")
];

export const LEUCO: Citation[] = [
  cite("c4", "tx-s37", null, null),
  cite("c5", "tx-s02", null, null),
  cite("c6", "tx-s05", null, null),
  cite("c7", "tx-s01", null, null),
  cite("c8", "tx-s02", null, null)
];

export const HYPOTHESIS: Citation[] = [{ ...cite("c9", "aj-s14", null, null, "HYPOTHESIS"), evidence: "QUOTED" }];

export const KASUTI_NAME: NativeName = { text: "ಕಸೂತಿ", lang: "kn", script: "Knda", sourceId: "wikidata-label-kasuti", sourceKind: "wikidata", reviewed: true };

export const UNREVIEWED_NAME: NativeName = { ...KASUTI_NAME, reviewed: false };

export const PHULKARI_NAME: NativeName = { text: "ਫੁਲਕਾਰੀ", lang: "pa", script: "Guru", sourceId: "wikidata-label-phulkari", sourceKind: "wikidata", reviewed: true };

export const SWAMIMALAI_NAME: NativeName = { text: "சுவாமிமலை வெண்கலப் படிமங்கள்", lang: "ta", script: "Taml", sourceId: "wikidata-label-swamimalai", sourceKind: "wikidata", reviewed: true };

export const AJRAK_PRINT = {
  src: "https://upload.wikimedia.org/wikipedia/commons/1/13/Ajrak_Print_6.jpg",
  alt: "Detail of an ajrakh print on an indigo ground.",
  credit: "SMarndi, CC BY-SA 4.0",
  page: "https://commons.wikimedia.org/wiki/File:Ajrak_Print_6.jpg"
};

export const BLOCK_CARVING = {
  src: "https://upload.wikimedia.org/wikipedia/commons/c/c1/Master_artist_carves_a_woodblock_for_textile_printing.jpg",
  alt: "A wooden textile printing block being carved, held up to show its floral and roundel motifs.",
  credit: "Journyes, CC BY-SA 4.0",
  page: "https://commons.wikimedia.org/wiki/File:Master_artist_carves_a_woodblock_for_textile_printing.jpg"
};

export const AJRAK_CLOTH = {
  src: "https://upload.wikimedia.org/wikipedia/commons/8/80/Ajrak_Craft.jpeg",
  alt: "An ajrakh cloth spread out, showing its field and borders.",
  credit: "Visdaviva, CC BY-SA 3.0",
  page: "https://commons.wikimedia.org/wiki/File:Ajrak_Craft.jpeg"
};

export const PRIEST_KING = {
  src: "https://upload.wikimedia.org/wikipedia/commons/b/bd/KING_PRIEST.jpg",
  alt: "The priest-king figure from Mohenjo-daro, his robe carved with a trefoil pattern.",
  credit: "Irfanmurtaza, CC BY-SA 4.0",
  page: "https://commons.wikimedia.org/wiki/File:KING_PRIEST.jpg"
};
