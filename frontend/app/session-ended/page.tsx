"use client";

import { useEffect, useState } from "react";

import { AuthFrame } from "@/components/auth/AuthShell";
import { ErrorState } from "@/components/DeadEnd";
import { nextFromSearch } from "@/lib/sessionReturn";

export default function SessionEndedPage() {
  const [next, setNext] = useState<string | null>(null);
  useEffect(() => {
    setNext(nextFromSearch(window.location.search));
  }, []);
  return (
    <AuthFrame>
      <ErrorState kind="session" next={next ?? "/ask"} />
    </AuthFrame>
  );
}
