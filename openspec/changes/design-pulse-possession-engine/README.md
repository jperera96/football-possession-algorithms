# PULSE: guía para revisores

**Estado: propuesta. No está aprobada.** Se aprueba solo cuando una persona la fusiona en `main`
mediante una PR de especificación. Este PR no implementa nada.

## Qué leer, según el tiempo

| Tiempo | Lectura |
|---|---|
| 10 min | Esta guía y `supporting/roadmap.md` |
| 30 min | Además, `proposal.md` y la tabla de cumplimiento de `supporting/current-architecture.md` |
| Revisión completa | Además, `design.md`, `specs/`, `tasks.md` y el resto de `supporting/` |

## Decisiones que debe tomar el equipo antes del merge

El schema exige resolver antes del merge lo que cambie specs, enfoque o tareas.

| ID | Decisión | Recomendación |
|---|---|---|
| D1 | Qué hacer con los tests golden y las reglas clase B. `RULES.md` prohíbe etiquetas manuales del partido "in any amount and for any purpose", también para validar | Retirar los tests del árbol, conservar el historial y preguntar a la organización por las reglas clase B |
| D2 | Canal y texto de la consulta a la organización. `RULES.md` indica abrir un issue, que es público | Lo decide el equipo; enviarla antes del 6 de noviembre |
| D3 | Corregir las afirmaciones de `APPROACH.md` y explicar el historial en el documento técnico | Sí |
| D4 | Disponibilidad real y rol del tercer integrante | Confirmar horas; sin dedicación completa, aplicar la lista de recortes |
| D5 | Aprobar el contrato completo, o solo P0 primero | Completo si se revisa antes del 7 de noviembre; si no, PR reducida |

## Respuestas rápidas

| Pregunta | Dónde |
|---|---|
| 1. Qué existe hoy | `supporting/current-architecture.md` |
| 2. Qué problemas hay que resolver | `proposal.md`, *Why* |
| 3. Qué queremos construir | `design.md`, *Target Architecture* |
| 4. Por qué esta arquitectura | `design.md`, *Decisions and Alternatives* |
| 5. Qué módulos se conservan | `supporting/current-architecture.md`: KEEP |
| 6. Qué se refactoriza | Misma matriz: REFACTOR |
| 7. Qué módulos nuevos hacen falta | `design.md`: `validation/`, `config/`, `make_submission.py` y los contratos |
| 8. Qué algoritmos se evaluarán | FSM actual, FSM refactorizada y Viterbi; HSMM solo con una necesidad medida |
| 9. Qué datos podemos usar | `supporting/external-validation-protocol.md` |
| 10. Cómo se miden las mejoras | Mismo documento: regla de selección |
| 11. Cómo se garantiza la reproducibilidad | `specs/submission-reproducibility/spec.md` |
| 12. Cómo se evita el sobreajuste | `design.md`, *Overfitting Risk* |
| 13. Qué tecnologías se usan | `supporting/technology-review.md` |
| 14. Qué tareas existen | `tasks.md` |
| 15. Qué dependencias tienen | `tasks.md`: *Depends on* |
| 16. Qué va primero | P0, hasta la puerta G1 |
| 17. Qué queda fuera de la fase 1 | `supporting/roadmap.md`: P3 y lista de recortes |
| 18. Qué hará cada integrante | `supporting/roadmap.md` |
| 19. Cómo se verifica cada requisito | `tasks.md`: *Verification* |
| 20. Qué falta por aprobar | Todo: este cambio entero |

## Avisos

- La posición sobre cumplimiento describe hechos del repositorio y el texto de las normas. No juzga intenciones, y los casos dudosos los decide la organización.
- No se promete ninguna puntuación. Quitar lógica específica del partido puede bajar el rendimiento en el partido real, y no hay forma legítima de estimarlo.
- Las referencias a código corresponden a `origin/main` en `54998ee`. Esta rama parte de `raulrn/openspec-init` y no contiene esos 20 commits.
