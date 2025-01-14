"use client";

import { StandardButton } from "../components/Button";
import { PageSplit } from "../components/PageSplit";
import LiveStream from "../components/LiveStream";
import { Dropdown } from "../components/Dropdown";
import { useState } from "react";
import { LabeledNumberInput } from "../components/TextInput";
import RemovableImageFrame from "../components/CustomImageFrame";
import { GoHome } from "../components/GoHome";
import { TomlViewer } from "../components/TomlViewer";

export default function Calibr() {
  const [selectedMethod, setSelectedMethod] = useState<
    "checkerboard" | "apriltag"
  >("checkerboard");
  const [checkerBoardWidth, setCheckerBoardWidth] = useState<number>(0);
  const [checkerBoardHeight, setCheckerBoardHeight] = useState<number>(0);
  const [checkerBoardSquareSize, setCheckerBoardSquareSize] =
    useState<number>(0);
  const [tomlData, setTomlData] = useState<string | null>(null);
  const [selectingImages, setSelectingImages] = useState<boolean>(false);

  const [selectedImages, setSelectedImages] = useState<
    {
      image: string;
      image_id: number;
    }[]
  >([]);

  async function sendRemoveImage(index: number) {
    await fetch("/backend/remove_image", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        image_id: index,
      }),
    });
  }

  async function sendSelectImage() {
    const response_image = await fetch("/backend/pick_image", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const image = await response_image.json();
    if (image.error) {
      console.error(image.error);
      return;
    }

    setSelectedImages([...selectedImages, image]);
  }

  async function requestCalibrationData() {
    const response = await fetch("/backend/get_calibration_data", {
      method: "GET",
    });
    const data = await response.json();
    if (data.error) {
      console.error(data.error);
      return null;
    }

    return data.toml_string;
  }

  async function sendUpdateCalibrationParams(
    checkerboard_width: number,
    checkerboard_height: number,
    checkerboard_square_size: number,
    which_calibration: "checkerboard" | "apriltag"
  ) {
    console.log("Sending update calibration params", {
      checkerboard_width,
      checkerboard_height,
      checkerboard_square_size,
      which_calibration,
    });
    await fetch("/backend/update_calibration", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        checkerboard_width,
        checkerboard_height,
        checkerboard_square_size,
        which_calibration,
      }),
    });
  }

  async function sendUpdateMode(mode: "checkerboard" | "apriltag" | "video") {
    console.log("Sending update mode", mode);
    await fetch("/backend/update_mode", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        new_mode: mode,
      }),
    });
  }

  return (
    <main className="w-full h-screen">
      <PageSplit>
        <div className="p-10 flex flex-col gap-20">
          <div className="flex flex-col gap-5">
            <div className="w-full flex gap-5">
              <div className="w-1/2">
                <Dropdown
                  options={[
                    { view: "Checkerboard", real: "checkerboard" },
                    { view: "April Tags", real: "apriltag" },
                  ]}
                  placeholder="Select a calibration method..."
                  onChange={(value) => {
                    setSelectedMethod(value as "checkerboard" | "apriltag");
                  }}
                />
              </div>
              <div className="w-1/2">
                <StandardButton
                  text="Select Image"
                  onClick={async () => {
                    console.log("Sending select image");
                    await sendSelectImage();
                  }}
                />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex gap-10">
                <LabeledNumberInput
                  label="Checkerboard Width"
                  onChange={async (value) => {
                    setCheckerBoardWidth(value);
                    await sendUpdateCalibrationParams(
                      value,
                      checkerBoardHeight,
                      checkerBoardSquareSize,
                      selectedMethod
                    );
                  }}
                />
                <LabeledNumberInput
                  label="Checkerboard Height"
                  onChange={async (value) => {
                    setCheckerBoardHeight(value);
                    await sendUpdateCalibrationParams(
                      checkerBoardWidth,
                      value,
                      checkerBoardSquareSize,
                      selectedMethod
                    );
                  }}
                />
              </div>
              <LabeledNumberInput
                label="Checkerboard Square Size (m)"
                onChange={async (value) => {
                  setCheckerBoardSquareSize(value);
                  await sendUpdateCalibrationParams(
                    checkerBoardWidth,
                    checkerBoardHeight,
                    value,
                    selectedMethod
                  );
                }}
              />
              <div className="flex gap-5">
                <LabeledNumberInput
                  label="Image Width (px)"
                  onChange={async (value) => {
                    setCheckerBoardSquareSize(value);
                    await sendUpdateCalibrationParams(
                      checkerBoardWidth,
                      checkerBoardHeight,
                      value,
                      selectedMethod
                    );
                  }}
                />
                <LabeledNumberInput
                  label="Image Height (px)"
                  onChange={async (value) => {
                    setCheckerBoardSquareSize(value);
                    await sendUpdateCalibrationParams(
                      checkerBoardWidth,
                      checkerBoardHeight,
                      value,
                      selectedMethod
                    );
                  }}
                />
              </div>
            </div>
            <StandardButton
              text={selectingImages ? "End Calibration" : "Begin Calibration"}
              onClick={async () => {
                const selecting = !selectingImages;
                setSelectingImages(selecting);

                if (selecting) {
                  await sendUpdateMode(selectedMethod);
                  setTomlData(null);
                } else {
                  const res = await requestCalibrationData();
                  if (res) {
                    setTomlData(res);
                  }

                  await new Promise((resolve) => setTimeout(resolve, 100));

                  await sendUpdateMode("video");
                  setSelectedImages([]);
                }
              }}
            />
          </div>

          {tomlData && (
            <TomlViewer toml={tomlData} title="Camera Calibration Data" />
          )}
          <div className="absolute bottom-4 left-4 h-fit z-40">
            <GoHome url="/" />
          </div>
        </div>
        <div className="p-10 flex flex-col gap-5">
          <div className="w-full h-full flex flex-col gap-5">
            <LiveStream />
          </div>
          <div className="w-full h-full grid grid-cols-3 gap-4">
            {selectedImages.map((image, index) => (
              <div key={index} className="aspect-square">
                <RemovableImageFrame
                  src={`data:image/jpeg;base64,${image.image}`}
                  alt={`Image ${index}`}
                  onRemove={async () => {
                    await sendRemoveImage(image.image_id);
                    setSelectedImages(
                      selectedImages.filter((_, i) => i !== index)
                    );
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      </PageSplit>
    </main>
  );
}
