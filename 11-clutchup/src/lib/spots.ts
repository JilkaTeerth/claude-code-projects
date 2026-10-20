// ClutchUp — Pune manual-transmission practice spots.
//
// SEED DATA: spots are based on Teerth's own learning journey + plausible Pune
// locations and approximate coordinates. VERIFY on the ground before trusting
// (timings + exact pins shift with construction/season). No DB, no API — this
// file is the whole source of truth. Edit freely.

export type Difficulty = "easy" | "medium" | "hard";

export type Skill =
  | "Clutch control"
  | "Hill start"
  | "U-turns"
  | "Lane discipline"
  | "Gear shifting"
  | "Parking"
  | "Junctions & give-way"
  | "Merging"
  | "Signals & stop-start"
  | "Slow crawl";

export interface Spot {
  id: string;
  name: string;
  area: string;
  difficulty: Difficulty;
  skills: Skill[];
  bestTime: string;
  why: string;
  mapsQuery: string;
  lat: number;
  lng: number;
}

export interface Tier {
  id: string;
  index: number;
  name: string;
  tagline: string;
  builds: string;
  difficulty: Difficulty;
  spots: Spot[];
}

export const APP = {
  name: "ClutchUp",
  tagline: "Learn manual the way it actually works — one road at a time.",
  city: "Pune",
} as const;

/** Rough geographic centre of the journey, for the initial map view. */
export const PUNE_CENTER: [number, number] = [18.524, 73.905];

export function mapsUrl(query: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

export function directionsUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
}

