from ..runtime.base import VideoGenerationAdapter
from ..runtime.hunyuan_15_adapter import Hunyuan15Adapter
from ..runtime.hunyuan_original_adapter import HunyuanOriginalAdapter
from ..runtime.mock_adapter import MockVideoAdapter


class ModelManager:
    def __init__(self) -> None:
        self._adapters: dict[str, VideoGenerationAdapter] = {
            "mock": MockVideoAdapter(),
            "hunyuan_original": HunyuanOriginalAdapter(),
            "hunyuan_15": Hunyuan15Adapter(),
        }
        self._loaded_runtime: str | None = None

    @property
    def loaded_runtime(self) -> str | None:
        return self._loaded_runtime

    def available_runtimes(self) -> list[str]:
        return sorted(self._adapters)

    def get_adapter(self, runtime: str) -> VideoGenerationAdapter:
        try:
            return self._adapters[runtime]
        except KeyError as exc:
            raise RuntimeError(f"Unsupported runtime: {runtime}") from exc

    def load(self, runtime: str) -> VideoGenerationAdapter:
        adapter = self.get_adapter(runtime)
        if self._loaded_runtime != runtime:
            adapter.validate()
            adapter.load()
            self._loaded_runtime = runtime
        return adapter

    def unload(self) -> None:
        if self._loaded_runtime is None:
            return
        self.get_adapter(self._loaded_runtime).unload()
        self._loaded_runtime = None


model_manager = ModelManager()
