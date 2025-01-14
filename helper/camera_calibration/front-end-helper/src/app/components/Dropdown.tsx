"use client";

import React, { useState, useRef, useEffect } from "react";

interface DropdownOption {
  view: string;
  real: string;
}

interface DropdownProps {
  options: DropdownOption[];
  defaultValue?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function Dropdown({
  options,
  defaultValue,
  onChange,
  placeholder = "Select an option",
  className = "",
}: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedOption, setSelectedOption] = useState<DropdownOption | null>(
    defaultValue
      ? options.find((opt) => opt.real === defaultValue) || null
      : null
  );
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSelect = (option: DropdownOption) => {
    setSelectedOption(option);
    setIsOpen(false);
    onChange?.(option.real);
  };

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-2 text-left bg-gray-800 text-gray-200 rounded-lg 
                   hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 
                   transition-colors duration-200 flex justify-between items-center"
      >
        <span
          className={`${!selectedOption ? "text-gray-400" : "text-gray-200"}`}
        >
          {selectedOption ? selectedOption.view : placeholder}
        </span>
        <svg
          className={`w-5 h-5 transition-transform duration-200 ${
            isOpen ? "transform rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div
          className="absolute w-full mt-2 bg-gray-800 rounded-lg shadow-lg 
                        border border-gray-700 z-50 max-h-60 overflow-auto"
        >
          {options.map((option, index) => (
            <div
              key={index}
              onClick={() => handleSelect(option)}
              className="px-4 py-2 cursor-pointer hover:bg-gray-700 
                         first:rounded-t-lg last:rounded-b-lg text-gray-200
                         transition-colors duration-200"
            >
              {option.view}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
