import "./globals.css";
import React from "react";

export const metadata = {
  title: "AeroScout — Aerial Hotspot Triage & Field Scout",
  description: "Detect, Triage, Ground-verify, Recalibrate",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}

