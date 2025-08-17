"use client";
import * as React from "react";

type Props = React.InputHTMLAttributes<HTMLInputElement> & { label?: string };

export function Switch({ label, ...props }: Props) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-sm">
      <input type="checkbox" className="peer sr-only" {...props} />
      <span
        className="h-5 w-9 rounded-full bg-muted-foreground/30 before:inline-block before:h-4 before:w-4 before:translate-x-0 before:rounded-full before:bg-background before:shadow before:transition peer-checked:bg-primary peer-checked:before:translate-x-4"
        aria-hidden
      />
      {label ? <span>{label}</span> : null}
    </label>
  );
}

