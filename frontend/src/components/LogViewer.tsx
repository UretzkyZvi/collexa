"use client";
import { useCallback, useRef, useState } from "react";
import { Virtuoso, ListScrollLocation, LogLevel } from "react-virtuoso";

export type LogEvent = { id?: string | number; ts?: string; level?: string; message: string };

export function LogViewer({ events }: { events: LogEvent[] }) {
  const virtuosoRef = useRef<any>(null);
  const [bottomOffset, setBottomOffset] = useState(0);

  const onScroll = useCallback((loc: ListScrollLocation) => {
    setBottomOffset(loc.bottomOffset ?? 0);
  }, []);

  const scrollToBottom = useCallback(() => {
    virtuosoRef.current?.scrollToIndex({ index: "LAST", align: "end", behavior: "auto" });
  }, []);

  return (
    <div className="relative" style={{ height: 400 }}>
      <Virtuoso
        style={{ height: "100%" }}
        ref={virtuosoRef}
        data={events}
        followOutput={(isAtBottom) => (isAtBottom ? "auto" : false)}
        itemContent={(_, ev) => (
          <div className="whitespace-pre-wrap text-xs">
            {ev.ts ? `${ev.ts} ` : ""}
            {ev.level ? `[${ev.level}] ` : ""}
            {ev.message}
          </div>
        )}
        atBottomStateChange={(atBottom) => {
          if (atBottom) setBottomOffset(0);
        }}
        // Track bottom offset for sticky button display
        onScroll={onScroll}
        // Helpful when debugging sizing
        logLevel={LogLevel.ERROR}
      />
      {bottomOffset > 120 ? (
        <button
          className="absolute bottom-3 right-3 rounded bg-primary px-3 py-1 text-xs text-primary-foreground shadow"
          onClick={scrollToBottom}
        >
          Scroll to latest
        </button>
      ) : null}
    </div>
  );
}

