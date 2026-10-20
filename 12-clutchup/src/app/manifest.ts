import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ClutchUp — Pune driving practice",
    short_name: "ClutchUp",
    description:
      "A map-based level journey of real Pune roads for learning manual driving — practice spots, timings, and progress.",
    start_url: "/",
    display: "standalone",
    background_color: "#07080a",
    theme_color: "#07080a",
    orientation: "portrait",
    categories: ["education", "navigation", "lifestyle"],
  };
}
