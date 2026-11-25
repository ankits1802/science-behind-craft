import { PageDownload } from "@/components/monograph/PageDownload";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { pageSubject, type PageSubject } from "@/lib/pageExport";

export const PAGE_DOWNLOAD_ROW_TEST_ID = "page-download-row";

export function PageDownloadRow({ document }: { document: PageSubject }) {
  return (
    <div className="kv-page kv-citethis-place" data-app="" data-testid={PAGE_DOWNLOAD_ROW_TEST_ID}>
      <ActionGroup>
        <PageDownload subject={pageSubject(document)} />
      </ActionGroup>
    </div>
  );
}
