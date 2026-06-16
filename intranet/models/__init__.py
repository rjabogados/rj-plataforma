from .rrhh_core import Negocio, Colaborador, Asistencia
from .solicitudes import Ticket, SolicitudVacaciones
from .comunicacion import Comunicado, MensajeInterno, EventoCalendario
from .reclutamiento import CandidatoReclutamiento

from .reclutamiento import CandidatoReclutamiento
from .historial import HistorialEstado, RegistroContacto

from .documentos import (
    DocumentoPersonal, CategoriaDocumento, PlantillaDocumento, 
    DocumentoGenerado, FirmaDigital
)

from .lms import (
    CursoInduccion, MaterialFormativo, EvaluacionCurso, PreguntaEvaluacion, 
    MatriculaCurso, RespuestaColaborador, Encuesta, Pregunta, 
    RespuestaEncuesta, CandidatoOnboarding
)