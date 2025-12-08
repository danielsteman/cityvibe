"use client";

import { useState, useRef, useEffect } from "react";
import { User, Settings, LogOut, History } from "lucide-react";
import { getUser, setUser } from "@/app/lib/storage";
import { User as UserType } from "@/app/lib/types";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface AccountMenuProps {
  onOpenPreferences: () => void;
  onOpenHistory: () => void;
}

export function AccountMenu({ onOpenPreferences, onOpenHistory }: AccountMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [user, setUserState] = useState<UserType | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setUserState(getUser());
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleLogout = () => {
    setUser(null);
    setUserState(null);
    setIsOpen(false);
  };

  if (!user) {
    return null;
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-muted/50 transition-all border border-white/10 hover:border-white/30"
        title="Account menu"
      >
        {user.avatar ? (
          <img
            src={user.avatar}
            alt={user.name}
            className="w-6 h-6 rounded-full border border-white/20"
          />
        ) : (
          <div className="w-6 h-6 rounded-full bg-primary/80 border border-primary/60 flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
        )}
        <span className="hidden sm:inline text-sm font-medium text-white/90">{user.name}</span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute right-0 top-full mt-2 w-56 rounded-lg bg-[hsl(240,10%,3.9%)] backdrop-blur-md border border-white/10 shadow-2xl z-50 overflow-hidden"
          >
            <div className="p-2 border-b border-white/10">
              <div className="px-3 py-2">
                <p className="text-sm font-semibold text-white">{user.name}</p>
                <p className="text-xs text-white/80 truncate">{user.email}</p>
              </div>
            </div>
            <div className="p-1">
              <button
                onClick={() => {
                  onOpenHistory();
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-white/90 hover:bg-muted/50 rounded-md transition-colors border border-transparent hover:border-white/10"
              >
                <History className="w-4 h-4" />
                Chat History
              </button>
              <button
                onClick={() => {
                  onOpenPreferences();
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-white/90 hover:bg-muted/50 rounded-md transition-colors border border-transparent hover:border-white/10"
              >
                <Settings className="w-4 h-4" />
                Preferences
              </button>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-md transition-colors border border-transparent hover:border-red-500/20 mt-1"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
