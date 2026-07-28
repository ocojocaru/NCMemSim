from __future__ import annotations

def validate_fraction(x: float) -> float:
    x=float(x)
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"Composition fraction must be in [0,1], received {x}.")
    return x

def linear(x: float, a: float, b: float) -> float:
    x=validate_fraction(x)
    return (1.0-x)*a+x*b

def bowing(x: float, a: float, b: float, bowing_parameter: float=0.0) -> float:
    x=validate_fraction(x)
    return linear(x,a,b)-bowing_parameter*x*(1.0-x)

def vegard(x: float, a: float, b: float, bowing_parameter: float=0.0) -> float:
    return bowing(x,a,b,bowing_parameter)
