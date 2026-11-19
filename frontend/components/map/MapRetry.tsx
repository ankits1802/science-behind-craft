import { AlertCircle } from "lucide-react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function MapRetry({ message, onRetry, className }: { message: string; onRetry: () => void; className?: string }) {
  return (
    <div role="alert" className={cn("grid gap-3 border-t border-rule pt-3 font-ui text-ui font-normal text-ink-1", className)} data-testid="map-retry">
      <p className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-error" aria-hidden />
        <span>{message}</span>
      </p>
      <ActionGroup align="start">
        <Button variant="quiet" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </ActionGroup>
    </div>
  );
}
