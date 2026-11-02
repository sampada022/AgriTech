"use client";

import React, { useEffect, useState } from "react";
import { 
  Camera, 
  MapPin, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles, 
  RefreshCw,
  Navigation,
  ArrowRight,
  Globe,
  PlusCircle
} from "lucide-react";
import { 
  fetchRoute, 
  submitObservation, 
  confirmObservation, 
  addManualHotspot,
  RoutePlan, 
  Observation 
} from "@/lib/api";
import { Language, getTranslation } from "@/lib/i18n";

export default function ScoutPage({ params }: { params: { id: string } }) {
  const scanId = params.id || "s_01";
  const [route, setRoute] = useState<RoutePlan | null>(null);
  const [currentStopIndex, setCurrentStopIndex] = useState(1);
  const [observation, setObservation] = useState<Observation | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [simulateWalk, setSimulateWalk] = useState(false);
  const [lang, setLang] = useState<Language>("en");
  const [manualAdded, setManualAdded] = useState(false);

  const t = (key: any) => getTranslation(lang, key);

  useEffect(() => {
    async function load() {
      try {
        const r = await fetchRoute(scanId);
        setRoute(r);
      } catch (err) {
        console.error("Failed to load scout route:", err);
      }
    }
    load();
  }, [scanId]);

  const currentWaypoint = route?.waypoints[currentStopIndex] || null;

  const handleCapturePhoto = async () => {
    setAnalyzing(true);
    try {
      const lat = currentWaypoint?.lat || 12.5232;
      const lon = currentWaypoint?.lon || 76.8962;
      const obs = await submitObservation(currentWaypoint?.hotspot_id || "h_01", lat, lon);
      setObservation(obs);
    } catch (err) {
      console.error(err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleConfirmLabel = async (label: string) => {
    if (!observation) return;
    try {
      const updated = await confirmObservation(observation.id, label);
      setObservation(updated);
      setConfirmed(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleNextStop = () => {
    setObservation(null);
    setConfirmed(false);
    if (route && currentStopIndex < route.waypoints.length - 1) {
      setCurrentStopIndex(currentStopIndex + 1);
    }
  };

  const handleAddManualSpot = async () => {
    try {
      const lat = (currentWaypoint?.lat || 11.0175) + 0.0001;
      const lon = (currentWaypoint?.lon || 76.8210) + 0.0001;
      await addManualHotspot(scanId, lat, lon, "Scout visual flag");
      setManualAdded(true);
      setTimeout(() => setManualAdded(false), 3500);
    } catch (err) {
      console.error("Manual add failed:", err);
    }
  };

  const toggleLanguage = () => {
    setLang(lang === "en" ? "kn" : "en");
  };

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col max-w-md mx-auto border-x border-border shadow-2xl">
      {/* Mobile Header with Language Toggle */}
      <div className="bg-surface p-4 border-b border-border flex items-center justify-between">
        <div>
          <span className="text-[10px] uppercase font-semibold text-accent tracking-wider">{t("app_title")}</span>
          <h1 className="text-base font-bold text-white">{t("mission_title")}</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleLanguage}
            className="px-2.5 py-1 text-xs rounded-lg bg-surface-card border border-border text-slate-200 flex items-center gap-1.5 hover:border-accent transition-colors font-medium"
            title="Toggle Kannada / English"
          >
            <Globe className="w-3.5 h-3.5 text-accent" />
            <span>{lang === "en" ? "ಕನ್ನಡ" : "EN"}</span>
          </button>
          <button 
            onClick={() => setSimulateWalk(!simulateWalk)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-all ${
              simulateWalk 
                ? "bg-primary/20 text-primary border-primary/40 font-semibold" 
                : "bg-surface-card text-slate-400 border-border"
            }`}
          >
            {simulateWalk ? t("simulating_walk") : t("simulate_walk")}
          </button>
        </div>
      </div>

      {/* Main Scout Flow */}
      <div className="flex-1 p-5 flex flex-col justify-between">
        <div>
          {/* Progress Banner */}
          <div className="bg-surface-card p-3 rounded-xl border border-border mb-4 flex items-center justify-between text-xs font-mono">
            <span>{t("stop_progress")} {currentStopIndex} {t("of")} {route?.waypoints.length ? route.waypoints.length - 1 : 1}</span>
            <span className="text-accent">{t("remaining_eta")} ~14m</span>
          </div>

          {/* Current Stop Target Card */}
          <div className="bg-surface p-5 rounded-2xl border border-border shadow-lg mb-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{t("active_target")}</span>
              <span className="px-2 py-0.5 rounded bg-danger/20 text-danger border border-danger/30 text-[10px] font-bold uppercase">
                {currentWaypoint?.tier === "amber" ? t("tier_amber") : currentWaypoint?.tier === "grey" ? t("tier_grey") : t("tier_red")}
              </span>
            </div>

            <h2 className="text-lg font-bold text-white mb-1">
              {currentWaypoint?.label || "Stop 1"} (Hotspot {currentWaypoint?.hotspot_id || "h_01"})
            </h2>
            <div className="text-xs text-slate-400 font-mono mb-4">
              Coords: {currentWaypoint?.lat.toFixed(4)}° N, {currentWaypoint?.lon.toFixed(4)}° E
            </div>

            <div className="p-3 bg-surface-card rounded-xl border border-border/80 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center text-primary">
                <Navigation className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <div className="text-xs font-bold text-white">{t("distance_ahead")}: 12 metres</div>
                <div className="text-[11px] text-slate-400">{t("within_arrival")}</div>
              </div>
            </div>

            {/* Manual Ground Hotspot Addition Button */}
            <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
              <button
                onClick={handleAddManualSpot}
                className="text-xs text-slate-400 hover:text-accent flex items-center gap-1.5 transition-colors"
              >
                <PlusCircle className="w-4 h-4 text-accent" />
                <span>{t("add_manual_hotspot")}</span>
              </button>
              {manualAdded && (
                <span className="text-[10px] text-primary flex items-center gap-1 animate-pulse">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Added to survey!
                </span>
              )}
            </div>
          </div>

          {/* Diagnosis Card */}
          {observation ? (
            <div className="bg-surface-card p-4 rounded-2xl border border-accent/40 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-accent flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" /> {t("ai_diagnosis_title")}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">{observation.diagnosis.image_quality} quality</span>
              </div>

              <div>
                <span className="text-xs text-slate-400">{t("top_candidate")}</span>
                <div className="text-sm font-bold text-white mt-0.5">
                  {observation.diagnosis.candidates[0].name}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <div className="h-1.5 flex-1 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary" 
                      style={{ width: `${observation.diagnosis.candidates[0].probability * 100}%` }} 
                    />
                  </div>
                  <span className="text-[11px] font-mono text-primary font-bold">
                    {Math.round(observation.diagnosis.candidates[0].probability * 100)}%
                  </span>
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-surface border border-border text-[11px] space-y-1 text-slate-300">
                <div className="font-semibold text-slate-200">{t("field_symptoms")}</div>
                <div>• {observation.diagnosis.observed_symptoms.join(", ")}</div>
                <div className="font-semibold text-slate-200 pt-1">{t("ipm_recommendation")}</div>
                <div>• {observation.diagnosis.actions_ipm[0]}</div>
              </div>

              {confirmed ? (
                <div className="p-3 bg-primary/20 border border-primary/40 rounded-xl text-primary text-xs font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Ground label confirmed. Model recalibrated v1 → v2!
                  </span>
                </div>
              ) : (
                <div className="pt-2 flex gap-2">
                  <button
                    onClick={() => handleConfirmLabel("pest")}
                    className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary/90 text-slate-950 font-bold text-xs transition-colors shadow-lg"
                  >
                    {t("confirm_button")}
                  </button>
                  <button
                    onClick={() => handleConfirmLabel("false_alarm")}
                    className="px-3 py-2.5 rounded-xl bg-surface border border-border text-slate-400 hover:text-white text-xs"
                  >
                    {t("false_alarm")}
                  </button>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Bottom Actions */}
        <div className="pt-4 space-y-2">
          {!observation ? (
            <button
              onClick={handleCapturePhoto}
              disabled={analyzing}
              className="w-full py-3.5 rounded-2xl bg-primary hover:bg-primary/90 text-slate-950 font-bold text-sm flex items-center justify-center gap-2 transition-colors shadow-lg shadow-primary/20 disabled:opacity-50"
            >
              {analyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  {t("analyzing_photo")}
                </>
              ) : (
                <>
                  <Camera className="w-5 h-5" />
                  {t("take_leaf_photo")}
                </>
              )}
            </button>
          ) : (
            <button
              onClick={handleNextStop}
              className="w-full py-3 rounded-2xl bg-surface-card hover:bg-surface border border-border text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
            >
              {t("advance_next")}
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          <div className="text-center">
            <a href="/" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
              {t("return_dashboard")}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
