import math
import joblib
from reglas_negocio import nivel_riesgo
from app.explanations import ExplicadorRiesgo, resumen_docente


def preparar_features(features):
    features = dict(features)
    if "observaciones_negativas" not in features and "total_obs_alerta" in features:
        features["observaciones_negativas"] = features["total_obs_alerta"]
    return features


def vector(features, nombres):
    valores = []
    for nombre in nombres:
        valor = features[nombre]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(f"{nombre} debe ser numerico")
        if not math.isfinite(valor):
            raise ValueError(f"{nombre} debe ser finito")
        if nombre in ("porcentaje_asistencia", "promedio_calificaciones"):
            if not 0 <= valor <= 100:
                raise ValueError(f"{nombre} fuera de 0..100")
        elif nombre != "tendencia_notas" and (valor < 0 or int(valor) != valor):
            raise ValueError(f"{nombre} debe ser entero no negativo")
        valores.append(valor)
    return valores


class Predictor:
    def __init__(self, path):
        self.bundle = joblib.load(path)
        expected = {"porcentaje_asistencia", "faltas_injustificadas", "atrasos", "promedio_calificaciones", "tendencia_notas", "observaciones_negativas"}
        if set(self.bundle["features"]) != expected or set(self.bundle["modelos"]) != {"reprobo", "abandono"}:
            raise ValueError("Contrato del modelo incompatible")
        for model in self.bundle["modelos"].values():
            if 1 not in model.classes_:
                raise ValueError("Modelo sin clase positiva")
        self.explicador = ExplicadorRiesgo(self.bundle["modelos"]["reprobo"], self.bundle["features"])

    def predict(self, alumno):
        features = preparar_features(alumno["features"])
        estado = features.get("estado_inscripcion", alumno.get("estado_inscripcion"))
        resultado = {"inscripcion_id": alumno["inscripcion_id"],
                     "version_modelo": self.bundle["version"],
                     "experimental": True, "entrenado_con": self.bundle["origen"],
                     "estado_inscripcion": estado}
        resultado["factores_riesgo"] = []
        resultado["resumen_explicativo"] = "Estimacion experimental de reprobacion; sin explicacion individual de factores. No validada con resultados reales."
        if estado == "CANCELADA":
            resultado["resumen_explicativo"] = "Retiro confirmado; no aplica prediccion futura."
            resultado.update(estado_prediccion="NO_APLICA_RETIRO_CONFIRMADO",
                             score_riesgo=None, nivel_riesgo=None)
            return resultado
        if (features.get("total_sesiones", 3) < 3
                or features.get("evaluaciones_rendidas", 1) < 1):
            resultado["resumen_explicativo"] = "Se requieren al menos tres sesiones y una evaluacion."
            resultado.update(estado_prediccion="DATOS_INSUFICIENTES",
                             score_riesgo=None, nivel_riesgo=None)
            return resultado
        entrada = vector(features, self.bundle["features"])
        resultado["estado_prediccion"] = "CALCULADA"
        if estado == "PAUSADA":
            resultado["requiere_seguimiento_por_pausa"] = True
            resultado["aviso"] = "La pausa requiere seguimiento y no forma parte de las seis features del modelo."
        for target, model in self.bundle["modelos"].items():
            indice = list(model.classes_).index(1)
            probabilidad = float(model.predict_proba([entrada])[0][indice]) * 100
            resultado[f"estimacion_{target}_pct"] = round(
                probabilidad, 2)
            if target == "reprobo":
                score_sin_redondear = probabilidad
        # Score principal = estimacion de reprobacion, sin mezclar ni sumar abandono.
        resultado["score_riesgo"] = resultado["estimacion_reprobo_pct"]
        resultado["nivel_riesgo"] = nivel_riesgo(resultado["score_riesgo"])
        resultado["factores_riesgo"], resultado["explicacion_modelo"] = self.explicador.explicar(
            entrada, score_sin_redondear)
        resultado["resumen_explicativo"], resultado["acciones_sugeridas"] = resumen_docente(
            resultado["score_riesgo"], resultado["nivel_riesgo"],
            resultado["factores_riesgo"], features, estado)
        return resultado