export const TIERS: Tier[] = [
  {
    id: "open-road",
    index: 1,
    name: "Open Road",
    tagline: "Get the car moving without fear.",
    builds: "Releasing the clutch smoothly, 1st→2nd, steering confidence, U-turns.",
    difficulty: "easy",
    spots: [
      {
        id: "kalyani-riverside",
        name: "Kalyani Nagar Riverside Stretch",
        area: "Kalyani Nagar",
        difficulty: "easy",
        skills: ["U-turns", "Lane discipline", "Clutch control"],
        bestTime: "Sun 7–9 AM",
        why: "Wide, near-empty road with a long runway — perfect for drilling U-turns and finding the clutch's bite point.",
        mapsQuery: "Riverside Road, Kalyani Nagar, Pune",
        lat: 18.5472,
        lng: 73.9083,
      },
      {
        id: "aga-khan-road",
        name: "Aga Khan Palace Road",
        area: "Kalyani Nagar / Nagar Road",
        difficulty: "easy",
        skills: ["Gear shifting", "Lane discipline"],
        bestTime: "Weekday 6:30–8 AM",
        why: "Long, calm straights to settle into 2nd–3rd gear and practise smooth shifting before anything gets busy.",
        mapsQuery: "Aga Khan Palace Road, Pune",
        lat: 18.5527,
        lng: 73.9015,
      },
      {
        id: "amanora-outer-ring",
        name: "Amanora Outer Ring Road",
        area: "Hadapsar",
        difficulty: "easy",
        skills: ["U-turns", "Clutch control", "Slow crawl"],
        bestTime: "Sun morning",
        why: "Broad township roads with gentle curves and almost no through-traffic on weekend mornings.",
        mapsQuery: "Amanora Park Town, Hadapsar, Pune",
        lat: 18.5175,
        lng: 73.9405,
      },
    ],
  },
  {
    id: "light-traffic",
    index: 2,
    name: "Light Society Traffic",
    tagline: "Share the road — at low stakes.",
    builds: "Slow crawl, give-way at junctions, speed breakers, basic parking, reading pedestrians.",
    difficulty: "medium",
    spots: [
      {
        id: "magarpatta-inner",
        name: "Magarpatta City Inner Circle",
        area: "Hadapsar",
        difficulty: "medium",
        skills: ["Slow crawl", "Junctions & give-way", "Clutch control"],
        bestTime: "Weekday 11 AM–4 PM",
        why: "A self-contained township loop — light, slow, predictable traffic and a roundabout to learn give-way without the chaos.",
        mapsQuery: "Magarpatta City, Hadapsar, Pune",
        lat: 18.5158,
        lng: 73.9275,
      },
      {
        id: "amanora-internal",
        name: "Amanora Township Internal Roads",
        area: "Hadapsar",
        difficulty: "medium",
        skills: ["Parking", "Slow crawl", "Junctions & give-way"],
        bestTime: "Weekday afternoon",
        why: "Speed breakers, marked bays and gentle 4-way stops — ideal for first parking attempts and controlled stop-start.",
        mapsQuery: "Amanora Town Centre, Hadapsar, Pune",
        lat: 18.5192,
        lng: 73.9398,
      },
      {
        id: "kp-lanes",
        name: "Koregaon Park Lanes (North Main fringe)",
        area: "Koregaon Park",
        difficulty: "medium",
        skills: ["Lane discipline", "Junctions & give-way", "Slow crawl"],
        bestTime: "Weekday 11 AM–1 PM",
        why: "Quiet tree-lined lanes with narrow give-way moments — builds judgement before you touch a main road.",
        mapsQuery: "Lane 5, Koregaon Park, Pune",
        lat: 18.5362,
        lng: 73.8939,
      },
    ],
  },
  {
    id: "hills-clutch",
    index: 3,
    name: "Hills & Clutch",
    tagline: "Where manual drivers are made.",
    builds: "Hill starts without rolling back, half-clutch holds, clutch–accelerator balance on a gradient.",
    difficulty: "medium",
    spots: [
      {
        id: "mundhwa-magarpatta-hill",
        name: "Mundhwa → Magarpatta Incline",
        area: "Mundhwa",
        difficulty: "medium",
        skills: ["Hill start", "Clutch control", "Signals & stop-start"],
        bestTime: "Weekday 10 AM–12 PM",
        why: "The make-or-break gradient — a real incline with room to practise rolling-stop hill starts and half-clutch holds.",
        mapsQuery: "Mundhwa to Magarpatta Road, Pune",
        lat: 18.5290,
        lng: 73.9285,
      },
      {
        id: "taljai-approach",
        name: "Taljai Hill Approach Roads",
        area: "Dhankawadi / Sahakar Nagar",
        difficulty: "hard",
        skills: ["Hill start", "Clutch control"],
        bestTime: "Sun 7–9 AM",
        why: "Steeper, quieter inclines to graduate your hill starts — enough slope to feel the car want to roll, little enough traffic to fail safely.",
        mapsQuery: "Taljai Hill, Pune",
        lat: 18.4875,
        lng: 73.8530,
      },
      {
        id: "law-college-incline",
        name: "Law College Road Incline",
        area: "Erandwane",
        difficulty: "medium",
        skills: ["Hill start", "Signals & stop-start", "Clutch control"],
        bestTime: "Weekday 2–4 PM",
        why: "A moderate urban slope with signals — practise holding the car on the clutch at a red light on a gradient.",
        mapsQuery: "Law College Road, Erandwane, Pune",
        lat: 18.5128,
        lng: 73.8345,
      },
    ],
  },
  {
    id: "peak-traffic",
    index: 4,
    name: "Peak Traffic",
    tagline: "The real thing. Your graduation.",
    builds: "Merging, signal reading, holding your line in dense mixed traffic, two-wheeler awareness.",
    difficulty: "hard",
    spots: [
      {
        id: "hadapsar-junction",
        name: "Hadapsar / Magarpatta Main Junction",
        area: "Hadapsar",
        difficulty: "hard",
        skills: ["Signals & stop-start", "Merging", "Junctions & give-way"],
        bestTime: "Weekday 6–8 PM (when ready)",
        why: "A busy signalled junction with heavy merging — the first real test of everything you've built, on roads you already know.",
        mapsQuery: "Hadapsar Gadital, Pune",
        lat: 18.5012,
        lng: 73.9412,
      },
      {
        id: "kharadi-bypass",
        name: "Kharadi Bypass / EON IT Park",
        area: "Kharadi",
        difficulty: "hard",
        skills: ["Merging", "Lane discipline", "Signals & stop-start"],
        bestTime: "Weekday evening",
        why: "Fast-moving merging traffic around the IT park — teaches confident lane changes and keeping pace without panic.",
        mapsQuery: "EON IT Park, Kharadi, Pune",
        lat: 18.5512,
        lng: 73.9435,
      },
      {
        id: "kp-north-main",
        name: "Koregaon Park North Main Road",
        area: "Koregaon Park",
        difficulty: "hard",
        skills: ["Slow crawl", "Junctions & give-way", "Merging"],
        bestTime: "Weekend evening",
        why: "Dense mixed traffic — cars, bikes, pedestrians, autos all at once. If you can hold your line here, you can drive Pune.",
        mapsQuery: "North Main Road, Koregaon Park, Pune",
        lat: 18.5378,
        lng: 73.8948,
      },
      {
        id: "pune-station-bund",
        name: "Pune Station / Bund Garden Road",
        area: "Central Pune",
        difficulty: "hard",
        skills: ["Signals & stop-start", "Merging", "Slow crawl"],
        bestTime: "Only once everything else is cleared",
        why: "Maximum-chaos final boss — relentless signals, autos and two-wheeler swarms. The certificate road.",
        mapsQuery: "Pune Railway Station, Pune",
        lat: 18.5285,
        lng: 73.8743,
      },
    ],
  },
];

export interface Level extends Spot {
  /** 1-based position across the whole journey. */
  n: number;
  tierId: string;
  tierIndex: number;
  tierName: string;
}

export const LEVELS: Level[] = TIERS.flatMap((t) =>
  t.spots.map((s) => ({
    ...s,
    n: 0,
    tierId: t.id,
    tierIndex: t.index,
    tierName: t.name,
  }))
).map((lvl, i) => ({ ...lvl, n: i + 1 }));

export const ALL_SPOTS: Spot[] = TIERS.flatMap((t) => t.spots);
export const TOTAL_SPOTS = ALL_SPOTS.length;
