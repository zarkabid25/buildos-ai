import { type LabelHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Label = forwardRef<HTMLLabelElement, LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => {
    return (
      <label
        ref={ref}
        className={cn("mb-1 block text-sm font-medium text-ink", className)}
        {...props}
      />
    );
  }
);
Label.displayName = "Label";
