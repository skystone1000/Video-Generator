from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ProgressCallback(Protocol):
    def __call__(self, progress: float, stage: str, message: str | None = None) -> None:
        ...


@dataclass
class GenerationResult:
    video_path: Path
    metadata_path: Path | None = None
    logs_path: Path | None = None
    model_version: str | None = None


class VideoGenerationAdapter(ABC):
    name: str
    model_version: str | None = None

    @abstractmethod
    def validate(self) -> None:
        ...

    @abstractmethod
    def load(self) -> None:
        ...

    @abstractmethod
    def generate(self, request, output_dir: str | Path, progress: ProgressCallback) -> GenerationResult:
        ...

    @abstractmethod
    def unload(self) -> None:
        ...
