"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Calendar, MapPin, Ticket, Info, Heart, Share2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EventData {
  id: string;
  title: string;
  image: string;
  time: string;
  location: string;
  price: string;
  category: string;
  source: string; // To show which MCP provided the data
  description?: string; // Optional description for dialog
}

export const EventCarousel = ({ events }: { events: EventData[] }) => {
  return (
    <div className="w-full overflow-x-auto hide-scrollbar py-4 snap-x snap-mandatory touch-pan-x">
      <div className="flex gap-4 sm:gap-6 w-max pr-2 sm:pr-4">
        {events.map((event, index) => (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            key={event.id}
            className="snap-start"
          >
            <EventCard event={event} />
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export const EventCard = ({ event }: { event: EventData }) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);

  // Load favorite state from localStorage
  useEffect(() => {
    const favorites = JSON.parse(localStorage.getItem("cityvibe-favorites") || "[]");
    setIsFavorite(favorites.includes(event.id));
  }, [event.id]);

  const handleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    const favorites = JSON.parse(localStorage.getItem("cityvibe-favorites") || "[]");
    if (isFavorite) {
      const newFavorites = favorites.filter((id: string) => id !== event.id);
      localStorage.setItem("cityvibe-favorites", JSON.stringify(newFavorites));
      setIsFavorite(false);
    } else {
      favorites.push(event.id);
      localStorage.setItem("cityvibe-favorites", JSON.stringify(favorites));
      setIsFavorite(true);
    }
  };

  const handleShare = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const shareData = {
      title: event.title,
      text: `${event.title} - ${event.location} at ${event.time}`,
      url: window.location.href,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        // User cancelled or error occurred
      }
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(`${event.title} - ${event.location} at ${event.time}`);
    }
  };

  return (
    <>
      <div
        className="relative w-full sm:w-[280px] h-[380px] rounded-xl overflow-hidden border border-white/20 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-sm flex flex-col group hover:border-primary/40 hover:shadow-[0_12px_48px_rgba(168,85,247,0.3)] transition-all duration-300 cursor-pointer"
        onClick={() => event.description && setIsDialogOpen(true)}
      >
        {/* Default gradient background - always visible, more prominent */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/40 via-secondary/30 to-primary/40 z-0" />

        {/* Pattern overlay for default background */}
        <div
          className="absolute inset-0 opacity-30 z-0"
          style={{
            backgroundImage: `radial-gradient(circle at 2px 2px, rgba(255,255,255,0.2) 1px, transparent 0)`,
            backgroundSize: "40px 40px",
          }}
        />

        {/* Background Image - only show if image exists and is not empty */}
        {event.image && event.image.trim() && (
          <div
            className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110 z-[1]"
            style={{ backgroundImage: `url(${event.image})` }}
            onError={(e) => {
              // Hide image if it fails to load, showing default background
              e.currentTarget.style.display = "none";
            }}
          />
        )}
        {/* Darker gradient overlay for better text readability - only when image exists */}
        {event.image && event.image.trim() && (
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/90 to-background/60 z-[2]" />
        )}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-secondary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500 z-[3]" />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-end h-full p-5 space-y-3">
          {/* Badges and Action Buttons */}
          <div className="absolute top-4 left-4 right-4 flex items-start justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-primary/90 text-white px-2 py-1 rounded-full backdrop-blur-md shadow-[0_0_10px_rgba(168,85,247,0.5)]">
                {event.category}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-black/60 border border-white/20 text-white/90 px-2 py-1 rounded-full backdrop-blur-md">
                MCP: {event.source}
              </span>
            </div>
            <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={handleFavorite}
                className={cn(
                  "p-1.5 rounded-full backdrop-blur-md transition-all border",
                  isFavorite
                    ? "bg-red-500/90 text-white border-red-400/60 hover:border-red-400"
                    : "bg-black/60 text-white/90 hover:bg-black/80 border-white/20 hover:border-white/40"
                )}
                title={isFavorite ? "Remove from favorites" : "Add to favorites"}
              >
                <Heart className={cn("w-3.5 h-3.5", isFavorite && "fill-current")} />
              </button>
              <button
                onClick={handleShare}
                className="p-1.5 rounded-full bg-black/60 text-white/90 hover:bg-black/80 backdrop-blur-md transition-all border border-white/20 hover:border-white/40"
                title="Share event"
              >
                <Share2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <h3 className="text-xl font-bold text-white leading-tight">{event.title}</h3>

          <div className="space-y-1 text-sm text-white/90">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-secondary" />
              <span>{event.time}</span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-secondary" />
              <span>{event.location}</span>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/10">
            <span className="font-semibold text-white">{event.price}</span>
            <div className="flex gap-2">
              {event.description && (
                <button
                  onClick={() => setIsDialogOpen(true)}
                  className="flex items-center gap-1 px-3 py-2 text-xs font-bold text-white bg-primary/80 hover:bg-primary rounded-full transition-all border border-primary/60 hover:border-primary shadow-[0_0_8px_rgba(168,85,247,0.3)]"
                  aria-label="More info"
                >
                  <Info className="w-3 h-3" />
                </button>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsDialogOpen(true);
                }}
                className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-black bg-white rounded-full hover:bg-secondary hover:text-white transition-all border-2 border-white/40 hover:border-secondary/60 shadow-[0_0_8px_rgba(255,255,255,0.2)]"
              >
                <Ticket className="w-3 h-3" />
                Book Now
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Event Details Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="bg-[hsl(240,10%,3.9%)] backdrop-blur-md border-white/10 text-foreground max-w-md mx-4 p-0 flex flex-col max-h-[90vh]">
          <div className="p-6 pb-4 flex-shrink-0 border-b border-white/10">
            <DialogHeader>
              <DialogTitle className="text-2xl text-white">{event.title}</DialogTitle>
              <DialogDescription className="text-white/80">
                {event.category} • {event.source}
              </DialogDescription>
            </DialogHeader>
          </div>
          <div className="space-y-4 px-6 py-4 overflow-y-auto flex-1 min-h-0">
            <div className="relative w-full h-48 rounded-lg border border-white/10 overflow-hidden">
              {/* Default gradient background */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/30 via-secondary/20 to-primary/30" />

              {/* Pattern overlay */}
              <div
                className="absolute inset-0 opacity-20"
                style={{
                  backgroundImage: `radial-gradient(circle at 2px 2px, rgba(255,255,255,0.15) 1px, transparent 0)`,
                  backgroundSize: "40px 40px",
                }}
              />

              {/* Event image if available */}
              {event.image && (
                <div
                  className="absolute inset-0 bg-cover bg-center"
                  style={{ backgroundImage: `url(${event.image})` }}
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
              )}
            </div>
            {event.description && (
              <p className="text-white/90 leading-relaxed">{event.description}</p>
            )}
            <div className="space-y-3 pt-3 border-t border-white/10 flex-shrink-0">
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="w-4 h-4 text-secondary flex-shrink-0" />
                <span className="text-white/90">{event.time}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="w-4 h-4 text-secondary flex-shrink-0" />
                <span className="text-white/90">{event.location}</span>
              </div>
            </div>
          </div>
          <div className="px-6 pb-6 pt-4 border-t border-white/10 flex-shrink-0 bg-[hsl(240,10%,3.9%)]">
            <div className="flex items-center justify-between gap-4">
              <span className="text-xl font-bold text-white">{event.price}</span>
              <Button
                className="bg-primary hover:bg-primary/90 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)] flex-shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle booking logic here - could open external booking URL, show booking form, etc.
                  setIsDialogOpen(false);
                }}
              >
                <Ticket className="w-4 h-4 mr-2" />
                Book Now
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

// Skeleton Loader Components
export const EventCardSkeleton = () => {
  return (
    <div className="relative w-full sm:w-[280px] h-[380px] rounded-xl overflow-hidden bg-muted border border-white/10 shadow-2xl flex flex-col">
      {/* Image Skeleton */}
      <Skeleton className="absolute inset-0" />
      <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />

      {/* Content Skeleton */}
      <div className="relative z-10 flex flex-col justify-end h-full p-5 space-y-3">
        {/* Badges Skeleton */}
        <div className="absolute top-4 left-4 flex flex-wrap gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>

        {/* Title Skeleton */}
        <Skeleton className="h-6 w-3/4" />

        {/* Info Skeleton */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>

        {/* Footer Skeleton */}
        <div className="flex items-center justify-between pt-2 border-t border-white/10">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-8 w-24 rounded-full" />
        </div>
      </div>
    </div>
  );
};

export const EventCarouselSkeleton = () => {
  return (
    <div className="w-full overflow-x-auto hide-scrollbar py-4 pl-1 snap-x snap-mandatory touch-pan-x">
      <div className="flex gap-3 sm:gap-4 w-max">
        {[1, 2, 3].map((index) => (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            key={index}
            className="snap-start"
          >
            <EventCardSkeleton />
          </motion.div>
        ))}
      </div>
    </div>
  );
};
