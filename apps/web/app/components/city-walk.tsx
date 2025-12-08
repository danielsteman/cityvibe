"use client";

import { motion } from "framer-motion";
import { MapPin, Clock, Route, ArrowRight, Navigation } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export interface CityWalkData {
  id: string;
  title: string;
  description: string;
  distance: string;
  duration: string;
  location: string;
  route: {
    name: string;
    waypoints: string[];
  };
  difficulty?: "Easy" | "Moderate" | "Challenging";
  source: string;
}

interface CityWalkProps {
  walk: CityWalkData;
}

export const CityWalk = ({ walk }: CityWalkProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="bg-muted/50 border-white/10 overflow-hidden group hover:border-primary/30 transition-all">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <CardTitle className="text-xl text-white mb-1">{walk.title}</CardTitle>
              <CardDescription className="text-muted-foreground text-sm">
                {walk.description}
              </CardDescription>
            </div>
            {walk.difficulty && (
              <span className="text-[10px] font-bold uppercase tracking-wider bg-secondary/20 text-secondary px-2 py-1 rounded-full border border-secondary/30">
                {walk.difficulty}
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2 text-sm">
              <Route className="w-4 h-4 text-secondary" />
              <span className="text-muted-foreground">{walk.distance}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-secondary" />
              <span className="text-muted-foreground">{walk.duration}</span>
            </div>
          </div>

          {/* Location */}
          <div className="flex items-center gap-2 text-sm">
            <MapPin className="w-4 h-4 text-primary" />
            <span className="text-muted-foreground">{walk.location}</span>
          </div>

          {/* Route Waypoints */}
          {walk.route.waypoints.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-white/10">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Route: {walk.route.name}
              </p>
              <div className="space-y-1.5">
                {walk.route.waypoints.map((waypoint, index) => (
                  <div key={index} className="flex items-start gap-2 text-sm">
                    <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                    <span className="text-muted-foreground">{waypoint}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Button */}
          <Button
            className="w-full bg-primary hover:bg-primary/90 text-white group-hover:shadow-[0_0_20px_rgba(168,85,247,0.4)] transition-all"
            onClick={() => {
              // In a real app, this would open navigation or start the walk
              console.log("Starting walk:", walk.id);
            }}
          >
            <Navigation className="w-4 h-4 mr-2" />
            Start Walk
            <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          {/* Source Badge */}
          <div className="pt-2 border-t border-white/10">
            <span className="text-[10px] text-muted-foreground">
              Source: <span className="font-semibold">{walk.source}</span>
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};
