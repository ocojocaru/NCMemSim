from __future__ import annotations
from collections.abc import Callable
from typing import Any

class MaterialRegistry:
    def __init__(self) -> None:
        self._factories: dict[str,Callable[...,Any]]={}
    def register(self,name: str,factory: Callable[...,Any],*,replace: bool=False) -> None:
        key=name.strip().lower()
        if key in self._factories and not replace:
            raise KeyError(f"Material model {name!r} is already registered.")
        self._factories[key]=factory
    def create(self,name: str,**kwargs: Any) -> Any:
        try: factory=self._factories[name.strip().lower()]
        except KeyError as exc: raise KeyError(f"Unknown material model {name!r}. Available: {self.available()}") from exc
        return factory(**kwargs)
    def available(self) -> tuple[str,...]:
        return tuple(sorted(self._factories))

registry=MaterialRegistry()
