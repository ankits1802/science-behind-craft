"use client";

import { useState } from "react";

import { apiErrorMessage } from "@/lib/api";
import { searchLibrary, type ComponentSummary } from "@/lib/componentProposalContract";

const SEARCH_FAILED = "Couldn't search the library. Try again.";

export type LibraryCraft = { slug: string; name: string };

export type LibrarySearchState = {
  query: string;
  craft: LibraryCraft | null;
  kind: string;
  found: ComponentSummary[] | null;
  searching: boolean;
  error: string | null;
  setQuery: (query: string) => void;
  setCraft: (craft: LibraryCraft | null) => void;
  setKind: (kind: string) => void;
  search: () => Promise<ComponentSummary[]>;
};

export function useLibrarySearch(): LibrarySearchState {
  const [query, setQuery] = useState("");
  const [craft, setCraft] = useState<LibraryCraft | null>(null);
  const [kind, setKind] = useState("");
  const [found, setFound] = useState<ComponentSummary[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search(): Promise<ComponentSummary[]> {
    setSearching(true);
    setError(null);
    try {
      const answer = await searchLibrary({ query, craftSlug: craft?.slug ?? null, kind: kind || null });
      setFound(answer.components);
      return answer.components;
    } catch (cause) {
      setError(apiErrorMessage(cause, SEARCH_FAILED));
      return [];
    } finally {
      setSearching(false);
    }
  }

  return { query, craft, kind, found, searching, error, setQuery, setCraft, setKind, search };
}
