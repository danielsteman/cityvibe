"use client";

import { motion } from "framer-motion";
import {
  Cloud,
  CloudRain,
  Sun,
  Wind,
  Snowflake,
  CloudFog,
  MapPin,
  Droplets,
  CloudLightning,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type WeatherType = "rain" | "sun" | "wind" | "snow" | "clouds" | "fog" | "storm" | "clear";

export interface WeatherEventData {
  id: string;
  location: string;
  weatherType: WeatherType;
  temperature: string;
  condition: string;
  precipitation?: string;
  humidity?: string;
  windSpeed?: string;
}

// ------------------------------------------------------------------
// CONFIG: Apple-style Color Palettes & Icons
// ------------------------------------------------------------------
const weatherConfig: Record<
  WeatherType,
  {
    icon: any;
    backgrounds: string[];
    textColor: string;
  }
> = {
  sun: {
    icon: Sun,
    backgrounds: ["bg-sky-500", "bg-blue-400", "bg-amber-300"],
    textColor: "text-white",
  },
  clear: {
    icon: Sun,
    backgrounds: ["bg-blue-600", "bg-sky-500", "bg-cyan-400"],
    textColor: "text-white",
  },
  rain: {
    icon: CloudRain,
    backgrounds: ["bg-slate-900", "bg-blue-900", "bg-slate-800"],
    textColor: "text-blue-50",
  },
  storm: {
    icon: CloudLightning,
    backgrounds: ["bg-slate-950", "bg-indigo-950", "bg-slate-900"],
    textColor: "text-indigo-50",
  },
  snow: {
    icon: Snowflake,
    // Cool, icy blues
    backgrounds: ["bg-slate-600", "bg-slate-500", "bg-gray-400"],
    textColor: "text-white",
  },
  clouds: {
    icon: Cloud,
    backgrounds: ["bg-slate-600", "bg-slate-500", "bg-gray-400"],
    textColor: "text-white",
  },
  fog: {
    icon: CloudFog,
    backgrounds: ["bg-slate-700", "bg-gray-600", "bg-slate-600"],
    textColor: "text-gray-100",
  },
  wind: {
    icon: Wind,
    // UPDATED: Now Blue-ish/Sky tones instead of Teal
    backgrounds: ["bg-sky-600", "bg-blue-500", "bg-indigo-400"],
    textColor: "text-white",
  },
};

// ------------------------------------------------------------------
// ANIMATIONS: Organic Fluid Backgrounds & Particles
// ------------------------------------------------------------------

const FluidBackground = ({ type }: { type: WeatherType }) => {
  const config = weatherConfig[type];

  return (
    <div className="absolute inset-0 z-0 overflow-hidden bg-slate-950">
      {/* Base Layer */}
      <div
        className={cn(
          "absolute inset-0 opacity-100 transition-colors duration-1000",
          config.backgrounds[0]
        )}
      />

      {/* Moving Blobs */}
      <motion.div
        animate={{ scale: [1, 1.2, 1], x: [-20, 20, -20], y: [-20, 20, -20] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        className={cn(
          "absolute -top-1/2 -left-1/2 w-[150%] h-[150%] rounded-full blur-[80px] opacity-60 mix-blend-overlay",
          config.backgrounds[1]
        )}
      />
      <motion.div
        animate={{ scale: [1.2, 1, 1.2], x: [20, -20, 20], y: [20, -20, 20] }}
        transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
        className={cn(
          "absolute -bottom-1/2 -right-1/2 w-[150%] h-[150%] rounded-full blur-[80px] opacity-60 mix-blend-overlay",
          config.backgrounds[2]
        )}
      />

      {/* Special sun glow */}
      {type === "sun" && (
        <motion.div
          animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 4, repeat: Infinity }}
          className="absolute top-[-10%] right-[-10%] w-64 h-64 bg-yellow-300 rounded-full blur-[80px] opacity-40 mix-blend-screen"
        />
      )}
    </div>
  );
};

const ParticleAnimation = ({ type }: { type: WeatherType }) => {
  switch (type) {
    case "rain":
    case "storm":
      return (
        <div className="absolute inset-0 z-[1] pointer-events-none">
          {Array.from({ length: 40 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-[2px] bg-white/40 rounded-full"
              style={{
                height: Math.random() * 25 + 10 + "px",
                left: Math.random() * 100 + "%",
                top: -30,
              }}
              animate={{ y: ["-10vh", "100vh"] }}
              transition={{
                duration: Math.random() * 0.4 + 0.3,
                repeat: Infinity,
                delay: Math.random() * 2,
                ease: "linear",
              }}
            />
          ))}
          {type === "storm" && (
            <motion.div
              className="absolute inset-0 bg-white mix-blend-soft-light"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0, 0.4, 0, 0, 0.2, 0] }}
              transition={{
                repeat: Infinity,
                duration: 4,
                delay: 1,
                repeatDelay: Math.random() * 3,
              }}
            />
          )}
        </div>
      );

    case "snow":
      return (
        <div className="absolute inset-0 z-[1] pointer-events-none">
          {/* UPDATED: Vertical falling snow (just like rain logic, but distinct shape) */}
          {Array.from({ length: 50 }).map((_, i) => {
            const size = Math.random() * 4 + 2;
            return (
              <motion.div
                key={i}
                className="absolute bg-white rounded-full opacity-90"
                style={{
                  width: size,
                  height: size,
                  left: Math.random() * 100 + "%",
                  top: -20,
                  filter: "blur(0.5px)",
                }}
                // Falling straight down
                animate={{ y: ["-10vh", "100vh"] }}
                transition={{
                  // Slower than rain
                  duration: Math.random() * 2 + 2,
                  repeat: Infinity,
                  delay: Math.random() * 3,
                  ease: "linear",
                }}
              />
            );
          })}
        </div>
      );

    case "clouds":
      return (
        <div className="absolute inset-0 z-[1] overflow-hidden pointer-events-none">
          {/*
               PERFECTIONIZED CLOUD LAYERS
               We construct distinct "Cloud Banks" using composite shapes for volume.
            */}

          {/* 1. Background Haze (The diffuse overcast layer) */}
          <motion.div
            className="absolute -top-10 -right-20 w-[120%] h-64 bg-white/10 blur-[60px]"
            animate={{ x: [-20, 20, -20] }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* 2. Top-Right Heavy Cloud Bank (Slow, distant) */}
          <motion.div
            className="absolute top-[-50px] -right-[100px] opacity-40"
            animate={{ x: [0, -40, 0] }}
            transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
          >
            {/* Creating a complex cloud shape with multiple circles */}
            <div className="relative">
              <div className="w-64 h-64 bg-slate-300 rounded-full blur-[50px]" />
              <div className="absolute top-20 right-10 w-48 h-48 bg-gray-200 rounded-full blur-[40px]" />
            </div>
          </motion.div>

          {/* 3. Mid-Left Cloud Bank (Medium speed, brighter edges) */}
          <motion.div
            className="absolute top-[10%] -left-[100px] opacity-30"
            animate={{ x: [-20, 50, -20] }}
            transition={{ duration: 30, repeat: Infinity, ease: "easeInOut", delay: 1 }}
          >
            <div className="relative">
              <div className="w-72 h-56 bg-white rounded-full blur-[60px]" />
              <div className="absolute -top-10 left-20 w-40 h-40 bg-slate-200 rounded-full blur-[40px]" />
            </div>
          </motion.div>

          {/* 4. Foreground "Low Hanging" Wisps (Faster, passing through) */}
          <motion.div
            className="absolute bottom-[-20px] left-[-20%] w-[140%] h-32 bg-white/5 blur-[40px] rounded-[100%]"
            animate={{ x: ["-10%", "10%", "-10%"] }}
            transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      );

    case "sun":
    case "clear":
      return (
        <div className="absolute inset-0 z-[1] overflow-hidden pointer-events-none">
          <motion.div
            className="absolute -top-[40%] -right-[40%] w-[120%] h-[120%] opacity-20"
            style={{
              background:
                "conic-gradient(from 0deg, transparent 0deg, rgba(255, 255, 255, 0.5) 20deg, transparent 40deg)",
              filter: "blur(30px)",
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="absolute top-[15%] right-[15%] w-32 h-32 bg-white/20 rounded-full blur-[50px]"
            animate={{ opacity: [0.3, 0.6, 0.3], scale: [1, 1.1, 1] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      );

    case "wind":
      return (
        <div className="absolute inset-0 z-[1] overflow-hidden pointer-events-none">
          {/* White Wind Streaks against the new Blue background */}
          {Array.from({ length: 12 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute h-[2px] bg-gradient-to-r from-transparent via-white/40 to-transparent"
              style={{
                width: Math.random() * 150 + 100 + "px",
                top: Math.random() * 100 + "%",
                left: -200,
              }}
              animate={{ x: ["-50%", "300%"] }}
              transition={{
                duration: Math.random() * 1.5 + 0.5,
                repeat: Infinity,
                delay: Math.random() * 2,
                ease: "linear",
              }}
            />
          ))}
        </div>
      );

    case "fog":
      return (
        <div className="absolute inset-0 z-[1] overflow-hidden pointer-events-none">
          {/*
              THICKER FOG IMPLEMENTATION
              Increased opacities (e.g., bg-white/90) and added an overlay wash to simulate density.
            */}

          {/* Layer 1: Dense Bottom Fog (Very opaque) */}
          <motion.div
            className="absolute bottom-[-20px] -left-[20%] w-[150%] h-48 bg-white/90 blur-[60px] rounded-[50%]"
            animate={{ x: ["-10%", "10%", "-10%"] }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Layer 2: Thick Mid-level Haze */}
          <motion.div
            className="absolute top-[30%] -right-[20%] w-[150%] h-40 bg-slate-100/60 blur-[70px] rounded-[50%]"
            animate={{ x: ["10%", "-10%", "10%"] }}
            transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Layer 3: Ambient Wash (Covers the whole card to reduce contrast) */}
          <motion.div
            className="absolute inset-0 bg-white/10"
            animate={{ opacity: [0.2, 0.4, 0.2] }}
            transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Layer 4: High Density Pulse */}
          <motion.div
            className="absolute top-0 left-0 w-full h-full bg-stone-200/40 blur-[90px]"
            animate={{ opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Layer 5: Passing Low Cloud (Fastest, very white) */}
          <motion.div
            className="absolute bottom-20 -left-full w-full h-24 bg-white/50 blur-[50px]"
            animate={{ x: ["0%", "250%"] }}
            transition={{ duration: 15, repeat: Infinity, ease: "linear", delay: 1 }}
          />
        </div>
      );

    default:
      return null;
  }
};

// ------------------------------------------------------------------
// COMPONENT: Weather Event Card
// ------------------------------------------------------------------

export const WeatherEventCard = ({ event }: { event: WeatherEventData }) => {
  const config = weatherConfig[event.weatherType] || weatherConfig.clear;
  const WeatherIcon = config.icon;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="relative w-full max-w-sm mx-auto h-[420px] rounded-[32px] overflow-hidden shadow-2xl border border-white/10"
    >
      {/* 1. Dynamic Background Layer */}
      <FluidBackground type={event.weatherType} />

      {/* 2. Particle Layer */}
      <ParticleAnimation type={event.weatherType} />

      {/* 3. Glass Reflection Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/10 to-transparent z-[2] pointer-events-none" />

      {/* 4. Content Layer */}
      <div
        className={cn("relative z-10 flex flex-col justify-between h-full p-6", config.textColor)}
      >
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="flex flex-col">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-1.5"
            >
              <MapPin className="w-3.5 h-3.5 opacity-70" />
              <span className="text-sm font-semibold tracking-wide uppercase opacity-80">
                {event.location}
              </span>
            </motion.div>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-xs font-medium opacity-60 mt-1"
            >
              Today, 10:23 AM
            </motion.div>
          </div>

          <motion.div
            initial={{ scale: 0, rotate: -20 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring" }}
            className="bg-white/20 backdrop-blur-md p-2 rounded-full shadow-lg border border-white/20"
          >
            <WeatherIcon className="w-6 h-6" />
          </motion.div>
        </div>

        {/* Center - Temperature */}
        <div className="flex flex-col items-center justify-center -mt-8">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
            className="relative"
          >
            <h1 className="text-[7rem] font-light leading-none tracking-tighter">
              {event.temperature.replace(/°./, "")}
              <span className="text-4xl align-top font-normal opacity-60">°</span>
            </h1>
          </motion.div>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-xl font-medium tracking-wide mt-2 capitalize opacity-90"
          >
            {event.condition}
          </motion.p>

          <div className="flex gap-2 mt-2 text-sm font-medium opacity-75">
            <span>H:24°</span>
            <span>L:18°</span>
          </div>
        </div>

        {/* Footer - Metrics */}
        <div className="grid grid-cols-3 gap-3">
          {event.windSpeed && (
            <MetricPill icon={Wind} label="Wind" value={event.windSpeed} delay={0.4} />
          )}
          {event.humidity && (
            <MetricPill icon={Droplets} label="Humidity" value={event.humidity} delay={0.5} />
          )}
          {event.precipitation ? (
            <MetricPill icon={CloudRain} label="Rain" value={event.precipitation} delay={0.6} />
          ) : (
            <MetricPill icon={Sun} label="UV Index" value="Low" delay={0.6} />
          )}
        </div>
      </div>
    </motion.div>
  );
};

// UPDATED: Standardized Glass Pill that works on both Light and Dark backgrounds
// We use a white/10 fill which lightens dark backgrounds and looks like frost on light ones.
const MetricPill = ({
  icon: Icon,
  label,
  value,
  delay,
}: {
  icon: any;
  label: string;
  value: string;
  delay: number;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, type: "spring" }}
    className="flex flex-col items-center justify-center bg-white/10 backdrop-blur-md rounded-2xl py-3 border border-white/20 shadow-sm"
  >
    <Icon className="w-5 h-5 mb-1 opacity-70" />
    <span className="text-xs opacity-60 font-medium">{label}</span>
    <span className="text-sm font-bold">{value}</span>
  </motion.div>
);

export const WeatherEventCarousel = ({ events }: { events: WeatherEventData[] }) => {
  if (events.length === 0) return null;

  // Mock data matching your screenshot + other types
  const demoEvents: WeatherEventData[] = [
    {
      id: "1",
      location: "Groningen, Netherlands",
      weatherType: "fog",
      temperature: "12°",
      condition: "Foggy",
      humidity: "90%",
      windSpeed: "8 km/h",
      precipitation: "30%",
    },
    {
      id: "2",
      location: "Rotterdam",
      weatherType: "wind",
      temperature: "14°",
      condition: "Windy",
      windSpeed: "32 km/h",
      humidity: "65%",
    },
    {
      id: "3",
      location: "Amsterdam",
      weatherType: "rain",
      temperature: "11°",
      condition: "Heavy Rain",
      precipitation: "100%",
      windSpeed: "12 km/h",
    },
  ];

  // Use passed events if available, otherwise use demo for display
  const displayEvents = events.length > 0 ? events : demoEvents;

  return (
    <div className="w-full overflow-x-auto hide-scrollbar py-8 snap-x snap-mandatory touch-pan-x">
      <div className="flex gap-6 w-max px-4">
        {displayEvents.map((event, index) => (
          <div key={event.id} className="snap-center">
            <WeatherEventCard event={event} />
          </div>
        ))}
      </div>
    </div>
  );
};

export const WeatherEventCardSkeleton = () => {
  return (
    <div className="relative w-full max-w-sm mx-auto h-[420px] rounded-[32px] bg-muted/20 border border-white/10 overflow-hidden">
      <div className="p-6 flex flex-col h-full justify-between">
        <div className="flex justify-between">
          <Skeleton className="h-4 w-24 bg-white/10" />
          <Skeleton className="h-10 w-10 rounded-full bg-white/10" />
        </div>
        <div className="flex flex-col items-center gap-4">
          <Skeleton className="h-32 w-32 rounded-full bg-white/10" />
          <Skeleton className="h-6 w-20 bg-white/10" />
        </div>
        <div className="flex gap-2 justify-between">
          <Skeleton className="h-16 w-full rounded-2xl bg-white/10" />
          <Skeleton className="h-16 w-full rounded-2xl bg-white/10" />
          <Skeleton className="h-16 w-full rounded-2xl bg-white/10" />
        </div>
      </div>
    </div>
  );
};
