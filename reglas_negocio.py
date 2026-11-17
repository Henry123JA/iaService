"""Umbrales comunicados por el usuario para sw-scala."""
import math


def nivel_riesgo(score):
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("El score debe ser numerico")
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("El score debe estar entre 0 y 100")
    if score >= 65:
        return "ALTO"
    if score >= 35:
        return "MEDIO"
    return "BAJO"
