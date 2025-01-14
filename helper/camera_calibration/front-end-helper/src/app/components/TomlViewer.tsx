import React, { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism"; // Dark theme
import toast, { Toaster } from "react-hot-toast"; // Toast for notifications
import { FaCopy } from "react-icons/fa";

interface TomlViewerProps {
  toml: string;
  title?: string; // Optional title for the component
}

export function TomlViewer({ toml, title = "TOML Viewer" }: TomlViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(toml);
    setCopied(true);
    toast.success("TOML copied to clipboard!");
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
      <SyntaxHighlighter language="toml" style={dracula} showLineNumbers>
        {toml}
      </SyntaxHighlighter>
    </div>
  );
}
