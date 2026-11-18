"use client";

import { Search, X } from "lucide-react";
import { useEffect, useRef } from "react";

const TYPING_TARGETS = "input, textarea, select, [contenteditable]:not([contenteditable='false'])";

export function takesSlashShortcut(key: string, target: EventTarget | null): boolean {
  if (key !== "/") return false;
  return !(target instanceof Element && target.closest(TYPING_TARGETS));
}

export function SearchInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Search",
  ariaLabel,
  shortcut = false
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  ariaLabel?: string;
  shortcut?: boolean;
}) {
  const input = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!shortcut) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
      if (!takesSlashShortcut(event.key, event.target)) return;
      event.preventDefault();
      input.current?.focus();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [shortcut]);

  return (
    <div className="kv-search" role="search">
      <Search className="h-[1.125rem] w-[1.125rem] shrink-0 text-ink-3" aria-hidden />
      <input
        ref={input}
        type="text"
        role="searchbox"
        aria-label={ariaLabel ?? placeholder}
        aria-keyshortcuts={shortcut ? "/" : undefined}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            onSubmit?.();
          }
        }}
      />
      {value ? (
        <button
          type="button"
          aria-label="Clear the search"
          onClick={() => {
            onChange("");
            input.current?.focus();
          }}
          className="kv-close m-0"
        >
          <X aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
