import { serverDocumentReader } from "@/lib/monographLanguagesServer";
import type { ShellParams } from "@/lib/monographRenderServer";
import { documentRest, restAddress } from "@/lib/monographRenderShell";
import { addressedDocument } from "@/lib/monographRestRead";

type RestRoute = { params: Promise<ShellParams> };

export const dynamic = "force-static";
export const revalidate = 604800;
export const dynamicParams = true;

export async function generateStaticParams(): Promise<ShellParams[]> {
  return [];
}

export async function GET(_request: Request, { params }: RestRoute): Promise<Response> {
  const { slug, version } = await params;
  const address = restAddress(version);
  const document = address === null ? null : await addressedDocument(serverDocumentReader("category", slug), address);
  if (!document || document.shell !== null) return new Response(null, { status: 404 });
  return Response.json(documentRest(document));
}
