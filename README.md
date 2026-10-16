# PME Conductor E2 — app de estudio (Python + Kivy)

App Android para preparar la oposición de **Conductor/a E2 del Parque Móvil del Estado**.

- 15 temas (5 de la parte común + 10 de la específica) con temario por apartados.
- 1.848 preguntas: 1.497 del banco del curso + 351 de dificultad alta con trampa explicada y truco para recordar.
- Modo aprendizaje (explicación completa de cada fallo) y modo examen.
- Simulacro oficial (100 preguntas, 100 min, −1/3), promoción interna (60/60) y mini simulacro.
- Mis fallos con repetición espaciada (Pendiente / En recuperación / Dominada), plan de recuperación, microrrepasos.
- Mis dudas, favoritas, progreso con índice de preparación y mapa de debilidades, plan de estudio, bases de la oposición.
- Modo claro/oscuro y tamaño de letra.

## Estructura
- `content/raw/` temas (`tema-XXX.md`), tests (`test-XXX.md` / `.psv`) y bases.
- `content/hard/` preguntas de dificultad alta.
- `tools/build_content.py` genera `app/data/content.json` y valida (3 opciones, 1 correcta, sin duplicados).
- `app/` código de la app (`main.py`, `ui.py`, `engine.py`) y `buildozer.spec`.

## APK
Cada `push` a `main` construye el APK con GitHub Actions y lo publica en **Releases**.

## Probar en PC
```
pip install kivy==2.3.1
python tools/build_content.py
cd app && python main.py
```
