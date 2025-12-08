import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        className={cn(
          "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border",
          {
            "bg-primary text-primary-foreground hover:bg-primary/90 border-primary/60 hover:border-primary shadow-[0_0_10px_rgba(168,85,247,0.3)]":
              variant === "default",
            "bg-destructive text-destructive-foreground hover:bg-destructive/90 border-destructive/60 hover:border-destructive":
              variant === "destructive",
            "border-2 border-white/30 bg-background hover:bg-accent hover:text-accent-foreground hover:border-white/50":
              variant === "outline",
            "bg-secondary text-secondary-foreground hover:bg-secondary/80 border-secondary/60 hover:border-secondary":
              variant === "secondary",
            "border-transparent hover:bg-accent hover:text-accent-foreground hover:border-white/20":
              variant === "ghost",
            "border-transparent text-primary underline-offset-4 hover:underline":
              variant === "link",
            "h-10 px-4 py-2": size === "default",
            "h-9 rounded-md px-3": size === "sm",
            "h-11 rounded-md px-8": size === "lg",
            "h-10 w-10": size === "icon",
          },
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
