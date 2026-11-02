"use client";

import React, { useEffect, useState } from "react";
import { 
  Plane, 
  MapPin, 
  Route as RouteIcon, 
  ShieldAlert, 
  Layers, 
  ArrowRight, 
  Camera, 
  CheckCircle2, 
  Sparkles,
  Smartphone,
  Download,
  FileCode,
  FileSpreadsheet,
  Navigation,
  Compass
} from "lucide-react";
import { 
  fetchFields, 
  fetchScan, 
  fetchHotspots, 
  fetchRoute, 
  fetchModelStatus,
  getExportGeoJsonUrl,
  getExportCsvUrl,
  getExportDatasetZipUrl,
  downloadFlightPlanKml,
  downloadFlightPlanQgc,
  Field, 
  Scan, 
  HotspotFeature, 
  RoutePlan, 
  ModelStatus 
} from "@/lib/api";

export default function DashboardPage() {
  const [fields, setFields] = useState<Field[]>([]);
  const [scan, setScan] = useState<Scan | null>(null);
  const [hotspots, setHotspots] = useState<HotspotFeature[]>([]);
  const [selectedHotspot, setSelectedHotspot] = useState<HotspotFeature | null>(null);
  const [route, setRoute] = useState<RoutePlan | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"triage" | "flightplan" | "exports">("triage");
  const [flightAlt, setFlightAlt] = useState<number>(35.0);

  useEffect(() => {
    async function loadData() {
      try {
        const fieldsData = await fetchFields();
        setFields(fieldsData);
        if (fieldsData.length > 0) {
          const scanData = await fetchScan("s_01");
          setScan(scanData);
          const spots = await fetchHotspots("s_01");
          setHotspots(spots.features);
          if (spots.features.length > 0) {
            setSelectedHotspot(spots.features[0]);
          }
          const routeData = await fetchRoute("s_01");
          setRoute(routeData);
          const modelData = await fetchModelStatus();
          setModel(modelData);
        }
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="h-16 border-b border-border bg-surface px-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-primary/20 p-2 rounded-lg border border-primary/40 text-primary">
            <Plane className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              AeroScout <span className="text-xs px-2 py-0.5 rounded bg-accent/20 text-accent border border-accent/30 uppercase tracking-wider font-semibold">Triage v1.0</span>
            </h1>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-surface-card border border-border p-1 rounded-xl text-xs">
          <button
            onClick={() => setActiveTab("triage")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === "triage" ? "bg-primary text-slate-950 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            Hotspot Triage & Route
          </button>
          <button
            onClick={() => setActiveTab("flightplan")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === "flightplan" ? "bg-primary text-slate-950 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            <Compass className="w-3.5 h-3.5" /> Drone Flight Plan
          </button>
          <button
            onClick={() => setActiveTab("exports")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === "exports" ? "bg-primary text-slate-950 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            <Download className="w-3.5 h-3.5" /> Export Data
          </button>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-card border border-border">
            <span className="text-slate-400">Scoring Engine:</span>
            <span className="font-mono text-accent font-semibold">{model?.active_version || "v1"}</span>
            <span className="text-slate-500">({model?.n_labels || 0} ground labels)</span>
          </div>
          <a 
            href="/scout/s_01" 
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/20 text-primary border border-primary/40 hover:bg-primary/30 transition-colors font-medium"
          >
            <Smartphone className="w-4 h-4" />
            Launch Mobile Scout App
          </a>
        </div>
      </header>

      {/* Main Studio Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left / Center Viewport */}
        <div className="flex-1 flex flex-col border-r border-border bg-[#070b14] relative">
          {activeTab === "flightplan" ? (
            /* Drone Flight Plan Sub-Panel */
            <div className="p-8 max-w-3xl mx-auto w-full my-auto space-y-6">
              <div className="bg-surface p-6 rounded-2xl border border-border shadow-xl">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-accent/20 border border-accent/30 flex items-center justify-center text-accent">
                    <Compass className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">Autonomous Drone Lawnmower Survey Planner</h2>
                    <p className="text-xs text-slate-400">Generates ready-to-fly DJI Pilot KML and QGroundControl Waypoint files.</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6 text-xs">
                  <div className="p-3 bg-surface-card rounded-xl border border-border">
                    <span className="text-slate-400">Target Field:</span>
                    <div className="text-sm font-semibold text-white mt-1">{fields[0]?.name || "Mandya Plot 4"}</div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">Coords: 11.0165° N, 76.8198° E</div>
                  </div>
                  <div className="p-3 bg-surface-card rounded-xl border border-border">
                    <span className="text-slate-400">Flight Altitude AGL:</span>
                    <div className="flex items-center gap-3 mt-1">
                      <input 
                        type="range" 
                        min="20" 
                        max="60" 
                        step="5" 
                        value={flightAlt} 
                        onChange={(e) => setFlightAlt(Number(e.target.value))}
                        className="flex-1 accent-primary" 
                      />
                      <span className="text-sm font-bold text-accent font-mono">{flightAlt} m</span>
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">Footprint: {(1.15 * flightAlt).toFixed(1)}m GSD ~3.0cm</div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <button
                    onClick={() => downloadFlightPlanKml(undefined, flightAlt)}
                    className="flex-1 py-3 rounded-xl bg-primary hover:bg-primary/90 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-colors shadow-lg"
                  >
                    <Download className="w-4 h-4" /> Download DJI Pilot KML
                  </button>
                  <button
                    onClick={() => downloadFlightPlanQgc(undefined, flightAlt)}
                    className="flex-1 py-3 rounded-xl bg-surface-card hover:bg-surface border border-border text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
                  >
                    <Download className="w-4 h-4 text-accent" /> Download QGC Waypoints (.wpl)
                  </button>
                </div>
              </div>
            </div>
          ) : activeTab === "exports" ? (
            /* Export Data Sub-Panel */
            <div className="p-8 max-w-3xl mx-auto w-full my-auto space-y-6">
              <div className="bg-surface p-6 rounded-2xl border border-border shadow-xl">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center text-primary">
                    <Download className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">GIS & Downstream ML Dataset Exports</h2>
                    <p className="text-xs text-slate-400">Download survey artifacts in standard geospatial and research formats.</p>
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  <a
                    href={getExportGeoJsonUrl("s_01")}
                    download
                    className="p-4 bg-surface-card hover:bg-surface border border-border rounded-xl flex items-center justify-between text-xs transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <FileCode className="w-5 h-5 text-accent" />
                      <div>
                        <div className="font-bold text-white group-hover:text-primary transition-colors">GeoJSON Hotspots FeatureCollection</div>
                        <div className="text-slate-400 text-[11px]">Hotspot polygons with all 7 explainability cue scores and tier classifications.</div>
                      </div>
                    </div>
                    <span className="px-3 py-1.5 rounded-lg bg-surface border border-border text-slate-300 font-mono text-[11px]">
                      .geojson
                    </span>
                  </a>

                  <a
                    href={getExportCsvUrl("s_01")}
                    download
                    className="p-4 bg-surface-card hover:bg-surface border border-border rounded-xl flex items-center justify-between text-xs transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <FileSpreadsheet className="w-5 h-5 text-primary" />
                      <div>
                        <div className="font-bold text-white group-hover:text-primary transition-colors">Tabular Summary Spreadsheet</div>
                        <div className="text-slate-400 text-[11px]">Ranked hotspots with areas, coordinates, biotic scores and feature vectors.</div>
                      </div>
                    </div>
                    <span className="px-3 py-1.5 rounded-lg bg-surface border border-border text-slate-300 font-mono text-[11px]">
                      .csv
                    </span>
                  </a>

                  <a
                    href={getExportDatasetZipUrl("s_01")}
                    download
                    className="p-4 bg-surface-card hover:bg-surface border border-border rounded-xl flex items-center justify-between text-xs transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <Sparkles className="w-5 h-5 text-warning" />
                      <div>
                        <div className="font-bold text-white group-hover:text-primary transition-colors">Downstream ML Training Dataset Bundle</div>
                        <div className="text-slate-400 text-[11px]">Standardized labels.csv + features.csv + metadata.json bundle for species model training.</div>
                      </div>
                    </div>
                    <span className="px-3 py-1.5 rounded-lg bg-surface border border-border text-slate-300 font-mono text-[11px]">
                      .zip
                    </span>
                  </a>
                </div>
              </div>
            </div>
          ) : (
            /* Default Hotspot Triage & Route View */
            <>
              {/* Map Layer Toolbar */}
              <div className="absolute top-4 left-4 z-10 flex gap-2">
                <div className="bg-surface/90 backdrop-blur-md border border-border p-1.5 rounded-lg shadow-lg flex items-center gap-1">
                  <button className="px-2.5 py-1 text-xs rounded bg-surface-card text-white font-medium border border-border flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-accent" /> Field RGB
                  </button>
                  <button className="px-2.5 py-1 text-xs rounded text-slate-400 hover:text-white transition-colors">
                    VARI Index
                  </button>
                  <button className="px-2.5 py-1 text-xs rounded text-slate-400 hover:text-white transition-colors">
                    Anomaly Heat
                  </button>
                </div>
                <div className="bg-surface/90 backdrop-blur-md border border-border px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-2 text-xs">
                  <span className="text-slate-400">Field:</span>
                  <span className="text-white font-medium">{fields[0]?.name || "Mandya Plot 4"}</span>
                  <span className="px-1.5 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 text-[10px] font-semibold uppercase">
                    {fields[0]?.data_source || "Synthetic"}
                  </span>
                </div>
              </div>

              {/* Interactive Map Visual Mock Area */}
              <div className="flex-1 flex items-center justify-center p-8 relative overflow-hidden">
                <div className="w-full max-w-2xl aspect-[4/3] rounded-2xl border border-border/80 bg-surface/40 p-6 flex flex-col justify-between relative shadow-2xl overflow-hidden">
                  <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40" />

                  <div className="relative z-10 flex justify-between items-start text-xs text-slate-400 font-mono">
                    <span>SW: 12.5200° N, 76.8950° E</span>
                    <span>NE: 12.5280° N, 76.9050° E</span>
                  </div>

                  {/* Hotspot Blobs on Mock Map */}
                  <div className="relative z-10 flex flex-wrap gap-4 items-center justify-around my-auto">
                    {hotspots.map((h) => {
                      const isSelected = selectedHotspot?.id === h.id;
                      const isRed = h.properties.tier === "red";
                      const isAmber = h.properties.tier === "amber";

                      return (
                        <button
                          key={h.id}
                          onClick={() => setSelectedHotspot(h)}
                          className={`relative p-3 rounded-2xl border transition-all duration-200 text-left ${
                            isSelected 
                              ? "scale-110 shadow-xl border-white ring-2 ring-primary bg-surface" 
                              : "border-border bg-surface-card/80 hover:border-slate-500"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className={`w-3 h-3 rounded-full animate-pulse ${
                              isRed ? "bg-danger" : isAmber ? "bg-warning" : "bg-slate-500"
                            }`} />
                            <span className="font-bold text-xs text-white">#{h.properties.rank}</span>
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono mt-1">
                            {h.properties.area_m2} m²
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {/* TSP Walk Summary Bar */}
                  <div className="relative z-10 bg-surface/90 backdrop-blur-md p-3 rounded-xl border border-border flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <RouteIcon className="w-4 h-4 text-primary" />
                      <span className="font-medium text-slate-200">Scout Route (2-opt TSP):</span>
                      <span className="font-mono text-white font-bold">{route?.distance_m}m</span>
                    </div>
                    <div className="flex items-center gap-4 text-slate-400">
                      <span>ETA: <strong className="text-white">{route?.eta_min} min</strong></span>
                      <span className="text-primary font-semibold">Walk Saved: {route?.saved_pct}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right Detail Pane */}
        <div className="w-96 bg-surface border-l border-border flex flex-col justify-between overflow-y-auto">
          <div className="p-5 space-y-6">
            {selectedHotspot ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div>
                    <h3 className="font-bold text-white flex items-center gap-2">
                      Hotspot #{selectedHotspot.properties.rank} ({selectedHotspot.id})
                      <span className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${
                        selectedHotspot.properties.tier === "red" 
                          ? "bg-danger/20 text-danger border border-danger/30" 
                          : "bg-warning/20 text-warning border border-warning/30"
                      }`}>
                        {selectedHotspot.properties.tier}
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5 font-mono">
                      Area: {selectedHotspot.properties.area_m2} m² · Biotic Score: {selectedHotspot.properties.biotic_score}
                    </p>
                  </div>
                </div>

                {/* Why Flagged Contribution Bars */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
                    <span>Evidence / Why Flagged</span>
                    <span className="text-[10px] text-slate-500 font-normal">Signed Contribution</span>
                  </h4>
                  <div className="space-y-2 text-xs">
                    {Object.entries(selectedHotspot.properties.contributions).map(([cue, val]) => (
                      <div key={cue}>
                        <div className="flex justify-between text-[11px] mb-0.5 text-slate-300 font-mono">
                          <span>{cue.replace("_", " ")}</span>
                          <span className={val > 0 ? "text-primary" : "text-slate-400"}>
                            {val > 0 ? `+${val}` : val}
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
                          <div 
                            className={`h-full ${val > 0 ? "bg-primary" : "bg-slate-600"}`} 
                            style={{ width: `${Math.min(Math.abs(val) * 60, 100)}%` }} 
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-2">
                  <a
                    href={`/scout/s_01`}
                    className="w-full py-2.5 px-4 rounded-xl bg-accent hover:bg-accent/90 text-slate-950 font-semibold text-xs flex items-center justify-center gap-2 transition-colors shadow-lg shadow-accent/20"
                  >
                    <Smartphone className="w-4 h-4" />
                    Inspect on Scout Phone App
                  </a>
                </div>
              </div>
            ) : null}
          </div>

          <div className="p-4 border-t border-border/60 text-[11px] text-slate-500 font-mono">
            Phase 6 P1 Features Active
          </div>
        </div>
      </div>
    </div>
  );
}
