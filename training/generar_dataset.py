"""Genera ejemplos SINTETICOS alineados con las reglas de negocio de Scala Musical."""
import argparse
import csv
import random
from pathlib import Path

FEATURES = [
    "porcentaje_asistencia", "faltas_injustificadas", "atrasos",
    "promedio_calificaciones", "tendencia_notas", "observaciones_negativas",
]
TARGETS = ["reprobo", "abandono"]


def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def generar(cantidad, semilla):
    rng = random.Random(semilla)
    for indice in range(cantidad):
        semanas_periodo = rng.choice([10, 11, 12])
        # Simula fotografias desde alerta temprana (semana 2-3) hasta mitad/avanzado del curso.
        if rng.random() < 0.55:
            semana = rng.choice([2, 3, 4])
            sesiones = rng.randint(3, min(7, semana * 2))
        else:
            semana = rng.randint(5, semanas_periodo - 1)
            sesiones = rng.randint(max(5, semana), min(16, semana * 2))
        evaluaciones = max(1, min(4, semana // 2))

        # Perfil latente de dificultad academica y compromiso del estudiante (0 = optimo, 1 = critico)
        dificultad = rng.betavariate(1.8, 2.4)

        # Conteos de faltas, faltas injustificadas y atrasos compatibles con las sesiones transcurridas
        prob_falta = limitar(0.02 + 0.48 * (dificultad ** 1.25), 0.01, 0.75)
        faltas = sum(rng.random() < prob_falta for _ in range(sesiones))
        injustificadas = sum(rng.random() < (0.45 + 0.40 * dificultad) for _ in range(faltas))
        sesiones_asistidas = sesiones - faltas
        prob_atraso = limitar(0.03 + 0.28 * dificultad, 0.02, 0.50)
        atrasos = sum(rng.random() < prob_atraso for _ in range(sesiones_asistidas))

        # Regla institucional de Laravel (sw-scala): cada atraso pondera al 80% (descuenta 0.2 de sesion)
        sesiones_efectivas = max(0.0, sesiones_asistidas - 0.2 * atrasos)
        asistencia = limitar(100.0 * sesiones_efectivas / sesiones, 0.0, 100.0)

        # Desempeno academico parcial y evolucion entre practicas
        promedio = limitar(rng.gauss(91.0 - 46.0 * dificultad, 10.5), 10.0, 100.0)
        tendencia = limitar(rng.gauss(5.0 - 15.0 * dificultad, 4.8), -30.0, 30.0)
        prob_obs = limitar(0.01 + 0.26 * (dificultad ** 1.3), 0.01, 0.45)
        observaciones = sum(rng.random() < prob_obs for _ in range(sesiones))

        # Probabilidad simulada de abandono posterior a la fotografia de seguimiento
        deficit_asistencia = max(0.0, 80.0 - asistencia)
        deficit_nota = max(0.0, 65.0 - promedio)
        caida_tendencia = max(0.0, -tendencia)
        p_abandono = limitar(
            0.015
            + deficit_asistencia * 0.0065
            + injustificadas * 0.045
            + atrasos * 0.015
            + observaciones * 0.040
            + deficit_nota * 0.0040
            + caida_tendencia * 0.0060,
            0.01, 0.85
        )
        abandono = int(rng.random() < p_abandono)

        # Evolucion hacia la nota final: integra las 6 variables de forma monotonica coherente
        penalizacion_asistencia = max(0.0, 78.0 - asistencia) * 0.22 + max(0.0, 65.0 - asistencia) * 0.18
        penalizacion_conducta = injustificadas * 2.4 + atrasos * 0.9 + observaciones * 2.8
        impulso_tendencia = 0.85 * tendencia
        nota_final = round(limitar(
            promedio
            + impulso_tendencia
            - penalizacion_asistencia
            - penalizacion_conducta
            - abandono * 16.0
            + rng.gauss(0.0, 8.0),
            0.0, 100.0), 2)

        yield {
            "registro_id": f"SINT-{indice + 1:06d}",
            "origen": "SINTETICO",
            "semana_seguimiento": semana,
            "semanas_periodo": semanas_periodo,
            "sesiones_transcurridas": sesiones,
            "evaluaciones_realizadas": evaluaciones,
            "porcentaje_asistencia": round(asistencia, 2),
            "faltas_injustificadas": injustificadas,
            "atrasos": atrasos,
            "promedio_calificaciones": round(promedio, 2),
            "tendencia_notas": round(tendencia, 2),
            "observaciones_negativas": observaciones,
            "nota_final_simulada": nota_final,
            "estado_final_simulado": "CANCELADA" if abandono else "ACTIVA",
            "reprobo": int(nota_final < 51),
            "abandono": abandono,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cantidad", type=int, default=3000)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--salida", type=Path, default=Path("data/dataset_sintetico.csv"))
    args = parser.parse_args()
    if args.cantidad < 20:
        parser.error("Usa al menos 20 ejemplos para la demostracion.")
    rows = list(generar(args.cantidad, args.semilla))
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generados {len(rows)} ejemplos SINTETICOS en {args.salida}")
    for target in TARGETS:
        print(f"{target}: {sum(row[target] for row in rows) / len(rows):.1%}")


if __name__ == "__main__":
    main()
