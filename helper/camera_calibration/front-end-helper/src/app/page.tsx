"use client";

import { StandardButton } from "./components/Button";
import { PageSplit } from "./components/PageSplit";
import LiveStream from "./components/LiveStream";
import { useRouter } from "next/navigation";
import { CheckBox } from "./components/CheckBox";
import { GradientSlider } from "./components/Slider";
import { useEffect, useState } from "react";
import { TransformationConfig } from "./interfaces/update_mode";

export default function Home() {
  const router = useRouter();
  const [transformationConfig, setTransformationConfig] =
    useState<TransformationConfig | null>(null);

  const [doUndistort, setDoUndistort] = useState(false);
  const [cameraConfig, setCameraConfig] = useState("");

  useEffect(() => {
    if (!transformationConfig) {
      fetchTransformationConfig().then((config) => {
        setTransformationConfig(config);
        if (config.undistort.undistort) {
          setDoUndistort(true);
        }
      });
    }
  }, [transformationConfig]);

  useEffect(() => {
    sendUpdateMode("video");
  }, []);

  async function fetchTransformationConfig() {
    const response = await fetch("/backend/get_saved_transformation_config", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
    return await response.json();
  }

  async function sendUpdateSettings(new_config: Partial<TransformationConfig>) {
    await fetch("/backend/update_settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ...new_config }),
    });
  }

  async function sendUpdateMode(mode: "checkerboard" | "apriltag" | "video") {
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
      {transformationConfig && (
        <PageSplit>
          <div className="w-full h-full p-10">
            <div className="flex flex-col gap-10">
              <div className="text-4xl font-bold">Camera Feed Calibration</div>
              <div className="flex flex-col gap-5">
                <div className="flex flex-col gap-3">
                  <div className="text-2xl font-bold">Detection Settings</div>
                  <CheckBox
                    label="Undistort Image"
                    onChange={async (v) => {
                      setDoUndistort(v);
                      if (!v) {
                        await sendUpdateSettings({
                          undistort: {
                            undistort: false,
                            camera_matrix: [],
                            dist_coeff: [],
                          },
                        });
                      }
                    }}
                    checked={doUndistort}
                  />
                  {doUndistort && (
                    <textarea
                      className="w-full h-40 text-black"
                      value={cameraConfig}
                      onChange={async (e) => {
                        setCameraConfig(e.target.value);

                        const camera_config = JSON.parse(e.target.value);
                        console.log(e.target.value + "camera_config");
                        if (
                          camera_config.camera_matrix &&
                          camera_config.dist_coeff
                        ) {
                          console.log(camera_config);
                          await sendUpdateSettings({
                            undistort: {
                              undistort: true,
                              camera_matrix: camera_config.camera_matrix,
                              dist_coeff: camera_config.dist_coeff,
                            },
                          });
                        }
                      }}
                    />
                  )}
                  <CheckBox
                    label="Detect April Tags"
                    onChange={(v) => {
                      setTransformationConfig({
                        ...transformationConfig,
                        detect_april_tags: v,
                      });
                    }}
                    checked={transformationConfig.detect_april_tags}
                  />
                  <CheckBox
                    label="Use Grayscale"
                    onChange={async (v) => {
                      setTransformationConfig({
                        ...transformationConfig,
                        use_grayscale: v,
                      });
                      await sendUpdateSettings({
                        ...transformationConfig,
                        use_grayscale: v,
                      });
                    }}
                    checked={transformationConfig.use_grayscale}
                  />
                </div>
                <div className="flex flex-col gap-3">
                  <div className="text-2xl font-bold">Color Settings</div>
                  <div className="flex flex-col gap-10 mt-5">
                    <div className="w-60 h-4">
                      <GradientSlider
                        onChange={async (v) => {
                          const v1 = v[0];
                          const v2 = v[1];
                          console.log(v1, v2);

                          setTransformationConfig({
                            ...transformationConfig,
                            threshholding: {
                              ...transformationConfig.threshholding,
                              hue: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });

                          await sendUpdateSettings({
                            ...transformationConfig,
                            threshholding: {
                              ...transformationConfig.threshholding,
                              hue: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });
                        }}
                        min={0}
                        max={360}
                        step={0.5}
                        initialValues={[
                          transformationConfig.threshholding?.hue?.min ?? 0,
                          transformationConfig.threshholding?.hue?.max ?? 360,
                        ]}
                      />
                    </div>
                    <div className="w-60 h-4">
                      <GradientSlider
                        onChange={async (v) => {
                          const v1 = v[0];
                          const v2 = v[1];

                          setTransformationConfig({
                            ...transformationConfig,
                            threshholding: {
                              ...transformationConfig.threshholding,
                              saturation: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });

                          await sendUpdateSettings({
                            ...transformationConfig,
                            threshholding: {
                              ...transformationConfig.threshholding,
                              saturation: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });
                        }}
                        min={0}
                        max={255}
                        step={0.5}
                        initialValues={[
                          transformationConfig.threshholding?.saturation?.min ??
                            0,
                          transformationConfig.threshholding?.saturation?.max ??
                            255,
                        ]}
                      />
                    </div>
                    <div className="w-60 h-4">
                      <GradientSlider
                        onChange={async (v) => {
                          const v1 = v[0];
                          const v2 = v[1];

                          setTransformationConfig({
                            ...transformationConfig,
                            threshholding: {
                              ...transformationConfig.threshholding,
                              value: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });

                          await sendUpdateSettings({
                            threshholding: {
                              ...transformationConfig.threshholding,
                              value: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });
                        }}
                        min={0}
                        max={255}
                        step={0.5}
                        initialValues={[
                          transformationConfig.threshholding?.value?.min ?? 0,
                          transformationConfig.threshholding?.value?.max ?? 255,
                        ]}
                      />
                    </div>
                  </div>
                </div>
                <div className="flex flex-col gap-3">
                  <div className="text-2xl font-bold">Camera Settings</div>
                  <div className="flex flex-col gap-10 mt-5">
                    <div className="w-60 h-4">
                      <GradientSlider
                        onChange={async (v) => {
                          const v1 = v[0];
                          const v2 = v[1];
                          console.log(v1, v2);

                          setTransformationConfig({
                            ...transformationConfig,
                            camera_settings: {
                              ...transformationConfig.camera_settings,
                              exposure: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });

                          await sendUpdateSettings({
                            ...transformationConfig,
                            camera_settings: {
                              ...transformationConfig.camera_settings,
                              gain: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });
                        }}
                        min={0}
                        max={360}
                        step={0.5}
                        initialValues={[
                          transformationConfig.threshholding?.hue?.min ?? 0,
                          transformationConfig.threshholding?.hue?.max ?? 360,
                        ]}
                      />
                    </div>
                    <div className="w-60 h-4">
                      <GradientSlider
                        onChange={async (v) => {
                          const v1 = v[0];
                          const v2 = v[1];

                          setTransformationConfig({
                            ...transformationConfig,
                            camera_settings: {
                              ...transformationConfig.camera_settings,
                              gain: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });

                          await sendUpdateSettings({
                            ...transformationConfig,
                            camera_settings: {
                              ...transformationConfig.camera_settings,
                              gain: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });
                        }}
                        min={0}
                        max={255}
                        step={0.5}
                        initialValues={[
                          transformationConfig.camera_settings?.gain?.min ?? 0,
                          transformationConfig.camera_settings?.gain?.max ??
                            255,
                        ]}
                      />
                    </div>
                    <div className="w-60 h-4">
                      <GradientSlider
                        onChange={async (v) => {
                          const v1 = v[0];
                          const v2 = v[1];

                          setTransformationConfig({
                            ...transformationConfig,
                            camera_settings: {
                              ...transformationConfig.camera_settings,
                              gamma: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });

                          await sendUpdateSettings({
                            camera_settings: {
                              ...transformationConfig.camera_settings,
                              gamma: {
                                min: v1,
                                max: v2,
                              },
                            },
                          });
                        }}
                        min={0}
                        max={255}
                        step={0.5}
                        initialValues={[
                          transformationConfig.camera_settings?.gamma?.min ?? 0,
                          transformationConfig.camera_settings?.gamma?.max ??
                            255,
                        ]}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <StandardButton
                text="Switch To Calibration"
                onClick={() => {
                  router.push("/calibration");
                }}
              />
            </div>
          </div>
          <div className="p-10">
            <LiveStream />
          </div>
        </PageSplit>
      )}
    </main>
  );
}
