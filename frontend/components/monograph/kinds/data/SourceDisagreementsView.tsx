import { HeldText } from "@/components/monograph/kinds/plates/HeldText";
import { heldComponent, type NestingViewProps } from "@/components/monograph/kinds/plates/nesting";
import { sourceDisagreementsShape, type Disagreement } from "@/lib/componentSpecsData";
import { parseShape } from "@/lib/shape";

function Item({ item, props }: { item: Disagreement; props: NestingViewProps }) {
  const renderUnit = props.renderUnit;
  const figure = item.figure;
  return (
    <div className="differ-item">
      <details className="differs" open>
        <summary>
          <span>
            <HeldText nodes={item.summary} />
          </span>
        </summary>
        <div className="differs-body">
          <div className="readings">
            {item.readings.map((reading) => (
              <div key={reading.unit} className="reading">
                <span className="who">{reading.who}</span>
                <p>{renderUnit(reading.unit)}</p>
              </div>
            ))}
          </div>
          {figure ? (
            <figure className="rangefig">
              <p className="fig-no" data-fig={figure.number.ref}>
                {renderUnit(figure.number.unit)}
              </p>
              <p className="chart-title">{renderUnit(figure.title)}</p>
              <p className="chart-dek">{renderUnit(figure.dek)}</p>
              {heldComponent(props, figure.chart)}
              <p className="src-line">{renderUnit(figure.source)}</p>
            </figure>
          ) : null}
        </div>
      </details>
    </div>
  );
}

export function SourceDisagreementsView(props: NestingViewProps) {
  const differ = parseShape(sourceDisagreementsShape, props.spec);
  return (
    <section className="sec" id={differ.id} aria-labelledby={differ.titleId}>
      <div className="spread">
        <div className="main">
          <h3 className="sec-h" id={differ.titleId}>
            <span className="sw sw-diff" aria-hidden="true"></span>
            {differ.title}
          </h3>
          <p className="sec-intro t-body">{props.renderUnit(differ.intro)}</p>
        </div>
      </div>
      <div className="differ-list">
        {differ.items.map((item) => (
          <Item key={item.readings[0].unit} item={item} props={props} />
        ))}
      </div>
    </section>
  );
}
