import { ConfirmProvider } from "@/components/dialogs/ConfirmDialog";
import { ReadingShell } from "@/components/shell/ReadingShell";

export default function ReadingLayout({ children }: { children: React.ReactNode }) {
  return (
    <ConfirmProvider>
      <ReadingShell>{children}</ReadingShell>
    </ConfirmProvider>
  );
}
