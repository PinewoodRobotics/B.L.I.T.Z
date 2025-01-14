import React, { useState } from "react";
import toast, { Toaster } from "react-hot-toast"; // Optional: Toast for notifications
import { FaCopy } from "react-icons/fa";
import JsonView from "@uiw/react-json-view";
import { nordTheme } from "@uiw/react-json-view/nord";

interface JsonViewerProps {
  data: object;
  title?: string; // Optional title for the viewer
}

export function JsonViewer({ data, title = "JSON Viewer" }: JsonViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    toast.success("JSON copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-4 bg-gray-900 text-white rounded-md shadow-lg">
      <Toaster position="top-right" reverseOrder={false} />
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">{title}</h2>
        <button
          onClick={handleCopy}
          className="flex items-center bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 focus:outline-none"
        >
          <FaCopy className="w-5 h-5 mr-2" />
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <JsonView
        value={data}
        displayDataTypes={false}
        displayObjectSize={true}
        style={{
          ...nordTheme,
          borderRadius: "0.5rem",
          padding: "0.5rem",
        }}
      />
    </div>
  );
}
