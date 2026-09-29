from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from .component import Component, ComponentConfig


@dataclass(frozen=True)
class PipelineConfig(ComponentConfig):
    pass


PipeConfigType = TypeVar("PipeConfigType", bound=PipelineConfig)

class Pipeline(Component[PipeConfigType], ABC):
    def __init__(self, config:PipeConfigType):
        super().__init__(config)
        self.is_paused = False

    def close(self, *args, **kwargs):
        try:
            super().close(*args, **kwargs)
        finally:
            self.is_paused = False

    # === EXPOSED METHODS ===

    def pause(self, *args, **kwargs):
        if not self.is_started or self.is_paused:
            return
        self._do_pause(*args, **kwargs)
        self.is_paused = True

    def resume(self, *args, **kwargs):
        if not self.is_started or not self.is_paused:
            return
        self._do_resume(*args, **kwargs)
        self.is_paused = False

    # === ABSTRACT METHODS ===

    @abstractmethod
    def _do_pause(self, *args, **kwargs):
        pass

    @abstractmethod
    def _do_resume(self, *args, **kwargs):
        pass
