import { AuthoredShell } from "@/components/monograph/AuthoredShell";
import { MonographFrame, type MonographPageProps } from "@/components/monograph/MonographFrame";
import { MonographRail } from "@/components/monograph/MonographRail";
import { PageDownloadRow } from "@/components/monograph/PageDownloadRow";
import { shellScopes } from "@/lib/kitShellScopes";
import { deferredRest } from "@/lib/monographDeferred";
import { railChapters } from "@/lib/monographRenderLayout";
import { documentTree, leadLength } from "@/lib/monographRenderShell";
import { shownPage } from "@/lib/monographShownPage";

export function MonographShellPage({ document: given, deferred = false, languages = null }: MonographPageProps) {
  const { document, plan } = shownPage(given);
  const rest = deferredRest(given, plan, deferred);
  const tree = documentTree(document);
  const drawn = rest === null ? tree : tree.slice(0, leadLength(tree));
  return (
    <MonographFrame document={document} given={given} dataDeferred={rest !== null} languages={languages} scopes={shellScopes(document, drawn)}>
      <MonographRail chapters={railChapters(plan)} />
      <AuthoredShell document={document} shell={document.shell ?? ""} rest={rest} />
      <PageDownloadRow document={document} />
    </MonographFrame>
  );
}
