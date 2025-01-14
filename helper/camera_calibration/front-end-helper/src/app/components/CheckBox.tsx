"use client";

import React, { useState } from "react";

interface CheckBoxProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  label?: string;
}

export function CheckBox({ checked = false, onChange, label }: CheckBoxProps) {
  const [isChecked, setIsChecked] = useState(checked);

  return (
    <label className="inline-flex items-center cursor-pointer">
      <div className="relative">
        <input
          type="checkbox"
          className="sr-only peer"
          checked={isChecked}
          onChange={(e) => {
            setIsChecked(e.target.checked);
            onChange?.(e.target.checked);
          }}
        />
        <div
          className="w-6 h-6 bg-gray-800 border-2 border-gray-600 rounded-md 
                      peer-checked:bg-blue-600 peer-checked:border-blue-500
                      transition-all duration-200 ease-in-out
                      after:content-[''] after:absolute after:left-[7px] after:top-[3px]
                      after:w-[8px] after:h-[14px] after:border-white
                      after:border-r-2 after:border-b-2 after:transform 
                      after:rotate-45 after:opacity-0
                      peer-checked:after:opacity-100 after:transition-opacity
                      hover:border-gray-400 peer-checked:hover:border-blue-400"
        />
      </div>
      {label && <span className="ml-3 text-gray-200 select-none">{label}</span>}
    </label>
  );
}
