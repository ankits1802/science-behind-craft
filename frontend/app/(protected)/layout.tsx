import { AppShell } from "@/components/AppShell";
import { ConfirmProvider } from "@/components/dialogs/ConfirmDialog";
import { UnsavedChangesProvider } from "@/components/UnsavedChangesGuard";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <ConfirmProvider>
      <UnsavedChangesProvider>
        <AppShell>{children}</AppShell>
      </UnsavedChangesProvider>
    </ConfirmProvider>
  );
}
