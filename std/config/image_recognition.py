from std.config_util import check_config


required_keys_main = ["image-input-topic", "image-output-topic", "model", "device"]

required_keys_trainer = [
    "name",
    "imgsz",
    "epochs",
    "data-yaml-path",
    "dataset-root-path",
    "batch-size",
]


class TrainerConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys_trainer, "TrainerConfig")
        self.name = config["name"]
        self.imgsz = config["imgsz"]
        self.epochs = config["epochs"]
        self.data_yaml_path = config["data-yaml-path"]
        self.dataset_root_path = config["dataset-root-path"]
        self.batch_size = config["batch-size"]


class ImageRecognitionConfig:
    def __init__(self, config: dict):
        check_config(config, required_keys_main, "ImageRecognitionConfig")
        self.image_input_topic = config["image-input-topic"]
        self.image_output_topic = config["image-output-topic"]
        self.model = config["model"]
        self.device = config["device"]

        self.trainer = TrainerConfig(config["trainer"])
