import { serverDocumentReader } from "@/lib/monographLanguagesServer";
import { prerenderedShells, type ShellParams } from "@/lib/monographRenderServer";
import { restAddress, restBody } from "@/lib/monographRenderShell";
import { addressedDocument } from "@/lib/monographRestRead";

type ShellRoute = { params: Promise<ShellParams> };

export const dynamic = "force-static";
export const revalidate = 604800;
export const dynamicParams = true;

export async function generateStaticParams(): Promise<ShellParams[]> {
  return prerenderedShells();
}

export async function GET(_request: Request, { params }: ShellRoute): Promise<Response> {
  const { slug, version } = await params;
  const address = restAddress(version);
  const document = address === null ? null : await addressedDocument(serverDocumentReader("craft", slug), address);
  if (!document) return new Response(null, { status: 404 });
  return Response.json(restBody(document));
}
