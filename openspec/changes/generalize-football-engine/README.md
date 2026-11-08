# Generalizar el motor: guía para revisores

**Estado: propuesta. No está aprobada.** Se aprueba solo cuando una persona la fusiona en `main`.
Sustituye al borrador PULSE (`design-pulse-possession-engine`), que nunca se aprobó.

## La idea en cuatro frases

1. El 0.9375 se midió en la misma ventana de 5 minutos con la que se desarrolló el motor. Por eso no dice cómo se comporta el resto del partido, y no hay forma legítima de medir el partido completo antes de entregar.
2. Para que la calidad aguante hay que **generalizar**: quitar lo específico del partido, que el motor funcione en otros partidos y medirlo allí.
3. Además, un script que ejecutáis vosotros revisa el partido completo sin etiquetas. Compara cómo se comporta el motor dentro y fuera de la ventana pública, y saca solo agregados.
4. Las reglas se quedan o se van según la evidencia externa, no según frames concretos del partido.

## Qué cambia respecto a la propuesta anterior

- Se centra en el algoritmo actual. No hay arquitectura nueva, ni Viterbi, ni depurador avanzado.
- Tiene 5 capacidades en lugar de 10, y 25 tareas en lugar de 34.
- Hay una tarea dedicada a mejorar el motor (2.9) con fallos vistos en partidos externos.
- Incluye un análisis de `experiments/` en `supporting/experiments-analysis.md`.
- Asume que la cifra pública puede bajar. Eso no es una regresión, sino que desaparece el optimismo de medir con los mismos datos con los que se desarrolló.

## Decisiones del equipo antes del merge

| ID | Decisión | Recomendación |
|---|---|---|
| D1 | Tests golden y reglas nacidas de casos del vídeo | Retirar los tests del árbol, conservar el historial, desactivar por defecto las reglas clase B sin evidencia y preguntar a la organización |
| D2 | Canal de la consulta a la organización (un issue es público) | Decidirlo y enviarla el 9 de noviembre |
| D3 | Corregir `APPROACH.md` y explicar el historial en el documento técnico | Sí |
| D4 | Horas reales de cada persona y rol del tercer integrante | Confirmarlo hoy |
| D5 | Usar los partidos de muestra de Metrica, que no declaran licencia | Sí, citándolos; confirmar que el equipo está de acuerdo |

## Qué leer

- **10 minutos:** esta guía, `supporting/experiments-analysis.md` y `supporting/roadmap.md`.
- **Revisión completa:** además, `proposal.md`, `design.md`, `specs/`, `tasks.md` y el resto de `supporting/`.
