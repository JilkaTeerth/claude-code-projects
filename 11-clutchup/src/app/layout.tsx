import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ClutchUp — Learn manual driving in Pune, one road at a time",
  description:
    "A sequenced ladder of real Pune roads ranked Easy → Hard for learner drivers. Best practice times, what each spot trains, and your progress — no account, no tracking.",
  openGraph: {
    title: "ClutchUp",
    description:
      "Learn manual the way it actually works — a curriculum of real Pune practice roads, from empty riverside straights to peak-hour traffic.",
    type: "website",
  },
  appleWebApp: { capable: true, title: "ClutchUp", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  themeColor: "#07080a",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-full overflow-hidden overscroll-none">{children}</body>
    </html>
  );
}
