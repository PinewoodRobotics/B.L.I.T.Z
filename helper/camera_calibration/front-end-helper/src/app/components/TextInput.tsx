"use client";

import { useState } from "react";

interface NumberInputProps {
  placeholder?: string;
  onChange: (value: number) => void;
  className?: string;
  min?: number;
  max?: number;
  step?: number;
  initialValue?: number;
}

export function NumberInput({
  placeholder,
  onChange,
  className = "",
  min,
  max,
  step = 1,
  initialValue = 0,
}: NumberInputProps) {
  const [value, setValue] = useState(initialValue);

  return (
    <input
      type="number"
      value={value}
      onChange={(e) => {
        setValue(Number(e.target.value));
        if (value !== undefined) {
          onChange(Number(e.target.value));
        }
      }}
      placeholder={placeholder}
      min={min}
      max={max}
      step={step}
      className={`
        w-full
        bg-gray-900
        text-gray-100
        border-2
        border-gray-700
        rounded-lg
        p-4
        font-mono
        placeholder-gray-500
        transition-all
        duration-300
        focus:outline-none
        focus:ring-2
        focus:ring-blue-500
        focus:border-transparent
        hover:border-gray-600
        shadow-inner
        shadow-gray-950
        backdrop-blur-sm
        bg-opacity-90
        [&::-webkit-inner-spin-button]:appearance-none
        [&::-webkit-outer-spin-button]:appearance-none
        ${className}
      `}
      style={{
        WebkitTapHighlightColor: "transparent",
      }}
    />
  );
}

interface LabeledNumberInputProps extends NumberInputProps {
  label: string;
}
export function LabeledNumberInput({
  label,
  placeholder,
  onChange,
  className = "",
  min,
  max,
  step = 1,
  initialValue = 0,
}: LabeledNumberInputProps) {
  const [value, setValue] = useState(initialValue);

  return (
    <div className="w-full flex flex-col gap-2">
      <label className="text-sm text-gray-400 font-medium pl-1">{label}</label>
      <input
        type="number"
        value={value ?? ""}
        onChange={(e) => {
          const val =
            e.target.value === "" ? undefined : Number(e.target.value);
          setValue(val as number);
          if (val !== undefined) {
            onChange(val);
          }
        }}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        className={`
          w-full
          bg-gray-900
          text-gray-100
          border-2
          border-gray-700
          rounded-lg
          p-4
          font-mono
          placeholder-gray-500
          transition-all
          duration-300
          focus:outline-none
          focus:ring-2
          focus:ring-blue-500
          focus:border-transparent
          hover:border-gray-600
          shadow-inner
          shadow-gray-950
          backdrop-blur-sm
          bg-opacity-90
          [&::-webkit-inner-spin-button]:appearance-none
          [&::-webkit-outer-spin-button]:appearance-none
          ${className}
        `}
        style={{
          WebkitTapHighlightColor: "transparent",
        }}
      />
    </div>
  );
}
