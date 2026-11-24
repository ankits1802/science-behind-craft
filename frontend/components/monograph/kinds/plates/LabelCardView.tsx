import { KitSceneArt, KitSceneKey, KitSceneTextures } from "@/components/artkit/KitScene";
import { kitIds } from "@/components/artkit/kitIds";
import { isKitScene } from "@/lib/componentSpecsKitScene";
import { labelCardShape } from "@/lib/componentSpecsPlates";
import { parseShape } from "@/lib/shape";

import { heldComponent, type NestingViewProps } from "./nesting";
import { SpecDrawing } from "./SpecDrawing";

export function LabelCardView(props: NestingViewProps) {
  const { spec, renderUnit } = props;
  const card = parseShape(labelCardShape, spec);
  const variant = card.variant;
  const seal = card.seal;
  const ids = kitIds(props.component.label);
  return (
    <div className={`label-card ${variant}`}>
      <p className={`lc-k ${variant}-k`}>{renderUnit(card.kicker)}</p>
      <div className={`${variant}-seal`}>
        {isKitScene(seal) ? <KitSceneArt scene={seal} ids={ids} name="seal" seal /> : <SpecDrawing element={seal} />}
        <p className="lc-s">{renderUnit(card.sentence)}</p>
      </div>
      {isKitScene(seal) ? <KitSceneKey scene={seal} ids={ids} renderUnit={renderUnit} className="seal-key" /> : null}
      {heldComponent(props, card.inset)}
      <dl className={`${variant}-facts`}>
        {card.facts.map((fact) => (
          <div key={fact.term}>
            <dt>{renderUnit(fact.term)}</dt>
            <dd>{renderUnit(fact.value)}</dd>
          </div>
        ))}
      </dl>
      <KitSceneTextures ids={ids} scenes={[seal]} />
    </div>
  );
}
