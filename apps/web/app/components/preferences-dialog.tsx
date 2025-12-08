"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Settings, MapPin, Heart, Bell } from "lucide-react";
import {
  Preferences,
  getPreferences,
  setPreferences,
  getDefaultPreferences,
} from "@/app/lib/storage";

interface PreferencesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CITIES = ["Amsterdam", "Rotterdam"];
const CATEGORIES = ["Music", "Culture", "Food", "Sports", "Nightlife", "Art", "Theater"];

export function PreferencesDialog({ open, onOpenChange }: PreferencesDialogProps) {
  const [prefs, setPrefs] = useState<Preferences>(getDefaultPreferences());

  useEffect(() => {
    if (open) {
      setPrefs(getPreferences());
    }
  }, [open]);

  const handleSave = () => {
    setPreferences(prefs);
    onOpenChange(false);
  };

  const toggleCategory = (category: string) => {
    setPrefs((prev) => ({
      ...prev,
      favoriteCategories: prev.favoriteCategories.includes(category)
        ? prev.favoriteCategories.filter((c) => c !== category)
        : [...prev.favoriteCategories, category],
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(240,10%,3.9%)] backdrop-blur-md border-white/10 text-foreground max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl text-white flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Preferences
          </DialogTitle>
          <DialogDescription className="text-white/80">
            Customize your CityVibe experience
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {/* Default City */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white/90 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Default City
            </label>
            <div className="flex gap-2">
              {CITIES.map((city) => (
                <button
                  key={city}
                  onClick={() => setPrefs((prev) => ({ ...prev, defaultCity: city }))}
                  className={`
                    flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all border
                    ${
                      prefs.defaultCity === city
                        ? "bg-primary text-white border-primary/60 shadow-[0_0_10px_rgba(168,85,247,0.3)]"
                        : "bg-muted/50 text-white border-white/20 hover:border-white/40 hover:bg-muted"
                    }
                  `}
                >
                  {city}
                </button>
              ))}
            </div>
          </div>

          {/* Favorite Categories */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white/90 flex items-center gap-2">
              <Heart className="w-4 h-4" />
              Favorite Categories
            </label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((category) => (
                <button
                  key={category}
                  onClick={() => toggleCategory(category)}
                  className={`
                    px-3 py-1.5 rounded-full text-xs font-medium transition-all border
                    ${
                      prefs.favoriteCategories.includes(category)
                        ? "bg-primary text-white border-primary/60 shadow-[0_0_8px_rgba(168,85,247,0.3)]"
                        : "bg-muted/50 text-white border-white/20 hover:border-white/40 hover:bg-muted"
                    }
                  `}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>

          {/* Notifications */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-white/90 flex items-center gap-2">
              <Bell className="w-4 h-4" />
              Notifications
            </label>
            <div className="space-y-2">
              <label className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-white/10 hover:border-white/20 transition-colors cursor-pointer">
                <span className="text-sm text-white/90">Enable Notifications</span>
                <input
                  type="checkbox"
                  checked={prefs.notifications.enabled}
                  onChange={(e) =>
                    setPrefs((prev) => ({
                      ...prev,
                      notifications: { ...prev.notifications, enabled: e.target.checked },
                    }))
                  }
                  className="w-4 h-4 rounded border-white/20 bg-[hsl(240,10%,3.9%)] text-primary focus:ring-primary"
                />
              </label>
              {prefs.notifications.enabled && (
                <div className="space-y-2 pl-4">
                  <label className="flex items-center justify-between p-2 rounded-lg bg-muted/20 border border-white/5 hover:border-white/10 transition-colors cursor-pointer">
                    <span className="text-xs text-white/90">Email Notifications</span>
                    <input
                      type="checkbox"
                      checked={prefs.notifications.email}
                      onChange={(e) =>
                        setPrefs((prev) => ({
                          ...prev,
                          notifications: { ...prev.notifications, email: e.target.checked },
                        }))
                      }
                      className="w-4 h-4 rounded border-white/20 bg-[hsl(240,10%,3.9%)] text-primary focus:ring-primary"
                    />
                  </label>
                  <label className="flex items-center justify-between p-2 rounded-lg bg-muted/20 border border-white/5 hover:border-white/10 transition-colors cursor-pointer">
                    <span className="text-xs text-white/90">Push Notifications</span>
                    <input
                      type="checkbox"
                      checked={prefs.notifications.push}
                      onChange={(e) =>
                        setPrefs((prev) => ({
                          ...prev,
                          notifications: { ...prev.notifications, push: e.target.checked },
                        }))
                      }
                      className="w-4 h-4 rounded border-white/20 bg-[hsl(240,10%,3.9%)] text-primary focus:ring-primary"
                    />
                  </label>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-4 mt-4 border-t border-white/10">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save Preferences</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
