"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useAuth } from "@/components/AuthProvider";
import { LegacyScope } from "@/components/monograph/LegacyScope";
import { askPagePath, signedOutAskHref } from "@/lib/askEntry";
import { askNextSpecShape, parseToolSpec } from "@/lib/componentSpecsTools";
import type { ComponentViewProps } from "@/lib/componentViewContract";

export function askNextHref(signedIn: boolean, craft: string, question: string): string {
  return signedIn ? askPagePath({ craft, question }) : signedOutAskHref({ craft, question });
}

export function AskNextView({ spec }: ComponentViewProps) {
  const askNext = useMemo(() => parseToolSpec(askNextSpecShape, spec), [spec]);
  const { user } = useAuth();
  return (
    <LegacyScope scope="rm">
      <ul className="asknext">
        {askNext.questions.map((question) => (
          <li key={question}>
            <Link href={askNextHref(Boolean(user), askNext.craft, question)}>
              <span className="aq">{question}</span>
              <span className="ago">
                <span>{askNext.action}</span>
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  <path d="M2.5 8 H13 M9 4 L13 8 L9 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </LegacyScope>
  );
}
