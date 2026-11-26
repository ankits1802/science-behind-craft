"use client";

import { usePathname } from "next/navigation";

import { LegacyScope } from "@/components/monograph/LegacyScope";
import { TextLink } from "@/components/ui/TextLink";
import type { LanguageOption, LanguageSwitchSpec } from "@/lib/componentSpecsTools";
import { isDocumentLanguage, TEXT_SCRIPTS } from "@/lib/documentLanguages";

function OptionName({ option }: { option: LanguageOption }) {
  const script = isDocumentLanguage(option.lang) ? TEXT_SCRIPTS[option.lang] : undefined;
  return (
    <>
      <span lang={option.lang} dir={option.direction} data-script={script} className="ui">
        {option.name}
      </span>
      {option.status !== option.name ? <span className="text-ink-3"> {option.status}</span> : null}
    </>
  );
}

function Choice({ option, current }: { option: LanguageOption; current: boolean }) {
  if (current || option.href === undefined) {
    return (
      <span aria-current={current ? "page" : undefined} className="font-medium text-ink-1">
        <OptionName option={option} />
      </span>
    );
  }
  return (
    <TextLink href={option.href}>
      <OptionName option={option} />
    </TextLink>
  );
}

export function LanguageLinks({ spec }: { spec: LanguageSwitchSpec }) {
  const pathname = usePathname();
  return (
    <LegacyScope scope="rm">
      <nav className="kv-lang-links wrap" aria-label={spec.label}>
        <p className="kicker">{spec.label}</p>
        <ul className="flex flex-wrap items-baseline gap-x-4 gap-y-1 font-ui text-ui">
          {spec.options.map((option) => (
            <li key={option.lang}>
              <Choice option={option} current={option.href === pathname} />
            </li>
          ))}
        </ul>
      </nav>
    </LegacyScope>
  );
}
