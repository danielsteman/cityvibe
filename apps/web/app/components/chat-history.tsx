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
import { History, Trash2, MessageSquare } from "lucide-react";
import { getChatHistory, deleteChatSession, ChatSession } from "@/app/lib/storage";
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

interface ChatHistoryProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLoadSession: (session: ChatSession) => void;
}

export function ChatHistory({ open, onOpenChange, onLoadSession }: ChatHistoryProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    if (open) {
      setSessions(getChatHistory());
    }
  }, [open]);

  const handleDelete = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteChatSession(sessionId);
    setSessions(getChatHistory());
  };

  const handleLoadSession = (session: ChatSession) => {
    onLoadSession(session);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[hsl(240,10%,3.9%)] backdrop-blur-md border-white/10 text-foreground max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-2xl text-white flex items-center gap-2">
            <History className="w-5 h-5" />
            Chat History
          </DialogTitle>
          <DialogDescription className="text-gray-300">
            View and restore your previous conversations
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto mt-4 space-y-2">
          {sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <MessageSquare className="w-12 h-12 text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No chat history yet</p>
              <p className="text-sm text-muted-foreground/70 mt-1">
                Your conversations will appear here
              </p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleLoadSession(session)}
                className="group relative p-4 rounded-lg bg-muted/30 border border-white/10 hover:border-primary/50 hover:bg-muted/50 transition-all cursor-pointer"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-white truncate mb-1">
                      {session.title}
                    </h3>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{formatDate(session.timestamp)}</span>
                      <span>•</span>
                      <span>{session.messages.length} messages</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-red-500/10 text-red-400 hover:text-red-300 transition-all border border-transparent hover:border-red-500/20"
                    title="Delete session"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex justify-end pt-4 mt-4 border-t border-white/10">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
