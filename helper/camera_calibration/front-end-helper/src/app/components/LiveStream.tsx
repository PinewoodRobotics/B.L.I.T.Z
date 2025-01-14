"use client";

import { useEffect, useRef, useState } from "react";

export default function LiveStream() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [port] = useState<number>(5005);

  useEffect(() => {
    console.log("Starting WebSocket connection");
    const socket = new WebSocket(`ws://localhost:${port}`);
    socket.binaryType = "arraybuffer"; // Set WebSocket to handle binary data

    socket.onopen = () => {
      console.log("Connected to WebSocket server");
      socket.send("request_frame"); // Send request to start streaming frames
    };

    socket.onmessage = (event) => {
      const canvas = canvasRef.current;

      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          // Create a Blob from the raw binary data
          const blob = new Blob([event.data], { type: "image/jpeg" });

          // Use an Image object to render the Blob to the canvas
          const image = new Image();
          image.src = URL.createObjectURL(blob);

          image.onload = () => {
            canvas.height = (canvas.width / image.width) * image.height;

            ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear previous frame
            ctx.drawImage(image, 0, 0, canvas.width, canvas.height); // Draw new frame
            URL.revokeObjectURL(image.src); // Release object URL to free memory
          };
        }
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socket.onclose = () => {
      console.log("WebSocket connection closed");
    };

    return () => {
      console.log("Cleaning up WebSocket");
      socket.close();
    };
  }, [port]);

  return (
    <div>
      <canvas ref={canvasRef} className="w-full h-full border-2 border-white" />
    </div>
  );
}
