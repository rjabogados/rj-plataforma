from .rrhh_core import Negocio, Area, Cargo, Colaborador, Asistencia
from .solicitudes import Ticket, SolicitudVacaciones
from .comunicacion import Comunicado, MensajeInterno, EventoCalendario, Notificacion
from .reclutamiento import CandidatoReclutamiento

from .reclutamiento import CandidatoReclutamiento
from .historial import HistorialEstado, RegistroContacto

from .documentos import (
    DocumentoPersonal, CategoriaDocumento, PlantillaDocumento, 
    DocumentoGenerado, FirmaDigital
)

from .lms import (
    CategoriaModuloLMS,
    RutaInduccion,
    RutaInduccionModulo,
    CursoInduccion, MaterialFormativo, EvaluacionCurso, PreguntaEvaluacion, 
    MatriculaCurso, RespuestaColaborador, Encuesta, Pregunta, OpcionPregunta,
    RespuestaEncuesta, CandidatoOnboarding, CursoInduccion, MaterialFormativo, 
    EvaluacionCurso, PreguntaEvaluacion, MatriculaCurso, RespuestaColaborador,
    OpcionRespuesta
)

