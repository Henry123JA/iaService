for (const [servicio, url] of [
  ['Laravel', 'http://host.docker.internal:8000/api/ml/dataset-alumnos'],
  ['FastAPI', 'http://host.docker.internal:8001/health'],
]) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(10000), headers: { Accept: 'application/json' } });
    const data = await response.json();
    console.log(JSON.stringify({ servicio, http: response.status,
      total_registros: data.total_registros, version_modelo: data.version_modelo }));
    if (!response.ok) process.exitCode = 1;
  } catch (error) {
    console.log(JSON.stringify({ servicio, error: error.message }));
    process.exitCode = 1;
  }
}
