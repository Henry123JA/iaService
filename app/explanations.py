"""Explicaciones locales del score de REPROBACION, sin atribuciones causales."""
import math

import numpy as np
import shap


VARIABLES = {
    "porcentaje_asistencia": ("Asistencia", "ASISTENCIA", "%"),
    "faltas_injustificadas": ("Faltas injustificadas", "ASISTENCIA", "faltas"),
    "atrasos": ("Llegadas tarde", "ASISTENCIA", "atrasos"),
    "promedio_calificaciones": ("Promedio de calificaciones", "ACADEMICO", "/100"),
    "tendencia_notas": ("Tendencia de notas", "EVOLUCION", "puntos"),
    "observaciones_negativas": ("Observaciones de seguimiento", "DISCIPLINA", "observaciones"),
}


def pesos_relativos(contribuciones):
    """Porcentajes de magnitud absoluta; no son probabilidad ni causalidad."""
    magnitudes = [abs(v) for v in contribuciones]
    total = sum(magnitudes)
    if total < 1e-10:
        return [0.0] * len(magnitudes)
    raw = [v / total * 10000 for v in magnitudes]
    unidades = [math.floor(v) for v in raw]
    orden = sorted(range(len(raw)), key=lambda i: raw[i] - unidades[i], reverse=True)
    for i in orden[:10000 - sum(unidades)]:
        unidades[i] += 1
    return [v / 100 for v in unidades]


class ExplicadorRiesgo:
    def __init__(self, model, nombres):
        self.nombres = list(nombres)
        self.clase = list(model.classes_).index(1)
        # Para sklearn RandomForestClassifier la salida raw es probabilidad.
        # La reconstruccion se verifica explicitamente contra predict_proba.
        self.explainer = shap.TreeExplainer(
            model, model_output="raw", feature_perturbation="tree_path_dependent")
        self.referencia = float(np.asarray(self.explainer.expected_value)[self.clase]) * 100

    def explicar(self, entrada, score_sin_redondear):
        values = np.asarray(self.explainer.shap_values(
            np.asarray([entrada], dtype=float), check_additivity=True))
        if values.shape != (1, len(self.nombres), 2):
            raise ValueError("Forma de SHAP incompatible con el clasificador binario")
        aportes = values[0, :, self.clase] * 100
        reconstruido = self.referencia + float(aportes.sum())
        if not np.all(np.isfinite(aportes)) or not math.isclose(
                reconstruido, score_sin_redondear, abs_tol=1e-5, rel_tol=0):
            raise ValueError("SHAP no reconstruye el score de reprobacion")
        pesos = pesos_relativos(aportes)
        factores = []
        for nombre, valor, aporte, peso in zip(self.nombres, entrada, aportes, pesos):
            titulo, categoria, unidad = VARIABLES[nombre]
            aporte = round(float(aporte), 6)
            direccion = "AUMENTA" if aporte > 0 else "REDUCE" if aporte < 0 else "NEUTRO"
            observado = f"{float(valor):g} {unidad}"
            efecto = {"AUMENTA": "eleva", "REDUCE": "reduce", "NEUTRO": "no modifica"}[direccion]
            descripcion = (f"{titulo}: {observado}. Este valor {efecto} la estimación "
                           f"en {abs(aporte):.2f} puntos porcentuales respecto a la referencia interna del modelo.")
            factores.append({
                "variable": nombre, "factor": titulo, "nombre": titulo,
                "categoria": categoria, "valor_observado": observado,
                "valor_numerico": valor, "detalle": observado, "valor_actual": observado,
                "descripcion": descripcion, "direccion": direccion,
                "contribucion_pp": aporte, "impacto": peso,
                "metodo": "TREE_SHAP", "version_explicacion": "tree-shap-v1",
            })
        # Muestra primero los incrementos mas importantes, luego proteccion y neutros.
        factores.sort(key=lambda f: (0 if f["direccion"] == "AUMENTA" else 1,
                                     -abs(f["contribucion_pp"])))
        metadata = {
            "metodo": "TREE_SHAP", "version": "tree-shap-v1", "objetivo": "REPROBACION",
            "escala": "PUNTOS_PORCENTUALES", "referencia_pct": round(self.referencia, 6),
            "score_reconstruido_pct": round(reconstruido, 6),
            "referencia_descripcion": "Referencia interna de los árboles entrenados con datos sintéticos; no es la tasa real de reprobación.",
            "interpretacion": "Aportes individuales relativos al modelo, no causas ni porcentajes de culpa. El peso relativo usa magnitudes absolutas.",
        }
        return factores, metadata


def resumen_docente(score, nivel, factores, features, estado):
    aumentan = [f for f in factores if f["direccion"] == "AUMENTA" and f["contribucion_pp"] >= 0.005]
    reducen = sorted((f for f in factores if f["direccion"] == "REDUCE"
                      and f["contribucion_pp"] <= -0.005), key=lambda f: f["contribucion_pp"])
    texto = [f"Estimación de reprobación: {score:.2f}% (nivel {nivel})."]

    def detalle(f):
        return f"{f['factor'].lower()} ({f['valor_observado']}, {f['contribucion_pp']:+.2f} puntos porcentuales)"

    if aumentan:
        texto.append("Las principales contribuciones que elevan la estimación son: "
                     + "; ".join(detalle(f) for f in aumentan[:2]) + ".")
    else:
        texto.append("No hay incrementos individuales relevantes respecto a la referencia interna del modelo.")
    if reducen:
        texto.append("La estimación se reduce principalmente por " + detalle(reducen[0]) + ".")

    acciones = []
    if estado == "PAUSADA":
        texto.append("La inscripción está PAUSADA: requiere contacto para acordar su continuidad. Este estado no interviene en el cálculo SHAP.")
        acciones.append("Contactar al estudiante para acordar fecha de retorno y seguimiento de la pausa.")
    if features["porcentaje_asistencia"] < 65 or features["promedio_calificaciones"] < 51:
        texto.append("Además, hay un umbral institucional crítico actual (asistencia <65% o promedio <51); requiere revisión docente aunque el score sea bajo.")
    if features["porcentaje_asistencia"] < 75 or features["faltas_injustificadas"] > 0:
        acciones.append("Revisar las ausencias con el estudiante y acordar un plan de asistencia.")
    if features["promedio_calificaciones"] < 70:
        acciones.append("Revisar las dificultades en la evaluación práctica y acordar refuerzo con el docente.")
    elif features["tendencia_notas"] < 0:
        acciones.append("Comparar las últimas evaluaciones y revisar qué habilidades requieren refuerzo.")
    if features["observaciones_negativas"] > 0 and len(acciones) < 3:
        acciones.append("Revisar las observaciones pedagógicas con el docente antes de decidir una intervención.")
    if not acciones:
        acciones.append("Mantener el seguimiento semanal de asistencia y evaluaciones.")
    texto.append("Modelo experimental entrenado con datos sintéticos: explica su estimación, no demuestra causas ni reemplaza el criterio docente.")
    return " ".join(texto), acciones
