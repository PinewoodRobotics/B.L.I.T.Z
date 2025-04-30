import importlib
import inspect
import os
import pkgutil
from typing import Dict, Type
from .pipeline import Pipeline


class PipelineManager:
    def __init__(self):
        self.pipelines: Dict[str, Type[Pipeline]] = {}
        self._discover_pipelines()

    def _discover_pipelines(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for _, name, _ in pkgutil.iter_modules([current_dir]):
            if name == "pipeline" or name == "pipeline_manager":
                continue
            try:
                module = importlib.import_module(
                    f".{name}",
                    package="project.example.position_debug.3d.object_pipelines",
                )
                for _, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, Pipeline)
                        and obj != Pipeline
                    ):
                        instance = obj()
                        self.pipelines[instance.get_topic()] = obj
            except Exception as e:
                print(f"Error loading pipeline {name}: {e}")

    def get_pipeline(self, topic: str) -> Type[Pipeline] | None:
        return self.pipelines.get(topic)

    def get_all_topics(self) -> list[str]:
        return list(self.pipelines.keys())
