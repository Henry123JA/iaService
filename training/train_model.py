"""Entrena modelos de demostracion con Validacion Cruzada Estratificada y reporte de metricas."""
import argparse
import csv
import json
import shutil
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split

from generar_dataset import FEATURES, TARGETS


CANDIDATOS = [
    {"n_estimators": 200, "max_depth": 8, "min_samples_leaf": 8, "max_features": "sqrt", "class_weight": "balanced"},
    {"n_estimators": 250, "max_depth": 9, "min_samples_leaf": 6, "max_features": "sqrt", "class_weight": "balanced"},
    {"n_estimators": 250, "max_depth": 10, "min_samples_leaf": 5, "max_features": "sqrt", "class_weight": "balanced_subsample"},
]


def evaluar_cv(x_train, y_train, params):
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    x_arr = np.asarray(x_train, dtype=float)
    y_arr = np.asarray(y_train, dtype=int)
    f1_list, rec_list, auc_list = [], [], []
    for train_idx, val_idx in skf.split(x_arr, y_arr):
        clf = RandomForestClassifier(**params, random_state=42, n_jobs=1)
        clf.fit(x_arr[train_idx], y_arr[train_idx])
        preds = clf.predict(x_arr[val_idx])
        probs = clf.predict_proba(x_arr[val_idx])[:, 1]
        f1_list.append(f1_score(y_arr[val_idx], preds, zero_division=0))
        rec_list.append(recall_score(y_arr[val_idx], preds, zero_division=0))
        auc_list.append(roc_auc_score(y_arr[val_idx], probs))
    return {
        "cv_f1_mean": round(float(np.mean(f1_list)), 4),
        "cv_f1_std": round(float(np.std(f1_list)), 4),
        "cv_recall_mean": round(float(np.mean(rec_list)), 4),
        "cv_roc_auc_mean": round(float(np.mean(auc_list)), 4),
        "score_seleccion": float(0.5 * np.mean(f1_list) + 0.3 * np.mean(rec_list) + 0.2 * np.mean(auc_list)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/dataset_sintetico.csv"))
    parser.add_argument("--salida", type=Path, default=Path("models/modelos_demo.joblib"))
    parser.add_argument("--metricas", type=Path, default=Path("models/metricas_modelo.json"))
    args = parser.parse_args()

    with args.dataset.open(encoding="utf-8", newline="") as archivo:
        rows = list(csv.DictReader(archivo))

    x = [[float(row[name]) for name in FEATURES] for row in rows]
    modelos = {}
    reporte_metricas = {
        "total_registros_entrenamiento": len(rows),
        "features": FEATURES,
        "version": "demo-sintetica-v2",
        "objetivos": {},
    }

    for target in TARGETS:
        y = [int(row[target]) for row in rows]
        if len(set(y)) != 2 or min(y.count(0), y.count(1)) < 2:
            raise ValueError(f"Faltan ejemplos de ambas clases para {target}.")

        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.25, random_state=42, stratify=y)

        # Seleccion de hiperparametros mediante 5-Fold Stratified Cross-Validation
        mejor_params = None
        mejor_cv = None
        for params in CANDIDATOS:
            res_cv = evaluar_cv(x_train, y_train, params)
            if mejor_cv is None or res_cv["score_seleccion"] > mejor_cv["score_seleccion"]:
                mejor_cv = res_cv
                mejor_params = params

        model = RandomForestClassifier(**mejor_params, random_state=42, n_jobs=1)
        model.fit(x_train, y_train)

        y_pred = model.predict(x_test)
        idx_pos = list(model.classes_).index(1)
        y_prob = model.predict_proba(x_test)[:, idx_pos]
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

        importancias = {
            nombre: round(float(imp) * 100, 2)
            for nombre, imp in zip(FEATURES, model.feature_importances_)
        }

        metricas_target = {
            "tasa_positiva_dataset_pct": round(sum(y) / len(y) * 100, 2),
            "hiperparametros": mejor_params,
            "validacion_cruzada_5fold": {
                "f1_mean": mejor_cv["cv_f1_mean"],
                "f1_std": mejor_cv["cv_f1_std"],
                "recall_mean": mejor_cv["cv_recall_mean"],
                "roc_auc_mean": mejor_cv["cv_roc_auc_mean"],
            },
            "test_holdout_25pct": {
                "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
                "precision_clase_1": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
                "recall_sensibilidad_clase_1": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
                "f1_clase_1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
                "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
                "pr_auc": round(float(average_precision_score(y_test, y_prob)), 4),
                "brier_score": round(float(brier_score_loss(y_test, y_prob)), 4),
                "matriz_confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
            },
            "importancia_global_gini_pct": importancias,
        }
        reporte_metricas["objetivos"][target] = metricas_target

        print(f"\n=== {target.upper()}: Evaluacion con 5-Fold CV + Test Holdout (SOLO datos sinteticos) ===")
        print(f"Mejor configuracion CV: {mejor_params}")
        print(f"5-Fold CV -> F1: {mejor_cv['cv_f1_mean']:.4f} (±{mejor_cv['cv_f1_std']:.4f}) | "
              f"Recall: {mejor_cv['cv_recall_mean']:.4f} | ROC-AUC: {mejor_cv['cv_roc_auc_mean']:.4f}")
        print(f"Test Holdout -> ROC-AUC: {metricas_target['test_holdout_25pct']['roc_auc']:.4f} | "
              f"Recall: {metricas_target['test_holdout_25pct']['recall_sensibilidad_clase_1']:.4f} | "
              f"F1: {metricas_target['test_holdout_25pct']['f1_clase_1']:.4f} | "
              f"Brier: {metricas_target['test_holdout_25pct']['brier_score']:.4f}")
        print(classification_report(y_test, y_pred, zero_division=0))
        modelos[target] = model

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    backup_path = args.salida.parent / "modelos_demo_v2_backup.joblib"
    if args.salida.exists() and not backup_path.exists():
        shutil.copy2(args.salida, backup_path)
        print(f"Respaldo del modelo anterior creado en {backup_path}")

    joblib.dump({
        "features": FEATURES,
        "modelos": modelos,
        "version": "demo-sintetica-v2",
        "origen": "SINTETICO",
        "metricas": reporte_metricas,
    }, args.salida)
    args.metricas.write_text(json.dumps(reporte_metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Modelos guardados en {args.salida}")
    print(f"Reporte de metricas guardado en {args.metricas}")


if __name__ == "__main__":
    main()
