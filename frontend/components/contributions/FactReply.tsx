import { GateResults } from "@/components/contributions/GateResults";
import { replyHeadline, type ProposalReply } from "@/lib/factProposalContract";

export function FactReply({ reply }: { reply: ProposalReply | null }) {
  return (
    <div role="status" aria-live="polite" className="grid gap-3 empty:hidden" data-testid="fact-reply">
      {reply ? (
        <>
          <h2 className="font-reading text-h3 text-ink-1">{replyHeadline(reply)}</h2>
          <p className="max-w-measure font-reading text-body-sm text-ink-2">{reply.message}</p>
          {reply.sourcesDiffer ? (
            <p className="max-w-measure font-reading text-body-sm text-ink-2">It differs from a fact already held, so both are shown as sources differ.</p>
          ) : null}
          <GateResults gates={reply.gates} />
        </>
      ) : null}
    </div>
  );
}
