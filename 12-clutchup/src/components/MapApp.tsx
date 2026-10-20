"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { LEVELS, TIERS, TOTAL_SPOTS, type Level } from "@/lib/spots";
import { useProgress } from "@/lib/useProgress";
import { MapHUD } from "./MapHUD";
import { LevelSheet } from "./LevelSheet";
import type { LevelState } from "./MapJourney";

// Leaflet touches `window` on import — load the map client-side only.
const MapJourney = dynamic(() => import("./MapJourney"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 grid place-items-center bg-ink">
      <div className="flex items-center gap-2 text-sm font-medium text-fog">
        <span className="h-2 w-2 animate-ping rounded-full bg-go" />
        Loading Pune…
      </div>
    </div>
  ),
});

export default function MapApp() {
  const { has, toggle, reset, count } = useProgress();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Which tiers are unlocked (>= half of previous tier cleared).
  const tierUnlocked = useMemo(() => {
    const map = new Map<string, boolean>();
    TIERS.forEach((tier, i) => {
      if (i === 0) return map.set(tier.id, true);
      const prev = TIERS[i - 1];
      const clearedPrev = prev.spots.filter((s) => has(s.id)).length;
      map.set(tier.id, clearedPrev >= Math.ceil(prev.spots.length / 2));
    });
    return map;
  }, [has]);

  // First uncleared level in an unlocked tier = the "current" objective.
  const currentLevel = useMemo(
    () => LEVELS.find((l) => tierUnlocked.get(l.tierId) && !has(l.id)),
    [tierUnlocked, has]
  );

  const states: Record<string, LevelState> = useMemo(() => {
    const out: Record<string, LevelState> = {};
    for (const l of LEVELS) {
      if (has(l.id)) out[l.id] = "cleared";
      else if (!tierUnlocked.get(l.tierId)) out[l.id] = "locked";
      else if (currentLevel && l.id === currentLevel.id) out[l.id] = "current";
      else out[l.id] = "open";
    }
    return out;
  }, [has, tierUnlocked, currentLevel]);

  const selected = LEVELS.find((l) => l.id === selectedId) ?? null;
  const graduated = count === TOTAL_SPOTS;

  const unlockHintFor = (level: Level | null): string | undefined => {
    if (!level) return undefined;
    const i = TIERS.findIndex((t) => t.id === level.tierId);
    if (i <= 0) return undefined;
    const prev = TIERS[i - 1];
    const clearedPrev = prev.spots.filter((s) => has(s.id)).length;
    const need = Math.ceil(prev.spots.length / 2) - clearedPrev;
    return `Clear ${need} more in “${prev.name}” to unlock this level.`;
  };

  return (
    <div className="relative h-dvh w-full overflow-hidden">
      <MapJourney states={states} selectedId={selectedId} onSelect={(l) => setSelectedId(l.id)} />

      <MapHUD
        count={count}
        graduated={graduated}
        stageLabel={currentLevel ? `Stage ${currentLevel.tierIndex} · ${currentLevel.name}` : "All clear"}
        onReset={() => {
          reset();
          setSelectedId(null);
        }}
      />

      <LevelSheet
        level={selected}
        state={selected ? states[selected.id] : "locked"}
        unlockHint={unlockHintFor(selected)}
        onToggle={toggle}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
