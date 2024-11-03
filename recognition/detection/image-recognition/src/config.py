from log import log_error, log_info

main_required = ["image-input-topic", "image-output-topic", "model", "device"]

autobahn_required = [
    "internal-sub-port",
    "internal-pub-port",
]

trainer_required = [
    "name",
    "imgsz",
    "epochs",
    "data-yaml-path",
    "dataset-root-path",
    "batch-size",
]


class Autobahn:
    def __init__(self, config):
        self.check(config)
        self.internal_sub_port = config["internal-sub-port"]
        self.internal_pub_port = config["internal-pub-port"]

    def check(self, config):
        for key in autobahn_required:
            if key not in config:
                log_error("Config Resolver", f"Missing {key} in config.")
                print()
                raise Exception("")


class Trainer:
    def __init__(self, config):
        check_config(config, trainer_required, "trainer")
        self.name = config["name"]
        self.imgsz = config["imgsz"]
        self.epochs = config["epochs"]
        self.data_yaml_path = config["data-yaml-path"]
        self.dataset_root_path = config["dataset-root-path"]
        self.batch_size = config["batch-size"]


class Config:
    def __init__(self, config):
        self.autobahn = Autobahn(config["autobahn"])
        log_info("Config Resolver", "Autobahn Config loaded!")

        config = config["image-recognition"]

        log_info("Config Resolver", "Main Config loaded!")

        self.trainer = Trainer(config["trainer"])
        log_info("Config Resolver", "Trainer Config loaded!")

        check_config(config, main_required, "image-recognition")
        self.image_input_topic = config["image-input-topic"]
        self.image_output_topic = config["image-output-topic"]
        self.model = config["model"]
        self.device = config["device"]


def check_config(config, required, submodule_name):
    for key in required:
        if key not in config:
            log_error("Config Resolver", f"Missing {key} in {submodule_name} config.")
            print()
            raise Exception()
