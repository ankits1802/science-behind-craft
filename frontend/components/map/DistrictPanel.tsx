"use client";

import { useEffect, useMemo, useRef } from "react";

import { CitedReading } from "@/components/answer/CitedReading";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { failureMessage, useRemote, type Remote } from "@/components/hooks/useRemote";
import { DistrictView } from "@/components/map/DistrictView";
import { RetryLine } from "@/components/RemotePanels";
import { Skeleton } from "@/components/ui/Skeleton";
import { listedSourceNumbers } from "@/lib/citations";
import type { DistrictCrafts } from "@/lib/districtCraftsContract";
import { fetchDistrictCrafts } from "@/lib/learningApi";

export function useDistrict(lgd: number | null): Remote<DistrictCrafts> {
  const load = useMemo(() => (lgd === null ? null : () => fetchDistrictCrafts(lgd)), [lgd]);
  return useRemote(load);
}

export function DistrictPanel({ district, onClose }: { district: Remote<DistrictCrafts>; onClose: () => void }) {
  const reduce = useAppReducedMotion();
  const panel = useRef<HTMLDivElement | null>(null);
  const data = district.data;
  const numbers = useMemo(() => listedSourceNumbers(data?.sources ?? []), [data]);

  const reduceRef = useRef(reduce);
  useEffect(() => {
    reduceRef.current = reduce;
  }, [reduce]);
  useEffect(() => {
    if (data) panel.current?.scrollIntoView({ block: "nearest", behavior: reduceRef.current ? "auto" : "smooth" });
  }, [data]);

  return (
    <div ref={panel} className="mt-6 scroll-mt-28 border-t border-ink-1 pt-4" data-testid="district-panel">
      {district.failure ? (
        <RetryLine message={failureMessage(district.failure, "Couldn't open this district.")} onRetry={district.retry} />
      ) : data ? (
        <CitedReading sources={data.sources} numbers={numbers}>
          <DistrictView district={data} reduce={reduce} onClose={onClose} />
        </CitedReading>
      ) : (
        <Skeleton shape="lede" label="Opening the district" />
      )}
    </div>
  );
}
