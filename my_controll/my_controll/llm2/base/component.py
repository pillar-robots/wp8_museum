from abc import ABC, abstractmethod
from typing import Type, TypeVar, Generic
from dataclasses import dataclass
import logging

from .exceptions import NotStartedError, IncorrectConfigurationError


@dataclass(frozen=True)
class ComponentConfig:
    pass


ConfigType = TypeVar("ConfigType", bound=ComponentConfig)

class Component(ABC, Generic[ConfigType]):
    config_class: Type[ConfigType]

    # === INITIALIZATION ===

    def __init__(self, config:ConfigType):
        if not isinstance(config, self.config_class):
            raise IncorrectConfigurationError(
                self.__class__.__name__,
                self.config_class.__name__,
                type(config).__name__
            )
        self.config = config
        self.is_started = False

    def __init_subclass__(cls):
        if ABC in cls.__bases__:  # Skip check if class is abstract
            return
        if not hasattr(cls, "config_class"):
            raise NotImplementedError(
                "Components must specify their configuration class "
                f"by defining 'config_class'."
            )

    # === MAGIC METHODS ===

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.close()
        else:
            try:
                self.close()
            except Exception:
                logging.getLogger(__name__).exception("Component cleanup failed.")

    # === EXPOSED METHODS ===

    def start(self, *args, **kwargs):
        if self.is_started:
            return
        try:
            self._do_start(*args, **kwargs)
        except BaseException:
            try:
                self._do_close()
            except Exception:
                logging.getLogger(__name__).exception("Startup cleanup failed.")
            raise
        self.is_started = True

    def run(self, *args, **kwargs):
        if not self.is_started:
            raise NotStartedError(self.__class__.__name__)
        return self._do_run(*args, **kwargs)

    def close(self, *args, **kwargs):
        if not self.is_started:
            return
        try:
            self._do_close(*args, **kwargs)
        finally:
            self.is_started = False

    # === MAGIC METHODS ===

    def __repr__(self):
        return (
            f"{self.__class__.__name__} "
            f"(status: {'started' if self.is_started else 'stopped'})"
        )

    # === ABSTRACT METHODS ===

    @abstractmethod
    def _do_start(self, *args, **kwargs):
        pass

    @abstractmethod
    def _do_run(self, *args, **kwargs):
        pass

    @abstractmethod
    def _do_close(self, *args, **kwargs):
        pass
