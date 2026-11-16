"use client";

import { useMemo } from "react";

import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { languageOptions, type AnswerLanguage } from "@/lib/answerLanguages";

export function LanguagePicker({
  value,
  languages,
  detected,
  onChange,
  disabled = false,
  ariaLabel = "Answer language"
}: {
  value: string;
  languages: AnswerLanguage[];
  detected: AnswerLanguage;
  onChange: (value: string) => void;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  const options = useMemo(() => languageOptions(languages, detected), [languages, detected]);
  return (
    <div className="w-44 min-w-0" data-testid="language-picker">
      <SearchableSelect
        value={value}
        options={options}
        onChange={onChange}
        ariaLabel={ariaLabel}
        searchable
        advanceOnSelect={false}
        disabled={disabled}
      />
    </div>
  );
}
