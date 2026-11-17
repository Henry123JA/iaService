<?php

// Verificacion de solo lectura. No carga ni imprime credenciales ni alumnos.
$backend = dirname(__DIR__, 2) . '/sw-scala';
require $backend . '/vendor/autoload.php';
$app = require $backend . '/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

use Illuminate\Support\Facades\DB;
use App\Models\AlertaSeguimiento;

if (DB::connection()->getDriverName() !== 'pgsql') {
    throw new RuntimeException('La conexion activa no es PostgreSQL.');
}

$expected = json_decode(file_get_contents(dirname(__DIR__) . '/data/predicciones_fastapi.json'), true, 512, JSON_THROW_ON_ERROR);
$predictions = array_values(array_filter($expected['resultados'],
    fn ($r) => $r['estado_prediccion'] === 'CALCULADA'));
$expectedOrigin = $argv[1] ?? 'ML_API';
$checkXai = ($argv[2] ?? '') === '--xai';
if (! in_array($expectedOrigin, ['ML_API', 'N8N_AUTO'], true)) {
    throw new InvalidArgumentException('Origen esperado invalido');
}

$report = DB::transaction(function () use ($predictions, $expectedOrigin, $checkXai) {
    DB::statement('SET TRANSACTION READ ONLY');
    $rows = [];
    $errors = [];
    foreach ($predictions as $prediction) {
        $alerts = AlertaSeguimiento::with('versionModelo')
            ->where('inscripcion_id', $prediction['inscripcion_id'])
            ->orderByDesc('id')->get();
        $alert = $alerts->first();
        if (! $alert) {
            $errors[] = 'Falta alerta para inscripcion ' . $prediction['inscripcion_id'];
            continue;
        }
        $metadata = $alert->metricas_base['prediccion_ml'] ?? [];
        $valid = $alert->origen === $expectedOrigin
            && $alert->versionModelo?->version === $prediction['version_modelo']
            && abs($alert->score_riesgo - $prediction['score_riesgo']) < 0.001
            && $alert->nivel_riesgo === $prediction['nivel_riesgo']
            && ($metadata['version_modelo'] ?? null) === $prediction['version_modelo']
            && ($metadata['experimental'] ?? null) === true
            && ($metadata['entrenado_con'] ?? null) === 'SINTETICO';
        $explanation = $metadata['explicacion_modelo'] ?? [];
        $factors = $alert->factores_riesgo ?? [];
        $contributions = array_sum(array_column($factors, 'contribucion_pp'));
        if ($checkXai) {
            $valid = $valid && count($factors) === 6
                && ($explanation['metodo'] ?? null) === 'TREE_SHAP'
                && isset($explanation['referencia_pct'])
                && abs($explanation['referencia_pct'] + $contributions - $alert->score_riesgo) < 0.0051
                && count($metadata['acciones_sugeridas'] ?? []) > 0
                && str_contains($alert->resumen_explicativo ?? '', 'sintéticos');
        }
        if (! $valid) {
            $errors[] = 'Diferencia con FastAPI en inscripcion ' . $prediction['inscripcion_id'];
        }
        $rows[] = [
            'alerta_id' => $alert->id,
            'inscripcion_id' => $alert->inscripcion_id,
            'origen' => $alert->origen,
            'version_modelo' => $alert->versionModelo?->version,
            'score_riesgo' => $alert->score_riesgo,
            'nivel_riesgo' => $alert->nivel_riesgo,
            'experimental' => $metadata['experimental'] ?? null,
            'entrenado_con' => $metadata['entrenado_con'] ?? null,
            'fecha_analisis' => $alert->fecha_analisis?->toIso8601String(),
            'alertas_existentes_para_inscripcion' => $alerts->count(),
            'verificada' => $valid,
            'metodo_explicacion' => $explanation['metodo'] ?? null,
            'cantidad_factores' => count($factors),
            'referencia_pct' => $explanation['referencia_pct'] ?? null,
            'suma_aportes_pp' => $contributions,
            'resumen_explicativo' => $checkXai ? $alert->resumen_explicativo : null,
        ];
    }
    return [
        'conexion' => 'pgsql',
        'solo_lectura' => true,
        'origen_esperado' => $expectedOrigin,
        'esperadas' => count($predictions),
        'encontradas' => count($rows),
        'verificadas' => count(array_filter($rows, fn ($r) => $r['verificada'])),
        'alertas' => $rows,
        'errores' => $errors,
    ];
});

echo json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR), PHP_EOL;
exit(count($report['errores']) === 0 && $report['verificadas'] === 7 ? 0 : 1);
