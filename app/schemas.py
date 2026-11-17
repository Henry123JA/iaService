from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

Porcentaje = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False, strict=True)]
Conteo = Annotated[int, Field(ge=0, strict=True)]
Estado = Literal["ACTIVA", "PAUSADA", "CANCELADA"]


class Features(BaseModel):
    model_config = ConfigDict(extra="ignore")
    porcentaje_asistencia: Porcentaje
    faltas_injustificadas: Conteo
    atrasos: Conteo
    promedio_calificaciones: Porcentaje | None
    tendencia_notas: Annotated[float, Field(allow_inf_nan=False, strict=True)]
    observaciones_negativas: Conteo = Field(
        validation_alias=AliasChoices("observaciones_negativas", "total_obs_alerta"))
    estado_inscripcion: Estado | None = None
    total_sesiones: Conteo | None = None
    evaluaciones_rendidas: Conteo | None = None


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    inscripcion_id: Annotated[int, Field(gt=0, strict=True)]
    alumno_codigo: str | None = None
    estado_inscripcion: Estado | None = None
    features: Features

    @model_validator(mode="after")
    def estado_consistente(self):
        interno = self.features.estado_inscripcion
        if interno and self.estado_inscripcion and interno != self.estado_inscripcion:
            raise ValueError("Estados de inscripcion contradictorios")
        estado = interno or self.estado_inscripcion
        sesiones = self.features.total_sesiones
        evaluaciones = self.features.evaluaciones_rendidas
        excluida = (estado == "CANCELADA" or (sesiones is not None and sesiones < 3)
                    or (evaluaciones is not None and evaluaciones < 1))
        if not excluida and self.features.promedio_calificaciones is None:
            raise ValueError("Una prediccion calculable requiere promedio_calificaciones")
        return self


class BatchRequest(BaseModel):
    alumnos: Annotated[list[PredictRequest], Field(min_length=1, max_length=1000)]

    @model_validator(mode="before")
    @classmethod
    def adaptar_laravel(cls, value):
        if isinstance(value, list):
            return {"alumnos": value}
        if isinstance(value, dict):
            for key in ("dataset", "data", "alumnos"):
                if isinstance(value.get(key), list):
                    if "total_registros" in value and value["total_registros"] != len(value[key]):
                        raise ValueError("total_registros no coincide con el listado")
                    return {"alumnos": value[key]}
        return value

    @model_validator(mode="after")
    def sin_duplicados(self):
        ids = [a.inscripcion_id for a in self.alumnos]
        if len(ids) != len(set(ids)):
            raise ValueError("Inscripciones duplicadas")
        return self


class FactorExplicativo(BaseModel):
    variable: str
    factor: str
    nombre: str
    categoria: Literal["ASISTENCIA", "ACADEMICO", "EVOLUCION", "DISCIPLINA"]
    valor_observado: str
    valor_numerico: float
    detalle: str
    valor_actual: str
    descripcion: str
    direccion: Literal["AUMENTA", "REDUCE", "NEUTRO"]
    contribucion_pp: float
    impacto: Annotated[float, Field(ge=0, le=100)]
    metodo: Literal["TREE_SHAP"]
    version_explicacion: str


class ExplicacionModelo(BaseModel):
    metodo: Literal["TREE_SHAP"]
    version: str
    objetivo: Literal["REPROBACION"]
    escala: Literal["PUNTOS_PORCENTUALES"]
    referencia_pct: float
    score_reconstruido_pct: float
    referencia_descripcion: str
    interpretacion: str


class PredictResponse(BaseModel):
    inscripcion_id: int
    version_modelo: str
    experimental: bool
    entrenado_con: str
    estado_inscripcion: Estado | None = None
    estado_prediccion: Literal["CALCULADA", "DATOS_INSUFICIENTES", "NO_APLICA_RETIRO_CONFIRMADO"]
    score_riesgo: float | None = None
    nivel_riesgo: Literal["BAJO", "MEDIO", "ALTO"] | None = None
    estimacion_reprobo_pct: float | None = None
    estimacion_abandono_pct: float | None = None
    requiere_seguimiento_por_pausa: bool = False
    aviso: str | None = None
    factores_riesgo: list[FactorExplicativo] = Field(default_factory=list)
    explicacion_modelo: ExplicacionModelo | None = None
    acciones_sugeridas: list[str] = Field(default_factory=list)
    resumen_explicativo: str


class BatchResponse(BaseModel):
    total_registros: int
    predicciones_calculadas: int
    resultados: list[PredictResponse]
