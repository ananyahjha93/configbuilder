from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from glob import glob
from os import PathLike
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar, Union, cast

from omegaconf import DictConfig, ListConfig
from omegaconf import OmegaConf as om
from omegaconf.errors import OmegaConfBaseException

__all__ = [
    "CliError",
    "ConfigClassA",
    "ConfigClassB",
    "ConfigClassC",
    "OptionSelector",
]


PathOrStr = Union[str, PathLike]

C = TypeVar("C", bound="BaseConfig")
D = TypeVar("D", bound="DictConfig|ListConfig")


def is_url(path: PathOrStr) -> bool:
    return re.match(r"[a-z0-9]+://.*", str(path)) is not None


def clean_opt(arg: str) -> str:
    if "=" not in arg:
        arg = f"{arg}=True"
    name, val = arg.split("=", 1)
    name = name.strip("-").replace("-", "_")
    return f"{name}={val}"


class StrEnum(str, Enum):
    """
    This is equivalent to Python's :class:`enum.StrEnum` since version 3.11.
    We include this here for compatibility with older version of Python.
    """

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"'{str(self)}'"


class ConfigurationError(Exception):
    """
    An error with a configuration file.
    """


class CliError(Exception):
    """
    An error from incorrect CLI usage.
    """


class BaseConfig:
    @classmethod
    def _register_resolvers(cls, validate_paths: bool = True):
        # Expands path globs into a list.
        def path_glob(*paths) -> List[str]:
            out = []
            for path in paths:
                matches = sorted(glob(path))
                if not matches and validate_paths:
                    raise FileNotFoundError(f"{path} does not match any files or dirs")
                out.extend(matches)
            return out

        # Chooses the first path in the arguments that exists.
        def path_choose(*paths) -> str:
            for path in paths:
                if is_url(path) or Path(path).exists():
                    return path
            if validate_paths:
                raise FileNotFoundError(", ".join(paths))
            else:
                return ""

        om.register_new_resolver("path.glob", path_glob, replace=True)
        om.register_new_resolver("path.choose", path_choose, replace=True)

    @classmethod
    def update_legacy_settings(cls, config: D) -> D:
        """
        Update the legacy config settings whose schemas have undergone backwards-incompatible changes.
        """
        return config

    @classmethod
    def new(cls: Type[C], **kwargs) -> C:
        cls._register_resolvers()
        conf = om.structured(cls)
        try:
            if kwargs:
                conf = om.merge(conf, kwargs)
            return cast(C, om.to_object(conf))
        except OmegaConfBaseException as e:
            raise ConfigurationError(str(e))

    @classmethod
    def load(
        cls: Type[C],
        path: PathOrStr,
        overrides: Optional[List[str]] = None,
        key: Optional[str] = None,
        validate_paths: bool = True,
    ) -> C:
        """Load from a YAML file."""
        cls._register_resolvers(validate_paths=validate_paths)
        schema = om.structured(cls)
        try:
            raw = om.load(str(path))
            if key is not None:
                raw = raw[key]  # type: ignore
            raw = cls.update_legacy_settings(raw)
            conf = om.merge(schema, raw)
            if overrides:
                conf = om.merge(conf, om.from_dotlist(overrides))
            return cast(C, om.to_object(conf))
        except OmegaConfBaseException as e:
            raise ConfigurationError(str(e))

    def save(self, path: PathOrStr) -> None:
        """Save to a YAML file."""
        om.save(config=self, f=str(path))

    def asdict(self, exclude: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        out = asdict(self)  # type: ignore
        if exclude is not None:
            for name in exclude:
                if name in out:
                    del out[name]
        return out


class OptionSelector(StrEnum):
    default = "default"
    """
    The default option.
    """

    option_a = "option_a"
    """
    Describe option_a.
    """

    option_b = "option_b"
    """
    Describe option_b.
    """


@dataclass
class ConfigClassA(BaseConfig):
    list_a: Optional[List[str]] = None
    """
    A list of strings.
    """


@dataclass
class ConfigClassB(BaseConfig):
    label: str = 0.0
    """
    Label of config class B.
    """

    list_b: Optional[List[str]] = None
    """
    List within a config class B.
    """


@dataclass
class ConfigClassC(BaseConfig):
    a: int = 0
    """
    Option A.
    """

    b: Optional[float] = None
    """
    Option B.
    """

    c: bool = False
    """
    Option C.
    """

    option_selector: OptionSelector = OptionSelector.default
    """
    Assign config from a pre-defined set of enums.
    """

    config_class_a: ConfigClassA = field(default_factory=ConfigClassA)
    """
    We define a nested configuration class here.
    """

    config_class_b: List[ConfigClassB] = field(default_factory=list)
    """
    We define an option to provide a list of configs of a particular class. (ex- list of eval configs or checkpointers)
    """
