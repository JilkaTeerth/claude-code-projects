"use client";

import { APP, TOTAL_SPOTS } from "@/lib/spots";
import { RouteIcon, FlagIcon, RefreshIcon } from "./icons";

interface Props {
  count: number;
  stageLabel: string;
  graduated: boolean;
  onReset: () => void;
}

export function MapHUD({ count, stageLabel, graduated, onReset }: Props) {
  const pct = TOTAL_SPOTS === 0 ? 0 : Math.round((count / TOTAL_SPOTS) * 100);

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-[900] p-3">
      <div className="glass pointer-events-auto mx-auto flex max-w-md items-center gap-3 rounded-2xl border border-line px-4 py-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ink-2 ring-1 ring-line">
          <RouteIcon className="h-5 w-5 text-go" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-extrabold tracking-tight text-chalk">{APP.name}</span>
            <span className="truncate text-[11px] font-semibold uppercase tracking-wide text-fog">
              {APP.city}
            </span>
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] font-medium text-fog">
            {graduated ? (
              <span className="inline-flex items-center gap-1 text-go">
                <FlagIcon className="h-3.5 w-3.5" /> Journey complete
              </span>
            ) : (
              <span className="truncate">Next · {stageLabel}</span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1">
          <div className="text-sm font-extrabold tabular-nums text-chalk">
            {count}
            <span className="text-xs font-bold text-fog">/{TOTAL_SPOTS}</span>
          </div>
          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-go transition-[width] duration-500"
              style={{ width: `${pct}%`, boxShadow: "0 0 8px rgba(25,229,127,.6)" }}
            />
          </div>
        </div>

        {count > 0 && (
          <button
            onClick={onReset}
            aria-label="Reset progress"
            className="pointer-events-auto grid h-8 w-8 shrink-0 place-items-center rounded-lg text-fog transition-colors hover:bg-white/5 hover:text-fog-2"
          >
            <RefreshIcon className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
