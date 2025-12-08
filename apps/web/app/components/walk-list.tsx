"use client";

import { motion } from "framer-motion";
import { CityWalk, CityWalkData } from "./city-walk";

interface WalkListProps {
  walks: CityWalkData[];
}

export const WalkList = ({ walks }: WalkListProps) => {
  if (walks.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>No walks found. Try a different search!</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {walks.map((walk, index) => (
        <motion.div
          key={walk.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <CityWalk walk={walk} />
        </motion.div>
      ))}
    </div>
  );
};
