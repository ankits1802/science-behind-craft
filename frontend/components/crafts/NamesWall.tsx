import Link from "next/link";

import { craftHref } from "@/lib/atlasCollection";
import { namesByState, type NamedCraft } from "@/lib/atlasNames";
import { shownNativeName } from "@/lib/editorialText";

function NameRow({ named }: { named: NamedCraft }) {
  const shown = shownNativeName(named.nativeName);
  if (!shown) return null;
  return (
    <li>
      <Link href={craftHref(named)} className="group grid gap-0.5 border-b border-rule pt-2 pb-2.5" data-testid="names-wall-name">
        <span lang={shown.lang} data-script={shown.script} dir={shown.dir} className="font-reading text-h3 font-medium [overflow-wrap:normal] [word-break:keep-all]">
          {shown.text}
        </span>
        <span className="font-ui text-label font-normal text-ink-3 group-hover:text-indigo group-hover:underline group-hover:underline-offset-3">{named.englishName}</span>
      </Link>
    </li>
  );
}

export function NamesWall({ names }: { names: readonly NamedCraft[] }) {
  const groups = namesByState(names);
  return (
    <div data-testid="names-wall">
      <p className="mb-[18px] font-ui text-ui font-normal text-ink-2">{`${names.length} crafts whose own-script name a source records, grouped by home state.`}</p>
      {groups.map((group) => (
        <section key={group.state} aria-label={group.state} className="border-t border-ink-1 pt-[18px] pb-[22px]">
          <h3 className="kicker mb-3">
            {group.state}
            <b className="ms-1.5 text-ink-1 [font-variant-numeric:lining-nums_tabular-nums]">{group.crafts.length}</b>
          </h3>
          <ul className="grid grid-cols-[repeat(auto-fill,minmax(min(15rem,100%),1fr))] gap-x-7 gap-y-1.5">
            {group.crafts.map((named) => (
              <NameRow key={named.slug} named={named} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
