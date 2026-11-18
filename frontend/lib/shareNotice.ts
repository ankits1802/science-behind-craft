export type SharedKind = "answer" | "lesson";

export type ShareNotice = { title: string; body: string; note: string; confirmLabel: string };

const NEVER_NAMED = "Your name, email address and role never appear. Stop sharing and the link stops working.";

export const SHARE_NOTICE: Record<SharedKind, ShareNotice> = {
  answer: {
    title: "Share this answer?",
    body: "Anyone with the link can read your question and this version of the answer with its citations, and download its report as a PDF.",
    note: NEVER_NAMED,
    confirmLabel: "Share link"
  },
  lesson: {
    title: "Share this lesson?",
    body: "Anyone with the link can read this lesson with its citations, and download its slides and handout.",
    note: NEVER_NAMED,
    confirmLabel: "Share link"
  }
};
