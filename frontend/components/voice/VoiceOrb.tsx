"use client";

import { useEffect } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { AudioLines, LoaderCircle, Mic, MicOff, Send } from "lucide-react";

import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import type { Activity } from "@/lib/voiceCall";
import { cn } from "@/lib/utils";

const LIVE: ReadonlySet<Activity> = new Set(["recording", "listening", "speaking"]);

const RING: Record<Activity | "idle", string> = {
  connecting: "ring-purple-100 dark:ring-purple-900",
  thinking: "ring-purple-100 dark:ring-purple-900",
  ready: "ring-purple-100 dark:ring-purple-900",
  recording: "ring-purple-300 dark:ring-purple-500",
  listening: "ring-purple-300 dark:ring-purple-500",
  speaking: "ring-purple-400 dark:ring-purple-400",
  idle: "ring-line-200"
};

function OrbIcon({ activity, pressable }: { activity: Activity | null; pressable: boolean }) {
  if (activity === null) return <MicOff className="h-7 w-7" aria-hidden />;
  if (activity === "connecting" || activity === "thinking") return <LoaderCircle className="h-7 w-7 motion-safe:animate-spin" aria-hidden />;
  if (activity === "speaking") return <AudioLines className="h-7 w-7" aria-hidden />;
  if (activity === "recording" && pressable) return <Send className="h-7 w-7" aria-hidden />;
  return <Mic className="h-7 w-7" aria-hidden />;
}

export function VoiceOrb({
  activity,
  level,
  label,
  onPress
}: {
  activity: Activity | null;
  level: () => number;
  label: string;
  onPress?: () => void;
}) {
  const reduce = useAppReducedMotion();
  const raw = useMotionValue(0);
  const smooth = useSpring(raw, { stiffness: 260, damping: 30 });
  const scale = useTransform(smooth, [0, 1], [1, 1.28]);
  const live = activity !== null && LIVE.has(activity);

  useEffect(() => {
    if (!live || reduce) {
      raw.set(0);
      return;
    }
    let frame = requestAnimationFrame(function tick() {
      raw.set(level());
      frame = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frame);
  }, [level, live, raw, reduce]);

  const core = cn(
    "relative grid h-24 w-24 place-items-center rounded-full ring-8 transition-colors",
    RING[activity ?? "idle"],
    activity === null ? "bg-surface-50 text-ink-500" : activity === "ready" ? "bg-purple-700 text-white" : "bg-purple-950 text-purple-100"
  );
  const halo = <motion.span aria-hidden style={{ scale }} className="absolute inset-0 rounded-full bg-purple-500/15" />;

  if (onPress && activity !== null) {
    return (
      <button type="button" onClick={onPress} aria-label={label} className={cn(core, activity === "ready" && "hover:bg-purple-800")} data-testid="voice-orb">
        {halo}
        <span className="relative">
          <OrbIcon activity={activity} pressable />
        </span>
      </button>
    );
  }
  return (
    <span className={core} data-testid="voice-orb">
      {halo}
      <span className="relative">
        <OrbIcon activity={activity} pressable={false} />
      </span>
    </span>
  );
}
