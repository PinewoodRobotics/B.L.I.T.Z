"use client";

import { useRef, useState, useEffect } from "react";

export function PageSplit({
  children,
  minSplitPercentage = 20,
  initialSplit = 50,
}: {
  children: [React.ReactNode, React.ReactNode];
  minSplitPercentage?: number;
  initialSplit?: number;
}) {
  const [splitPosition, setSplitPosition] = useState(initialSplit);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [render, setRender] = useState(false);

  useEffect(() => {
    setSplitPosition(
      parseInt(localStorage.getItem("savedSplit") ?? "0") || initialSplit
    );
    setRender(true);
  }, [initialSplit]);

  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const container = containerRef.current;
    const containerRect = container.getBoundingClientRect();
    const percentage =
      ((e.clientX - containerRect.left) / containerRect.width) * 100;

    // Clamp the split position between minSplitPercentage and (100 - minSplitPercentage)
    const newPosition = Math.min(
      Math.max(percentage, minSplitPercentage),
      100 - minSplitPercentage
    );
    localStorage.setItem("savedSplit", newPosition.toString());
    setSplitPosition(newPosition);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div
      ref={containerRef}
      className="flex h-full w-full relative transition-opacity duration-500 ease-in-out"
      style={{ opacity: render ? 1 : 0 }}
    >
      <div
        className={`h-full overflow-auto`}
        style={{ width: `${splitPosition}%` }}
      >
        {children[0]}
      </div>

      <div
        className={`
          w-1
          absolute
          cursor-col-resize
          ${
            isDragging
              ? "bg-blue-400 select-none"
              : "bg-gray-300 hover:bg-gray-400"
          }
          before:absolute
          before:content-['']
          before:w-4
          before:h-4
          before:top-1/2
          before:-translate-y-1/2
          before:left-1/2
          before:-translate-x-1/2
          before:rounded-full
          before:bg-current
          before:opacity-20
          after:absolute
          after:content-['']
          after:w-2
          after:h-2
          after:top-1/2
          after:-translate-y-1/2
          after:left-1/2
          after:-translate-x-1/2
          after:rounded-full
          after:bg-current
          after:opacity-60
        `}
        style={{
          left: `${splitPosition}%`,
          top: 0,
          bottom: 0,
          transform: "translateX(-50%)",
        }}
        onMouseDown={handleMouseDown}
      />

      <div
        className={`h-full overflow-auto`}
        style={{ width: `${100 - splitPosition}%` }}
      >
        {children[1]}
      </div>
    </div>
  );
}
