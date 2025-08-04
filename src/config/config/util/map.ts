import { createCanvas } from "canvas";
import fs from "fs";
import type { MapData as MapDataThrift } from "../../../blitz/generated/thrift/gen-nodejs/common_types";

export type MapData = MapDataThrift;

export function fromImageToMap(
  imagePath: string,
  pixel_split_per_pixel: number = 1
): MapData {
  const { Image } = require("canvas");
  const imageBuffer = fs.readFileSync(imagePath);
  const img = new Image();
  img.src = imageBuffer;

  if (!img.complete || img.width === 0 || img.height === 0) {
    throw new Error("Image failed to load or is invalid");
  }

  const width = img.width;
  const height = img.height;
  const splitWidth = width * pixel_split_per_pixel;
  const splitHeight = height * pixel_split_per_pixel;
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0, width, height);
  const imageData = ctx.getImageData(0, 0, width, height).data;
  const boolArray: boolean[] = [];
  for (let y = 0; y < height; y++) {
    for (let splitY = 0; splitY < pixel_split_per_pixel; splitY++) {
      for (let x = 0; x < width; x++) {
        for (let splitX = 0; splitX < pixel_split_per_pixel; splitX++) {
          const i = y * width + x;
          const r = imageData[i * 4];
          const g = imageData[i * 4 + 1];
          const b = imageData[i * 4 + 2];
          if (r === 255 && g === 255 && b === 255) {
            boolArray.push(false);
          } else {
            boolArray.push(true);
          }
        }
      }
    }
  }

  return {
    map_size_x: splitWidth,
    map_size_y: splitHeight,
    map_data: boolArray,
  } as MapData;
}
