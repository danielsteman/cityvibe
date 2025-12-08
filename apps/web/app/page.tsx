"use client";

import { useState, useRef, useEffect } from "react";
import { useUIState, useActions } from "@ai-sdk/rsc";
import type { AI } from "./actions";
import { Send, Sparkles, MapPin, X, Copy, ChevronDown, Filter, User, History } from "lucide-react";
import clsx from "clsx";
import { motion } from "framer-motion";
import { EventCarouselSkeleton } from "./components/event-card";
import { ToastContainer, Toast } from "@/components/ui/toast";
import { LoginDialog } from "./components/login-dialog";
import { AccountMenu } from "./components/account-menu";
import { PreferencesDialog } from "./components/preferences-dialog";
import { ChatSidebar } from "./components/chat-sidebar";
import { getUser, setUser, setCurrentSession, saveChatSession, ChatSession } from "./lib/storage";
import { User as UserType } from "./lib/types";

export default function CityVibePage() {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useUIState<typeof AI>();
  const { submitUserMessage } = useActions<typeof AI>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const [user, setUserState] = useState<UserType | null>(null);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isPreferencesOpen, setIsPreferencesOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Load user on mount
  useEffect(() => {
    const storedUser = getUser();
    setUserState(storedUser);
    if (!storedUser) {
      setIsLoginOpen(true);
    }
  }, []);

  // Save chat session when messages change
  useEffect(() => {
    if (messages.length > 0) {
      const sessionId = currentSessionId || Date.now().toString();
      setCurrentSessionId(sessionId);

      const firstUserMessage = messages.find((m: any) => m.role === "user");
      let title = "New Chat";
      if (firstUserMessage) {
        // Try to get content from the message object (it's stored in user messages)
        title = (firstUserMessage as any).content || "New Chat";
        if (title.length > 50) title = title.substring(0, 50) + "...";
      }

      const session: ChatSession = {
        id: sessionId,
        title: title,
        timestamp: parseInt(sessionId),
        messages: messages,
      };

      setCurrentSession(session);
    }
  }, [messages, currentSessionId]);

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Auto-focus input after sending message
  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [isLoading, messages.length]);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Check if user scrolled up
  useEffect(() => {
    const chatArea = chatAreaRef.current;
    if (!chatArea) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatArea;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 200;
      setShowScrollButton(!isNearBottom);
    };

    chatArea.addEventListener("scroll", handleScroll);
    return () => chatArea.removeEventListener("scroll", handleScroll);
  }, []);

  const showToast = (message: string, type: Toast["type"] = "success") => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, message, type }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleClearChat = () => {
    // Save current session before clearing
    if (messages.length > 0 && currentSessionId) {
      const firstUserMessage = messages.find((m: any) => m.role === "user");
      let title = "New Chat";
      if (firstUserMessage) {
        title = (firstUserMessage as any).content || "New Chat";
        if (title.length > 50) title = title.substring(0, 50) + "...";
      }
      const session: ChatSession = {
        id: currentSessionId,
        title: title,
        timestamp: parseInt(currentSessionId),
        messages: messages,
      };
      saveChatSession(session);
    }

    setMessages([]);
    setActiveFilters([]);
    setCurrentSessionId(null);
    setCurrentSession(null);
    showToast("Chat cleared", "info");
    inputRef.current?.focus();
  };

  const handleLogin = (loggedInUser: UserType) => {
    setUserState(loggedInUser);
    showToast(`Welcome, ${loggedInUser.name}!`, "success");
  };

  const handleLoadSession = (session: ChatSession) => {
    // Save current session before loading new one
    if (messages.length > 0 && currentSessionId) {
      const firstUserMessage = messages.find((m: any) => m.role === "user");
      let title = "New Chat";
      if (firstUserMessage) {
        title = (firstUserMessage as any).content || "New Chat";
        if (title.length > 50) title = title.substring(0, 50) + "...";
      }
      const currentSession: ChatSession = {
        id: currentSessionId,
        title: title,
        timestamp: parseInt(currentSessionId),
        messages: messages,
      };
      saveChatSession(currentSession);
    }

    setMessages(session.messages);
    setCurrentSessionId(session.id);
    setCurrentSession(session);
    showToast("Chat session loaded", "success");
  };

  const handleNewChat = () => {
    // Save current session before starting new one
    if (messages.length > 0 && currentSessionId) {
      const firstUserMessage = messages.find((m: any) => m.role === "user");
      let title = "New Chat";
      if (firstUserMessage) {
        title = (firstUserMessage as any).content || "New Chat";
        if (title.length > 50) title = title.substring(0, 50) + "...";
      }
      const currentSession: ChatSession = {
        id: currentSessionId,
        title: title,
        timestamp: parseInt(currentSessionId),
        messages: messages,
      };
      saveChatSession(currentSession);
    }

    setMessages([]);
    setActiveFilters([]);
    setCurrentSessionId(null);
    setCurrentSession(null);
    showToast("New chat started", "info");
    inputRef.current?.focus();
  };

  const handleScrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleCopyMessage = (text: string) => {
    navigator.clipboard.writeText(text);
    showToast("Message copied to clipboard");
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

    setIsLoading(true);
    setInputValue(""); // Clear input immediately

    const messageId = Date.now().toString();
    // Add User Message to UI
    setMessages((currentMessages: any) => [
      ...currentMessages,
      {
        id: messageId,
        role: "user",
        content: content, // Store original content for copying
        display: (
          <div className="flex justify-end w-full mb-2 sm:mb-4 animate-[fadeIn_0.3s_ease-out] group/message">
            <div className="bg-primary/20 text-white px-3 sm:px-4 py-2 text-sm sm:text-base rounded-2xl rounded-tr-sm max-w-full border border-primary/40 break-words relative shadow-[0_0_8px_rgba(168,85,247,0.2)]">
              {content}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopyMessage(content);
                }}
                className="absolute -left-8 top-0 opacity-0 group-hover/message:opacity-100 transition-opacity p-1.5 hover:bg-muted rounded-lg"
                title="Copy message"
              >
                <Copy className="w-3.5 h-3.5 text-white/70 hover:text-white" />
              </button>
            </div>
          </div>
        ),
      },
    ]);

    // Call Server Action
    const response = await submitUserMessage(content);

    // Add AI Response to UI
    setMessages((currentMessages: any) => [...currentMessages, { ...response, role: "assistant" }]);

    setIsLoading(false);
  };

  const suggestions = [
    {
      label: "Techno in Rotterdam?",
      icon: <Sparkles className="w-3 h-3 text-secondary" />,
      query: "What's happening in Rotterdam tonight?",
    },
    {
      label: "Art in Amsterdam",
      icon: <MapPin className="w-3 h-3 text-primary" />,
      query: "Show me culture in Amsterdam",
    },
    {
      label: "Hidden Gems",
      icon: <Sparkles className="w-3 h-3 text-secondary" />,
      query: "Show me walks in Amsterdam",
    },
    {
      label: "Concerts Tonight",
      icon: <Sparkles className="w-3 h-3 text-primary" />,
      query: "Concerts in Amsterdam",
    },
  ];

  const quickFilters = [
    { label: "Free", query: "free events" },
    { label: "Tonight", query: "events tonight" },
    { label: "Music", query: "music events" },
    { label: "Culture", query: "culture events" },
    { label: "Food", query: "food events" },
  ];

  return (
    <div className="flex h-screen bg-[hsl(var(--background))] text-[hsl(var(--foreground))] overflow-hidden font-sans">
      {/* Chat Sidebar */}
      {user && (
        <ChatSidebar
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onLoadSession={handleLoadSession}
          onNewChat={handleNewChat}
          currentSessionId={currentSessionId}
        />
      )}
      {/* Main Content */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-white/5 bg-[hsl(240,10%,3.9%)]/50 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
              <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-white fill-white" />
            </div>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
              CityVibe
            </h1>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white hover:text-white hover:bg-muted/50 rounded-lg transition-all border border-white/20 hover:border-white/40"
                title="Toggle chat history"
              >
                <History className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">History</span>
              </button>
            )}
            {messages.length > 0 && (
              <button
                onClick={handleClearChat}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white hover:text-white hover:bg-muted/50 rounded-lg transition-all border border-white/20 hover:border-white/40"
                title="Clear chat"
              >
                <X className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Clear</span>
              </button>
            )}
            {user ? (
              <AccountMenu
                onOpenPreferences={() => setIsPreferencesOpen(true)}
                onOpenHistory={() => setIsSidebarOpen(true)}
              />
            ) : (
              <button
                onClick={() => setIsLoginOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white bg-primary/80 hover:bg-primary rounded-lg transition-all border border-primary/60 hover:border-primary"
                title="Sign in"
              >
                <User className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sign In</span>
              </button>
            )}
            <div className="text-[10px] sm:text-xs text-white/90 flex items-center gap-1">
              <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="hidden sm:inline">MCP Connected</span>
              <span className="sm:hidden">MCP</span>
            </div>
          </div>
        </header>

        {/* Chat Area */}
        <div
          ref={chatAreaRef}
          className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 bg-[hsl(240,10%,3.9%)] relative"
        >
          <div className="max-w-6xl mx-auto px-2 sm:px-4 space-y-4 sm:space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center space-y-6 sm:space-y-8 px-4 opacity-0 animate-[fadeIn_0.5s_ease-out_forwards] min-h-[60vh]">
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="text-center space-y-3"
                >
                  <h2 className="text-3xl sm:text-4xl font-bold text-white">Tonight's Plan?</h2>
                  <p className="text-base sm:text-lg text-white/90">
                    Discover amazing events in your city
                  </p>
                  <p className="text-sm text-white/80">
                    Ask me anything about what's happening tonight
                  </p>
                </motion.div>

                <div className="flex flex-wrap justify-center gap-2 sm:gap-3 w-full max-w-lg">
                  {suggestions.map((s, i) => (
                    <motion.button
                      key={i}
                      onClick={() => handleSendMessage(s.query || s.label)}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 + i * 0.1 }}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="flex items-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2.5 rounded-full bg-muted/50 border-2 border-white/20 hover:border-primary/60 hover:bg-muted hover:shadow-[0_0_15px_rgba(168,85,247,0.3)] transition-all text-sm text-white touch-manipulation"
                    >
                      {s.icon}
                      <span className="whitespace-nowrap font-medium">{s.label}</span>
                    </motion.button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {/* Quick Filters */}
                {messages.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 overflow-x-auto hide-scrollbar pb-2"
                  >
                    <Filter className="w-4 h-4 text-white/90 flex-shrink-0" />
                    {quickFilters.map((filter) => (
                      <button
                        key={filter.label}
                        onClick={() => {
                          handleSendMessage(filter.query);
                          setActiveFilters((prev) =>
                            prev.includes(filter.label)
                              ? prev.filter((f) => f !== filter.label)
                              : [...prev, filter.label]
                          );
                        }}
                        className={clsx(
                          "px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap flex-shrink-0 border",
                          activeFilters.includes(filter.label)
                            ? "bg-primary text-white shadow-[0_0_10px_rgba(168,85,247,0.4)] border-primary/60 hover:border-primary"
                            : "bg-muted/50 text-white hover:bg-muted hover:text-white border-white/20 hover:border-white/40"
                        )}
                      >
                        {filter.label}
                      </button>
                    ))}
                  </motion.div>
                )}
              </>
            )}
            {messages.length > 0 &&
              messages.map((message: any) => (
                <div
                  key={message.id}
                  className={clsx(
                    "w-full flex animate-[fadeIn_0.3s_ease-out]",
                    message.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {/* Render the component (Text or React Node) */}
                  <div
                    className={clsx(
                      "max-w-[90%] sm:max-w-md md:max-w-2xl lg:max-w-4xl",
                      message.role === "assistant" && "w-full max-w-full" // Allow full width for carousels
                    )}
                  >
                    {message.display}
                  </div>
                </div>
              ))}

            {/* Loading Indicator with Skeleton */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full space-y-4"
              >
                <div className="flex items-center gap-2 text-white/90 text-sm pl-2">
                  <motion.div
                    className="w-2 h-2 bg-primary rounded-full"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                  />
                  <motion.div
                    className="w-2 h-2 bg-secondary rounded-full"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                  />
                  <motion.div
                    className="w-2 h-2 bg-primary rounded-full"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                  />
                  <span className="animate-pulse">Checking MCP Servers...</span>
                </div>
                <EventCarouselSkeleton />
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Scroll to Bottom Button */}
          {showScrollButton && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={handleScrollToBottom}
              className="fixed bottom-24 right-4 sm:right-6 z-30 p-3 bg-primary text-white rounded-full shadow-lg hover:bg-primary/90 hover:shadow-[0_0_20px_rgba(168,85,247,0.5)] transition-all"
              aria-label="Scroll to bottom"
            >
              <ChevronDown className="w-5 h-5" />
            </motion.button>
          )}
        </div>

        {/* Toast Notifications */}
        <ToastContainer toasts={toasts} onClose={removeToast} />

        {/* Login Dialog */}
        <LoginDialog open={isLoginOpen} onOpenChange={setIsLoginOpen} onLogin={handleLogin} />

        {/* Preferences Dialog */}
        <PreferencesDialog open={isPreferencesOpen} onOpenChange={setIsPreferencesOpen} />

        {/* Input Area */}
        <div className="p-3 sm:p-4 md:p-6 bg-[hsl(240,10%,3.9%)]/80 backdrop-blur-lg border-t border-white/5 safe-area-inset-bottom">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(inputValue);
            }}
            className="max-w-6xl mx-auto px-2 sm:px-4 relative"
          >
            <input
              ref={inputRef}
              className="w-full bg-muted/50 border border-white/20 rounded-full py-3 sm:py-4 pl-4 sm:pl-6 pr-12 sm:pr-14 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all placeholder:text-white/80 touch-manipulation"
              placeholder="What's happening tonight?"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isLoading}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  setInputValue("");
                  inputRef.current?.blur();
                }
              }}
            />
            <motion.button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              whileHover={!isLoading && inputValue.trim() ? { scale: 1.1 } : {}}
              whileTap={!isLoading && inputValue.trim() ? { scale: 0.9 } : {}}
              className="absolute right-1.5 sm:right-2 top-1/2 -translate-y-1/2 p-2 bg-primary text-white rounded-full hover:bg-primary/90 hover:shadow-[0_0_15px_rgba(168,85,247,0.5)] disabled:opacity-50 disabled:cursor-not-allowed transition-all touch-manipulation"
            >
              <Send className="w-4 h-4" />
            </motion.button>
          </form>
        </div>
      </div>
    </div>
  );
}
