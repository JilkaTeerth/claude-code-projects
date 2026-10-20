"use client";

import { type Level, type Difficulty, directionsUrl } from "@/lib/spots";
import type { LevelState } from "./MapJourney";
import { PinIcon, ClockIcon, CheckIcon, LockIcon } from "./icons";

const DIFF: Record<Difficulty, { label: string; color: string; tint: string; border: string }> = {
  easy: { label: "Easy", color: "var(--color-easy)", tint: "rgba(46,226,122,0.12)", border: "rgba(46,226,122,0.4)" },
  medium: { label: "Medium", color: "var(--color-medium)", tint: "rgba(246,196,83,0.12)", border: "rgba(246,196,83,0.4)" },
  hard: { label: "Hard", color: "var(--color-hard)", tint: "rgba(251,111,91,0.12)", border: "rgba(251,111,91,0.4)" },
};

interface Props {
  level: Level | null;
  state: LevelState;
  unlockHint?: string;
  onToggle: (id: string) => void;
  onClose: () => void;
}

export function LevelSheet({ level, state, unlockHint, onToggle, onClose }: Props) {
  const open = !!level;
  const d = level ? DIFF[level.difficulty] : DIFF.easy;
  const cleared = state === "cleared";
  const locked = state === "locked";

  return (
    <>
      {/* scrim */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-[1000] bg-black/40 transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <section
        role="dialog"
        aria-modal="true"
        className={`fixed inset-x-0 bottom-0 z-[1001] mx-auto w-full max-w-md transition-transform duration-300 ${
          open ? "translate-y-0" : "translate-y-[110%]"
        }`}
        style={{ transitionTimingFunction: "cubic-bezier(0.2,0.8,0.2,1)" }}
      >
        <div className="glass m-2 rounded-3xl border border-line-2 p-5 pb-6 shadow-2xl">
          <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-line-2" />

          {level && (
            <>
              <div className="flex items-start gap-3">
                <div
                  className="grid h-11 w-11 shrink-0 place-items-center rounded-full border text-sm font-bold"
                  style={{
                    borderColor: cleared ? "var(--color-go)" : locked ? "var(--color-line)" : d.color,
                    color: cleared ? "#04210f" : locked ? "var(--color-fog)" : d.color,
                    background: cleared ? "var(--color-go)" : "var(--color-ink-2)",
                  }}
                >
                  {cleared ? <CheckIcon className="h-5 w-5" /> : locked ? <LockIcon className="h-4 w-4" /> : level.n}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-fog">
                      Stage {level.tierIndex} · {level.tierName}
                    </span>
                  </div>
                  <h2 className="mt-0.5 text-balance text-lg font-bold leading-tight tracking-tight text-chalk">
                    {level.name}
                  </h2>
                  <p className="text-xs font-medium text-fog">{level.area}</p>
                </div>
                <span
                  className="shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold"
                  style={{ color: d.color, borderColor: d.border, background: d.tint }}
                >
                  {d.label}
                </span>
              </div>

              {locked ? (
                <div className="mt-4 flex items-center gap-2.5 rounded-xl border border-dashed border-line bg-ink-2/50 px-4 py-3 text-[13px] text-fog">
                  <LockIcon className="h-4 w-4 shrink-0" />
                  {unlockHint ?? "Clear earlier stages to unlock this level."}
                </div>
              ) : (
                <>
                  <p className="mt-4 text-[14px] leading-relaxed text-fog-2">{level.why}</p>

                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {level.skills.map((s) => (
                      <span
                        key={s}
                        className="rounded-md border border-line bg-ink-2/60 px-2 py-1 text-[11px] font-medium text-fog-2"
                      >
                        {s}
                      </span>
                    ))}
                  </div>

                  <div className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-ink-2/60 px-3 py-1.5 text-[12.5px] font-medium text-fog-2">
                    <ClockIcon className="h-4 w-4 text-go" />
                    Best time · {level.bestTime}
                  </div>

                  <div className="mt-5 flex gap-2.5">
                    <a
                      href={directionsUrl(level.lat, level.lng)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-line-2 bg-ink-2/70 py-3 text-sm font-semibold text-chalk transition-colors hover:border-fog/40"
                    >
                      <PinIcon className="h-4 w-4" />
                      Directions
                    </a>
                    <button
                      onClick={() => onToggle(level.id)}
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-sm font-bold transition-all"
                      style={
                        cleared
                          ? { background: "var(--color-go)", color: "#04210f" }
                          : { background: "var(--color-chalk)", color: "#0a0a0a" }
                      }
                    >
                      <CheckIcon className={`h-4 w-4 ${cleared ? "pop-check" : ""}`} />
                      {cleared ? "Cleared" : "Mark practiced"}
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </section>
    </>
  );
}
