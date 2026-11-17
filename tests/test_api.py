import copy
import json
import unittest

from fastapi.testclient import TestClient

from app.main import app, ROOT
from app.predictor import Predictor


EJEMPLO = {"inscripcion_id": 5, "features": {
    "porcentaje_asistencia": 58.3, "faltas_injustificadas": 3, "atrasos": 2,
    "promedio_calificaciones": 62.5, "tendencia_notas": -8.5,
    "observaciones_negativas": 2}}


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_single_matches_shared_predictor(self):
        response = self.client.post("/api/v1/predict", json=EJEMPLO)
        self.assertEqual(response.status_code, 200)
        expected = self.client.app.state.predictor.predict(EJEMPLO)
        self.assertEqual(response.json()["score_riesgo"], expected["score_riesgo"])
        self.assertTrue(response.json()["experimental"])
        self.assertEqual(len(response.json()["factores_riesgo"]), 6)
        self.assertEqual(response.json()["explicacion_modelo"]["metodo"], "TREE_SHAP")
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_batch_formats_and_alias(self):
        item = copy.deepcopy(EJEMPLO)
        item["features"]["total_obs_alerta"] = item["features"].pop("observaciones_negativas")
        for body in ([item], {"dataset": [item], "total_registros": 1},
                     {"alumnos": [item]}, {"data": [item]}):
            with self.subTest(body=type(body)):
                response = self.client.post("/api/v1/predict-batch", json=body)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["predicciones_calculadas"], 1)

    def test_business_exclusions(self):
        for estado, sesiones, expected in (
                ("CANCELADA", 0, "NO_APLICA_RETIRO_CONFIRMADO"),
                ("PAUSADA", 0, "DATOS_INSUFICIENTES"),
                ("PAUSADA", 4, "CALCULADA")):
            item = copy.deepcopy(EJEMPLO)
            item["features"].update(estado_inscripcion=estado,
                                    total_sesiones=sesiones, evaluaciones_rendidas=1)
            response = self.client.post("/api/v1/predict", json=item)
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertEqual(result["estado_prediccion"], expected)
            if expected != "CALCULADA":
                self.assertIsNone(result["score_riesgo"])
                self.assertEqual(result["factores_riesgo"], [])
                self.assertIsNone(result["explicacion_modelo"])
            else:
                self.assertTrue(result["requiere_seguimiento_por_pausa"])

    def test_invalid_features(self):
        for name, value in (("porcentaje_asistencia", 101), ("atrasos", -1),
                            ("atrasos", 1.5), ("atrasos", True),
                            ("promedio_calificaciones", "62.5")):
            item = copy.deepcopy(EJEMPLO)
            item["features"][name] = value
            self.assertEqual(self.client.post("/api/v1/predict", json=item).status_code, 422)
        item = copy.deepcopy(EJEMPLO)
        del item["features"]["tendencia_notas"]
        self.assertEqual(self.client.post("/api/v1/predict", json=item).status_code, 422)

    def test_invalid_batch(self):
        for body in ([], [EJEMPLO, EJEMPLO],
                     {"dataset": [EJEMPLO], "total_registros": 2}):
            self.assertEqual(self.client.post("/api/v1/predict-batch", json=body).status_code, 422)

    def test_conflicting_states(self):
        item = copy.deepcopy(EJEMPLO)
        item["estado_inscripcion"] = "ACTIVA"
        item["features"]["estado_inscripcion"] = "CANCELADA"
        self.assertEqual(self.client.post("/api/v1/predict", json=item).status_code, 422)

    def test_null_grade_only_for_excluded_students(self):
        item = copy.deepcopy(EJEMPLO)
        item["features"]["promedio_calificaciones"] = None
        self.assertEqual(self.client.post("/api/v1/predict", json=item).status_code, 422)
        item["features"].update(total_sesiones=0, evaluaciones_rendidas=0)
        response = self.client.post("/api/v1/predict", json=item)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estado_prediccion"], "DATOS_INSUFICIENTES")

    def test_missing_model_fails_explicitly(self):
        with self.assertRaises(FileNotFoundError):
            Predictor(ROOT / "models" / "inexistente.joblib")

    def test_real_snapshot_when_available(self):
        path = ROOT / "data" / "respuesta_laravel.json"
        if not path.exists():
            self.skipTest("No hay respuesta local de Laravel")
        payload = json.loads(path.read_text(encoding="utf-8"))
        response = self.client.post("/api/v1/predict-batch", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["total_registros"], payload["total_registros"])
        for item, prediction in zip(payload["dataset"], result["resultados"]):
            expected = self.client.app.state.predictor.predict(item)
            self.assertEqual(prediction["score_riesgo"], expected["score_riesgo"])
            self.assertEqual(prediction["estado_prediccion"], expected["estado_prediccion"])

    def test_explanation_reconstructs_prediction_with_signed_contributions(self):
        for changes in ({}, {"porcentaje_asistencia": 100, "faltas_injustificadas": 0,
                              "atrasos": 0, "promedio_calificaciones": 95,
                              "tendencia_notas": 5, "observaciones_negativas": 0},
                        {"porcentaje_asistencia": 20, "promedio_calificaciones": 30}):
            item = copy.deepcopy(EJEMPLO)
            item["features"].update(changes)
            response = self.client.post("/api/v1/predict", json=item)
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            factors = result["factores_riesgo"]
            metadata = result["explicacion_modelo"]
            self.assertAlmostEqual(metadata["referencia_pct"] + sum(
                f["contribucion_pp"] for f in factors), metadata["score_reconstruido_pct"], places=4)
            self.assertLessEqual(abs(metadata["score_reconstruido_pct"] - result["score_riesgo"]), 0.00501)
            self.assertAlmostEqual(sum(f["impacto"] for f in factors), 100, places=2)
            self.assertEqual({f["variable"] for f in factors}, set(EJEMPLO["features"]))
            for factor in factors:
                expected = "AUMENTA" if factor["contribucion_pp"] > 0 else "REDUCE" if factor["contribucion_pp"] < 0 else "NEUTRO"
                self.assertEqual(factor["direccion"], expected)
            self.assertIn("sintéticos", result["resumen_explicativo"])
            self.assertTrue(result["acciones_sugeridas"])
            self.assertNotIn("Seguimiento sugerido:", result["resumen_explicativo"])
            for accion in result["acciones_sugeridas"]:
                self.assertNotIn(accion, result["resumen_explicativo"])

    def test_individual_explanations_differ_for_different_students(self):
        good = copy.deepcopy(EJEMPLO)
        good["features"].update(promedio_calificaciones=95, porcentaje_asistencia=100)
        a = self.client.post("/api/v1/predict", json=EJEMPLO).json()
        b = self.client.post("/api/v1/predict", json=good).json()
        self.assertNotEqual([f["contribucion_pp"] for f in a["factores_riesgo"]],
                            [f["contribucion_pp"] for f in b["factores_riesgo"]])

    def test_paused_state_does_not_change_shap_but_adds_followup(self):
        paused = copy.deepcopy(EJEMPLO)
        paused["features"]["estado_inscripcion"] = "PAUSADA"
        a = self.client.post("/api/v1/predict", json=EJEMPLO).json()
        b = self.client.post("/api/v1/predict", json=paused).json()
        self.assertEqual(a["score_riesgo"], b["score_riesgo"])
        self.assertEqual(a["factores_riesgo"], b["factores_riesgo"])
        self.assertIn("PAUSADA", b["resumen_explicativo"])

    def test_zero_attributions_have_zero_relative_weights(self):
        from app.explanations import pesos_relativos
        self.assertEqual(pesos_relativos([0, 0, 0]), [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
