"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { History, Trash2, MessageSquare, Plus, X } from "lucide-react";
import { getChatHistory, deleteChatSession, ChatSession } from "@/app/lib/storage";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

// Simple date formatter
const formatDate = (timestamp: number) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    return `Today at ${date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;
  } else if (days === 1) {
    return `Yesterday at ${date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    })}`;
  } else if (days < 7) {
    return `${days} days ago`;
  } else {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
};

interface ChatSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  onLoadSession: (session: ChatSession) => void;
  onNewChat: () => void;
  currentSessionId: string | null;
}

export function ChatSidebar({
  isOpen,
  onToggle,
  onLoadSession,
  onNewChat,
  currentSessionId,
}: ChatSidebarProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    const loadSessions = () => {
      setSessions(getChatHistory());
    };
    loadSessions();
    // Refresh sessions periodically
    const interval = setInterval(loadSessions, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteChatSession(sessionId);
    setSessions(getChatHistory());
  };

  const handleLoadSession = (session: ChatSession) => {
    onLoadSession(session);
  };

  return (
    <>
      {/* Overlay for mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          />
        )}
      </AnimatePresence>
      {/* Sidebar - fixed on mobile, relative on desktop */}
      <div
        className={cn(
          "w-80 bg-[hsl(240,10%,3.9%)] backdrop-blur-md border-r border-white/10 flex flex-col shadow-2xl transition-transform duration-300",
          "fixed lg:relative left-0 top-0 h-full z-50 lg:z-auto",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Header */}
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-white" />
            <h2 className="text-lg font-semibold text-white">Chat History</h2>
          </div>
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors border border-white/20 hover:border-white/40 lg:hidden"
            title="Close sidebar"
          >
            <X className="w-4 h-4 text-white" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-4 border-b border-white/10">
          <Button
            onClick={onNewChat}
            className="w-full bg-primary hover:bg-primary/90 text-white border border-primary/60 hover:border-primary shadow-[0_0_10px_rgba(168,85,247,0.3)]"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <MessageSquare className="w-12 h-12 text-white/50 mb-4" />
              <p className="text-white/90">No chat history yet</p>
              <p className="text-sm text-white/80 mt-1">Your conversations will appear here</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleLoadSession(session)}
                className={cn(
                  "group relative p-3 rounded-lg border transition-all cursor-pointer",
                  currentSessionId === session.id
                    ? "bg-primary/20 border-primary/50 shadow-[0_0_8px_rgba(168,85,247,0.2)]"
                    : "bg-muted/30 border-white/10 hover:border-primary/50 hover:bg-muted/50"
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-white truncate mb-1">
                      {session.title}
                    </h3>
                    <div className="flex items-center gap-2 text-xs text-white/80">
                      <span>{formatDate(session.timestamp)}</span>
                      <span>•</span>
                      <span>{session.messages.length} messages</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 text-red-400 hover:text-red-300 transition-all border border-transparent hover:border-red-500/20 flex-shrink-0"
                    title="Delete session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
