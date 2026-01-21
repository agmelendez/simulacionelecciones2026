# Monte Carlo – Elecciones Presidenciales Costa Rica 2026 (actualizado con CIEP 21-ene-2026)

## Qué hace
- Integra un pool de encuestas (tabla agregada).
- Estima distribución de:
  - **U** = indecisos + no responde (sobre total),
  - **B** = nulo/blanco (sobre total; si falta, se imputa/estima),
  - **shares en decididos** (candidatos vs “RESTO”) en espacio logit.
- Simula asignación de indecisos con mezcla de escenarios: proporcional, momentum, dispersión, abstención.
- Reporta probabilidad de superar **40% de votos válidos** en 1ª ronda.

## Cómo correr
```bash
pip install numpy pandas matplotlib
python cr_presidential_mc_2026_updated.py
```

## Ajustes recomendados
1) Reemplazá `POLLS` por tu base completa (ideal: incluir todas las mediciones disponibles).
2) Calibrá `INDECISION_MIX` con backtesting (p. ej. 2010–2022).
3) Si tenés info de **“segunda preferencia”** o matrices de transición (panel), incorporá un escenario adicional.

## Salidas
- `resumen_mc_2026.json`
- `simulaciones_mc_2026.csv` (opcional; puede ser pesado)
- `figura_mc_2026.png`
