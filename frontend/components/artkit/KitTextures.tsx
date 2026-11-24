import type { KitIds } from "./kitIds";

const HIDDEN = { position: "absolute", width: 0, height: 0, overflow: "hidden" } as const;

export function KitTextures({ ids }: { ids: KitIds }) {
  return (
    <svg className="kv-kit-defs" width="0" height="0" style={HIDDEN} aria-hidden="true" focusable="false">
      <defs>
        <pattern id={ids.weave} width="3" height="3" patternUnits="userSpaceOnUse">
          <path d="M0 3 L3 0" stroke="black" strokeOpacity=".09" strokeWidth=".6" />
          <path d="M0 0 L3 3" stroke="white" strokeOpacity=".08" strokeWidth=".5" />
        </pattern>
        <pattern id={ids.grain} width="16" height="7" patternUnits="userSpaceOnUse">
          <path d="M0 2 Q4 0.8 8 2 T16 2 M0 5.4 Q4 4.4 8 5.4 T16 5.4" fill="none" stroke="var(--ink-1)" strokeOpacity=".2" strokeWidth=".6" />
        </pattern>
        <pattern id={ids.strata} width="10" height="8" patternUnits="userSpaceOnUse">
          <path d="M0 4 H6" stroke="var(--ink-3)" strokeOpacity=".35" strokeWidth=".8" />
          <path d="M5 0 H10 M-5 0 H0" stroke="var(--ink-3)" strokeOpacity=".2" strokeWidth=".8" />
        </pattern>
        <pattern id={ids.speckle} width="9" height="9" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="3" r=".7" fill="var(--ink-1)" fillOpacity=".28" />
          <circle cx="6.5" cy="7" r=".55" fill="var(--ink-1)" fillOpacity=".22" />
          <circle cx="7" cy="1.6" r=".45" fill="white" fillOpacity=".3" />
        </pattern>
        <pattern id={ids.ripple} width="18" height="8" patternUnits="userSpaceOnUse">
          <path d="M1 5 q4 -3 8 0 t8 0" fill="none" stroke="var(--ink-1)" strokeOpacity=".22" strokeWidth=".7" />
        </pattern>
      </defs>
    </svg>
  );
}
