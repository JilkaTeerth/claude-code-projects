"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { LEVELS, PUNE_CENTER, type Level } from "@/lib/spots";

export type LevelState = "locked" | "open" | "current" | "cleared";

const STAGE_COLOR: Record<number, string> = {
  1: "#2ee27a",
  2: "#f6c453",
  3: "#ffa94d",
  4: "#fb6f5b",
};

function nodeHtml(level: Level, state: LevelState): string {
  const color = STAGE_COLOR[level.tierIndex] ?? "#8b95a3";
  const check =
    '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#04210f" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5 10 17.5 19 6.5"/></svg>';
  const lock =
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#8b95a3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';

  let inner: string;
  let style: string;
  if (state === "cleared") {
    inner = check;
    style = `background:#19e57f;border-color:#19e57f;color:#04210f;box-shadow:0 0 16px -2px rgba(25,229,127,.7)`;
  } else if (state === "locked") {
    inner = lock;
    style = `background:#0d0f13;border-color:#2c333d;color:#8b95a3;opacity:.85`;
  } else {
    inner = `${level.n}`;
    const glow = state === "current" ? `box-shadow:0 0 0 4px ${color}22, 0 0 18px -2px ${color}aa` : "";
    style = `background:#0d0f13;border-color:${color};color:${color};${glow}`;
  }

  const pulse = state === "current" ? '<span class="lvl-pulse"></span>' : "";
  return `<div class="lvl-node" style="${style}">${pulse}<span class="lvl-inner">${inner}</span></div>`;
}

function FitToJourney() {
  const map = useMap();
  useEffect(() => {
    const bounds = L.latLngBounds(LEVELS.map((l) => [l.lat, l.lng] as [number, number]));
    map.fitBounds(bounds, { padding: [70, 70], maxZoom: 14 });
  }, [map]);
  return null;
}

interface Props {
  states: Record<string, LevelState>;
  selectedId: string | null;
  onSelect: (level: Level) => void;
}

export default function MapJourney({ states, selectedId, onSelect }: Props) {
  const route = LEVELS.map((l) => [l.lat, l.lng] as [number, number]);

  return (
    <MapContainer
      center={PUNE_CENTER}
      zoom={13}
      zoomControl={false}
      className="absolute inset-0 h-full w-full"
      style={{ background: "#07080a" }}
    >
      <TileLayer
        // free CARTO dark basemap — no token required
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
      />

      {/* the journey route */}
      <Polyline
        positions={route}
        pathOptions={{ color: "#3a4150", weight: 3, opacity: 0.7, dashArray: "2 9", lineCap: "round" }}
      />

      {LEVELS.map((level) => {
        const state = states[level.id] ?? "locked";
        const selected = selectedId === level.id;
        const icon = L.divIcon({
          html: nodeHtml(level, state),
          className: `lvl-icon${selected ? " lvl-selected" : ""}`,
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        });
        return (
          <Marker
            key={level.id}
            position={[level.lat, level.lng]}
            icon={icon}
            eventHandlers={{ click: () => onSelect(level) }}
            zIndexOffset={selected ? 1000 : state === "current" ? 500 : 0}
          />
        );
      })}

      <FitToJourney />
    </MapContainer>
  );
}
