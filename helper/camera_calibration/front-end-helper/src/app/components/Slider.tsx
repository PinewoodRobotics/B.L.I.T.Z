"use client";

import { Slider } from "@mui/material";
import React, { useState, useRef } from "react";

export function GradientSlider({
  min = 0,
  max = 100,
  step = 1,
  initialValues = [25, 75],
  gradient = "linear-gradient(to right, red, yellow, green)",
  onChange,
}: {
  min?: number;
  max?: number;
  step?: number;
  initialValues?: [number, number];
  gradient?: string;
  onChange?: (values: [number, number]) => void;
}) {
  const [values, setValues] = useState<[number, number]>(initialValues);
  const sliderRef = useRef<HTMLDivElement>(null);

  const percentage = (value: number) => ((value - min) / (max - min)) * 100;

  const handleThumbMove = (index: number, clientX: number) => {
    if (!sliderRef.current) return;

    const sliderRect = sliderRef.current.getBoundingClientRect();
    const sliderWidth = sliderRect.width;
    const offsetX = clientX - sliderRect.left;
    const newValue =
      Math.round(((offsetX / sliderWidth) * (max - min)) / step) * step + min;

    const clampedValue = Math.min(Math.max(newValue, min), max);
    const newValues: [number, number] = [...values] as [number, number];

    if (index === 0 && clampedValue <= newValues[1] - step) {
      newValues[0] = clampedValue;
    } else if (index === 1 && clampedValue >= newValues[0] + step) {
      newValues[1] = clampedValue;
    }

    setValues(newValues);
    onChange?.(newValues);
  };

  return (
    <div
      ref={sliderRef}
      className="relative w-full max-w-lg mx-auto h-full rounded-lg"
      style={{ background: gradient }}
    >
      {/* Selected Range */}
      <div
        className="absolute h-full bg-white opacity-40 rounded-lg"
        style={{
          left: `${percentage(values[0])}%`,
          right: `${100 - percentage(values[1])}%`,
        }}
      ></div>

      {/* Thumbs */}
      {values.map((value, index) => (
        <div
          key={index}
          className="absolute top-1/2 w-6 h-6 bg-white opacity-60 border-2 border-gray-800 rounded-full transform -translate-y-1/2 -translate-x-1/2 cursor-pointer shadow-md group"
          style={{
            left: `${percentage(value)}%`,
          }}
          onMouseDown={() => {
            const handleMouseMove = (moveEvent: MouseEvent) => {
              handleThumbMove(index, moveEvent.clientX);
            };

            const handleMouseUp = () => {
              document.removeEventListener("mousemove", handleMouseMove);
              document.removeEventListener("mouseup", handleMouseUp);
            };

            document.addEventListener("mousemove", handleMouseMove);
            document.addEventListener("mouseup", handleMouseUp);
          }}
        >
          <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            {value}
          </div>
        </div>
      ))}
    </div>
  );
}

export function BasicSlider() {
  return (
    <div style={{ width: "300px", margin: "50px auto" }}>
      <Slider
        defaultValue={50}
        min={0}
        max={100}
        step={1}
        onChange={(event, value) => console.log(value)}
        aria-label="Basic slider"
        sx={{
          color: "#007AFF", // iOS blue color
          "& .MuiSlider-thumb": {
            backgroundColor: "#fff",
            border: "2px solid #007AFF",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
            "&:hover, &.Mui-focusVisible": {
              boxShadow: "0 3px 6px rgba(0,0,0,0.15)",
            },
          },
          "& .MuiSlider-rail": {
            backgroundColor: "#E5E5EA", // iOS light gray
            opacity: 1,
          },
          "& .MuiSlider -track": {
            backgroundColor: "#007AFF",
          },
          "& .MuiSlider-valueLabel": {
            backgroundColor: "#007AFF",
            borderRadius: "6px",
            padding: "2px 6px",
            fontSize: "12px",
          },
        }}
      />
    </div>
  );
}
