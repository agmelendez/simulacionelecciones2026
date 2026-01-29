#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMULACIÓN ELECTORAL COSTA RICA 2026 - VERSIÓN 3.0
================================================================================
Actualización: 28 de enero de 2026

Cambios en esta versión (respecto a 22-ene-2026 / v2):
- Se incorpora la última encuesta CIEP-UCR publicada el 28-ene-2026 (campo 20-23, 26 ene).
- Laura Fernández alcanza 43.8%, claramente por encima del umbral del 40%.
- Indecisos reducidos a mínimo histórico de campaña: 25.9%.
- Se añade Juan Carlos Hidalgo (PUSC) como candidato con datos observados (2.5%).
- Claudia Dobles (CAC) muestra crecimiento significativo (de 5% a 8.6%).
- Se reduce σ_sistemático de 1.5 a 1.2 dada la convergencia de encuestas finales.
- Se actualizan títulos, fechas de reporte y semilla.

Nota metodológica:
Este script mantiene el enfoque "rápido y estable" (heurístico) con agregación ponderada
por decay temporal exponencial, estimación de tendencia lineal y ajustes históricos
por tipología de votantes (PEN 2024).

Autor: Agustín Gómez Meléndez (CIOdD-UCR)
Fecha: 28 de enero de 2026
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -----------------------------------------------------------------------------
# Configuración de estilo
# -----------------------------------------------------------------------------
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================
ELECTION_DATE = pd.Timestamp("2026-02-01")
UPDATE_DATE = "2026-01-28"

SEED = 20260128
N_SIMS = 200_000

# Parámetro de incertidumbre sistemática (reducido por convergencia de encuestas)
SIGMA_SISTEMATICO = 1.2  # Reducido de 1.5 en v2

# Patrones de variabilidad electoral (PEN 2024) — recalibrados para encuestas finales
VOTANTES_HABITUALES = 0.31
VOTANTES_OCASIONALES_VOTAN = 0.30
VOTANTES_OCASIONALES_ABSTIENEN = 0.15
ABSTIENEN_SIEMPRE = 0.24

# =============================================================================
# DATOS DE ENCUESTAS (ACTUALIZADOS AL 28 DE ENERO 2026)
# =============================================================================
@dataclass
class Poll:
    poll_id: str
    pollster: str
    publish_date: str
    question_type: str
    moe: float
    values: Dict[str, Optional[float]]
    n_eff: Optional[float] = None


POLLS: List[Poll] = [
    # --- Octubre 2025 ---
    Poll("ciep_ucr_1", "CIEP-UCR", "2025-10-22", "abierta", 2.7,
         {"INDECISOS": 55.0, "LAURA FERNÁNDEZ": 25.0, "ÁLVARO RAMOS": 7.0,
          "ARIEL ROBLES": 3.0, "CLAUDIA DOBLES": 3.0, "OTROS": 4.1, "NULO/BLANCO": 2.5}),
    Poll("opol_1", "OPOL", "2025-10-29", "papeleta", 2.2,
         {"INDECISOS": 38.79, "LAURA FERNÁNDEZ": 31.2, "ÁLVARO RAMOS": 7.41,
          "FABRICIO ALVARADO": 4.84, "ARIEL ROBLES": 3.72, "CLAUDIA DOBLES": 2.92,
          "OTROS": 2.24, "NO RESPONDE": 0.24, "NULO/BLANCO": 1.8}),
    
    # --- Noviembre 2025 ---
    Poll("idespo_una_1", "IDESPO-UNA", "2025-11-06", "abierta", 3.3,
         {"INDECISOS": 52.4, "LAURA FERNÁNDEZ": 28.1, "ÁLVARO RAMOS": 6.2,
          "ARIEL ROBLES": 2.3, "CLAUDIA DOBLES": 2.9, "OTROS": 3.3, "NO RESPONDE": 1.6, "NULO/BLANCO": 2.0}),
    Poll("opol_2", "OPOL", "2025-11-12", "papeleta", 2.16,
         {"INDECISOS": 42.3, "LAURA FERNÁNDEZ": 21.0, "ÁLVARO RAMOS": 10.4,
          "FABRICIO ALVARADO": 6.5, "ARIEL ROBLES": 4.1, "CLAUDIA DOBLES": 2.9, "OTROS": 2.7}),
    Poll("demoscopia_1", "Demoscopia", "2025-11-13", "abierta", 2.83,
         {"INDECISOS": 56.7, "LAURA FERNÁNDEZ": 21.4, "ÁLVARO RAMOS": 9.0,
          "FABRICIO ALVARADO": 3.7, "ARIEL ROBLES": 2.1, "CLAUDIA DOBLES": 3.0, "OTROS": 4.1}),
    Poll("opol_3", "OPOL", "2025-11-25", "papeleta", 2.10,
         {"INDECISOS": 37.37, "LAURA FERNÁNDEZ": 37.85, "ÁLVARO RAMOS": 7.19,
          "FABRICIO ALVARADO": 3.97, "ARIEL ROBLES": 2.35, "CLAUDIA DOBLES": 1.29,
          "OTROS": 2.11, "NO RESPONDE": 0.5, "NULO/BLANCO": 1.03}),
    
    # --- Diciembre 2025 ---
    Poll("ciep_ucr_2", "CIEP-UCR", "2025-12-03", "papeleta", 2.3,
         {"INDECISOS": 34.14, "LAURA FERNÁNDEZ": 37.66, "ÁLVARO RAMOS": 6.91,
          "FABRICIO ALVARADO": 3.66, "ARIEL ROBLES": 3.38, "CLAUDIA DOBLES": 2.80,
          "OTROS": 3.93, "NULO/BLANCO": 0.92}),
    Poll("idespo_una_2", "IDESPO-UNA", "2025-12-08", "panel", 3.3,
         {"INDECISOS": 45.0, "LAURA FERNÁNDEZ": 30.0, "ÁLVARO RAMOS": 8.0,
          "FABRICIO ALVARADO": 1.0, "ARIEL ROBLES": 5.0, "CLAUDIA DOBLES": 4.0,
          "OTROS": 1.5, "NULO/BLANCO": 2.6}),
    Poll("opol_4", "OPOL", "2025-12-10", "abierta", 2.24,
         {"INDECISOS": 43.9, "LAURA FERNÁNDEZ": 32.8, "ÁLVARO RAMOS": 6.6,
          "ARIEL ROBLES": 3.7, "CLAUDIA DOBLES": 5.2, "OTROS": 4.4,
          "NO RESPONDE": 1.6, "NULO/BLANCO": 1.8}),
    Poll("demoscopia_2", "Demoscopia", "2025-12-16", "papeleta", 2.83,
         {"INDECISOS": 41.7, "LAURA FERNÁNDEZ": 27.4, "ÁLVARO RAMOS": 11.3,
          "FABRICIO ALVARADO": 3.6, "ARIEL ROBLES": 4.8, "CLAUDIA DOBLES": 3.1,
          "OTROS": 3.1, "NO RESPONDE": 2.15}),
    Poll("opol_5", "OPOL", "2025-12-23", "papeleta", 2.11,
         {"INDECISOS": 33.77, "LAURA FERNÁNDEZ": 39.45, "ÁLVARO RAMOS": 5.64,
          "FABRICIO ALVARADO": 2.98, "ARIEL ROBLES": 3.13, "CLAUDIA DOBLES": 2.63,
          "OTROS": 2.64, "NULO/BLANCO": 2.91}),
    
    # --- Enero 2026 ---
    Poll("cid_gallup", "CID Gallup", "2026-01-06", "lista", 2.87,
         {"INDECISOS": 14.0, "LAURA FERNÁNDEZ": 41.0, "ÁLVARO RAMOS": 9.0,
          "FABRICIO ALVARADO": 6.0, "ARIEL ROBLES": 4.0, "CLAUDIA DOBLES": 4.0,
          "JOSÉ AGUILAR": 2.0, "OTROS": 4.0, "NO RESPONDE": 11.0}),
    Poll("ciep_ucr_3", "CIEP-UCR", "2026-01-21", "abierta", 3.1,
         {"INDECISOS": 32.0, "LAURA FERNÁNDEZ": 40.0, "ÁLVARO RAMOS": 8.0,
          "CLAUDIA DOBLES": 5.0, "ARIEL ROBLES": 4.0, "FABRICIO ALVARADO": 4.0,
          "JOSÉ AGUILAR": 4.0, "OTROS": 3.0},
         n_eff=1006.0),
    Poll("idespo_una_3", "IDESPO-UNA", "2026-01-22", "abierta", 3.45,
         {"INDECISOS": 35.2, "LAURA FERNÁNDEZ": 39.9, "ÁLVARO RAMOS": 6.0,
          "CLAUDIA DOBLES": 5.2, "ARIEL ROBLES": 3.5,
          "OTROS": 5.9, "NO RESPONDE": 3.6, "NULO/BLANCO": 0.7},
         n_eff=805.0),
    
    # =========================================================================
    # NUEVA: CIEP-UCR (publicación 28-ene-2026; última encuesta antes de elección)
    # Trabajo de campo: 20-23 y 26 de enero de 2026
    # n = 1,501 | MoE = ±2.5 pp (95% confianza)
    # Datos de votantes decididos
    # =========================================================================
    Poll("ciep_ucr_4", "CIEP-UCR", "2026-01-28", "abierta", 2.5,
         {"INDECISOS": 25.9,
          "LAURA FERNÁNDEZ": 43.8,
          "ÁLVARO RAMOS": 9.2,
          "CLAUDIA DOBLES": 8.6,  # Crecimiento significativo (de 5% a 8.6%)
          "JOSÉ AGUILAR": 2.8,
          "JUAN CARLOS HIDALGO": 2.5,  # PUSC - nuevo candidato en el modelo
          "FABRICIO ALVARADO": 1.5,
          "ARIEL ROBLES": 3.8,  # Frente Amplio - CORREGIDO (era 1.8%, dato erróneo)
          "OTROS": 1.9,
          "NULO/BLANCO": 2.0},
         n_eff=1501.0),
]

# Candidatos principales (actualizado con Juan Carlos Hidalgo)
CANDIDATES = [
    "LAURA FERNÁNDEZ",
    "ÁLVARO RAMOS",
    "CLAUDIA DOBLES",
    "ARIEL ROBLES",
    "FABRICIO ALVARADO",
    "JOSÉ AGUILAR",
    "JUAN CARLOS HIDALGO",
    "OTROS",
]

# =============================================================================
# CONSTRUCCIÓN DE DATOS
# =============================================================================
def polls_to_frame(polls: List[Poll]) -> pd.DataFrame:
    """Convierte lista de encuestas a DataFrame."""
    rows = []
    for p in polls:
        row = {
            "poll_id": p.poll_id,
            "pollster": p.pollster,
            "publish_date": pd.Timestamp(p.publish_date),
            "question_type": p.question_type,
            "moe": float(p.moe),
            "n_eff_override": p.n_eff,
        }
        row.update(p.values)
        rows.append(row)

    df = pd.DataFrame(rows)

    # n_eff: usar override si existe, sino aproximar desde MOE
    df["n_eff"] = df["n_eff_override"]
    missing = df["n_eff"].isna()
    df.loc[missing, "n_eff"] = 0.25 * (1.96 * 100.0 / df.loc[missing, "moe"]) ** 2

    # Asegurar columnas
    for c in ["INDECISOS", "NO RESPONDE", "NULO/BLANCO"] + CANDIDATES:
        if c not in df.columns:
            df[c] = np.nan

    df["NO RESPONDE"] = df["NO RESPONDE"].fillna(0.0)
    df["NULO/BLANCO"] = df["NULO/BLANCO"].fillna(df["NULO/BLANCO"].median())

    # Totales
    df["U"] = (df["INDECISOS"].fillna(0.0) + df["NO RESPONDE"]).clip(0, 95)
    df["B"] = df["NULO/BLANCO"].clip(0, 20)
    df["DECIDED_TOTAL"] = (100.0 - df["U"] - df["B"]).clip(1e-6)

    # Shares sobre decididos
    for c in CANDIDATES:
        df[c] = df[c].fillna(0.0)
        df[f"S_{c}"] = (df[c] / df["DECIDED_TOTAL"]).clip(0, 1)

    df["RESTO_TOTAL"] = (df["DECIDED_TOTAL"] - df[CANDIDATES].sum(axis=1)).clip(0)
    df["S_RESTO"] = (df["RESTO_TOTAL"] / df["DECIDED_TOTAL"]).clip(0, 1)

    share_cols = [f"S_{c}" for c in CANDIDATES] + ["S_RESTO"]
    total_shares = df[share_cols].sum(axis=1).replace(0, 1.0)
    for col in share_cols:
        df[col] = df[col] / total_shares

    return df.sort_values("publish_date").reset_index(drop=True)


def compute_weights(df: pd.DataFrame, half_life_days: float = 14.0) -> np.ndarray:
    """Calcula pesos con decay temporal exponencial."""
    days_to_election = (ELECTION_DATE - df["publish_date"]).dt.days.clip(lower=0)
    decay = np.exp(-np.log(2.0) * (days_to_election / half_life_days))

    q = df["question_type"].str.lower()
    factor = np.where(q == "papeleta", 1.0,
             np.where(q == "lista", 1.0,
             np.where(q == "panel", 0.8,
             np.where(q == "abierta", 0.7, 0.6))))

    return (df["n_eff"].astype(float) * decay * factor).values


# =============================================================================
# MODELO DE AGREGACIÓN ROBUSTO
# =============================================================================
def aggregate_polls(df: pd.DataFrame, weights: np.ndarray) -> Dict:
    """Agrega encuestas y estima tendencia lineal ponderada para LF."""
    # Para el modelo principal, usar papeleta, lista y abierta reciente
    mask = df["question_type"].isin(["papeleta", "lista", "abierta"])
    df_main = df[mask].copy()
    w_main = weights[mask]

    if len(df_main) == 0:
        df_main = df.copy()
        w_main = weights

    w_main = w_main.astype(float)
    w_norm = w_main / w_main.sum()

    days = (df_main["publish_date"] - df_main["publish_date"].min()).dt.days.values.astype(float)
    y_lf = df_main["LAURA FERNÁNDEZ"].values.astype(float)

    # Regresión lineal ponderada
    X = np.column_stack([np.ones(len(days)), days])
    W = np.diag(w_main)
    try:
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y_lf)
    except np.linalg.LinAlgError:
        beta = np.array([np.average(y_lf, weights=w_norm), 0.0])

    days_to_election = float((ELECTION_DATE - df_main["publish_date"].min()).days)
    lf_projected = beta[0] + beta[1] * days_to_election

    residuals = y_lf - (beta[0] + beta[1] * days)
    rmse = float(np.sqrt(np.average(residuals**2, weights=w_main)))

    # Estimaciones ponderadas por candidato
    estimates: Dict[str, float] = {}
    for c in CANDIDATES:
        if c in df_main.columns:
            estimates[c] = float(np.average(df_main[c].values.astype(float), weights=w_norm))
        else:
            estimates[c] = 0.0

    estimates["U"] = float(np.average(df_main["U"].values.astype(float), weights=w_norm))
    estimates["B"] = float(np.average(df_main["B"].values.astype(float), weights=w_norm))

    # Calcular tendencia solo en encuestas de enero (más recientes)
    df_jan = df_main[df_main["publish_date"] >= "2026-01-01"]
    if len(df_jan) >= 2:
        days_jan = (df_jan["publish_date"] - df_jan["publish_date"].min()).dt.days.values.astype(float)
        y_jan = df_jan["LAURA FERNÁNDEZ"].values.astype(float)
        if days_jan.max() > 0:
            trend_jan = (y_jan[-1] - y_jan[0]) / (days_jan[-1] - days_jan[0] + 1)
        else:
            trend_jan = beta[1]
    else:
        trend_jan = beta[1]

    return {
        "estimates": estimates,
        "lf_projected": float(np.clip(lf_projected, 25, 55)),
        "lf_trend": float(beta[1]),
        "lf_trend_jan": float(trend_jan),
        "rmse": rmse,
        "n_polls": int(len(df_main)),
        "last_date": df_main["publish_date"].max(),
        "used_question_types": sorted(df_main["question_type"].unique().tolist()),
    }


# =============================================================================
# SIMULACIÓN MONTE CARLO
# =============================================================================
def run_simulation(n_sims: int = N_SIMS, seed: int = SEED) -> Dict:
    """Simulación Monte Carlo con incertidumbre reducida (v3.0)."""
    print("\n" + "="*80)
    print("🎲 SIMULACIÓN MONTE CARLO - COSTA RICA 2026 - VERSIÓN 3.0")
    print(f"   Actualización: {UPDATE_DATE}")
    print("="*80)

    df = polls_to_frame(POLLS)
    weights = compute_weights(df)
    agg = aggregate_polls(df, weights)

    print(f"\nEncuestas disponibles: {len(df)}")
    print(f"Encuestas usadas (principal): {agg['n_polls']} | tipos: {agg['used_question_types']}")
    print(f"Última encuesta (publicación): {agg['last_date'].date()}")
    print(f"Laura Fernández proyectada (tendencia): {agg['lf_projected']:.1f}%")
    print(f"Tendencia diaria estimada (global): {agg['lf_trend']:.3f}% por día")
    print(f"Tendencia diaria (enero): {agg['lf_trend_jan']:.3f}% por día")

    rng = np.random.default_rng(seed)

    print(f"\n⏳ Generando {n_sims:,} simulaciones...")

    estimates = agg["estimates"]
    
    # Usar el valor más reciente como base (CIEP 28-ene: 43.8%)
    last_poll = df.iloc[-1]
    lf_base = float(last_poll["LAURA FERNÁNDEZ"])
    
    # Ajustar ligeramente hacia abajo por tendencia conservadora
    # (proyección = base + trend * días_restantes, pero con prudencia)
    days_remaining = 3  # 28 ene → 1 feb
    lf_base_adjusted = lf_base + agg['lf_trend_jan'] * days_remaining * 0.5  # Factor de prudencia
    lf_base_adjusted = np.clip(lf_base_adjusted, 40, 50)

    # Error estándar total (reducido en v3.0)
    se_lf = float(last_poll["moe"] / 1.96)
    trend_uncertainty = float(agg["rmse"])
    total_se = float(np.sqrt(se_lf**2 + trend_uncertainty**2 + SIGMA_SISTEMATICO**2))

    print(f"  Base LF (última encuesta): {lf_base:.1f}%")
    print(f"  Base LF (ajustada): {lf_base_adjusted:.1f}%")
    print(f"  SE total: {total_se:.2f}%")

    sims = pd.DataFrame(index=np.arange(n_sims))

    # Simulación de Laura Fernández
    lf_sims = rng.normal(lf_base_adjusted, total_se, size=n_sims)

    # Ajuste por tipo de elector (recalibrado para encuestas finales)
    tipo_elector = rng.choice(
        ['habitual', 'ocasional_vota', 'ocasional_abstiene', 'abstiene'],
        size=n_sims,
        p=[VOTANTES_HABITUALES, VOTANTES_OCASIONALES_VOTAN, 
           VOTANTES_OCASIONALES_ABSTIENEN, ABSTIENEN_SIEMPRE]
    )

    ajuste = np.zeros(n_sims)
    m = (tipo_elector == 'ocasional_vota')
    ajuste[m] = rng.normal(0.3, 0.2, size=m.sum())  # Reducido de 0.5
    m = (tipo_elector == 'ocasional_abstiene')
    ajuste[m] = rng.normal(-0.3, 0.2, size=m.sum())  # Reducido de -0.5
    m = (tipo_elector == 'abstiene')
    ajuste[m] = rng.normal(-0.5, 0.3, size=m.sum())  # Reducido de -1.0

    sims["LAURA FERNÁNDEZ"] = (lf_sims + ajuste).clip(30, 55)

    # Indecisos (reducidos significativamente)
    u_base = float(last_poll["INDECISOS"])  # 25.9%
    sims["U"] = rng.normal(u_base, 3.0, size=n_sims).clip(15, 40)

    # Blancos/nulos
    b_base = float(last_poll.get("NULO/BLANCO", 2.0))
    sims["B"] = rng.normal(b_base, 0.8, size=n_sims).clip(0, 6)

    decided = 100.0 - sims["U"] - sims["B"]

    # Otros candidatos (usando valores de última encuesta)
    for c in CANDIDATES:
        if c == "LAURA FERNÁNDEZ":
            continue
        base = float(last_poll.get(c, estimates.get(c, 0.0)))
        if base == 0:
            base = float(estimates.get(c, 1.0))
        # Variabilidad proporcional al nivel de apoyo
        sd = max(1.0, base * 0.2)
        sims[c] = rng.normal(base, sd, size=n_sims).clip(0.2, 20)

    # Resto
    others_cols = [c for c in CANDIDATES if c != "LAURA FERNÁNDEZ"]
    sims["RESTO"] = (decided - sims["LAURA FERNÁNDEZ"] - sims[others_cols].sum(axis=1)).clip(0, 20)

    # Normalizar a 100%
    all_cols = ["LAURA FERNÁNDEZ"] + others_cols + ["RESTO", "U", "B"]
    total = sims[all_cols].sum(axis=1)
    for col in all_cols:
        sims[col] = 100.0 * sims[col] / total

    # Variables de resultado
    sims["LF"] = sims["LAURA FERNÁNDEZ"]
    sims["wins_round1"] = sims["LF"] >= 40.0

    # Determinar top 1 y top 2
    cand_all = CANDIDATES + ["RESTO"]
    vals = sims[cand_all].values
    top1_idx = np.argmax(vals, axis=1)
    top1 = np.array([cand_all[i] for i in top1_idx])
    vals2 = vals.copy()
    vals2[np.arange(n_sims), top1_idx] = -1
    top2_idx = np.argmax(vals2, axis=1)
    top2 = np.array([cand_all[i] for i in top2_idx])

    sims["top1"] = top1
    sims["top2"] = top2

    print("✅ Simulación completada")

    # Resultados
    out = {
        "polls_used": agg["n_polls"],
        "update_date": UPDATE_DATE,
        "aggregation": agg,
        "last_poll_lf": lf_base,
        "summary": {
            "n_sims": int(n_sims),
            "election_date": str(ELECTION_DATE.date()),
            "p_LF_win_round1": float(sims["wins_round1"].mean()),
            "p_LF_top1": float((sims["top1"] == "LAURA FERNÁNDEZ").mean()),
            "LF_mean": float(sims["LF"].mean()),
            "LF_median": float(sims["LF"].median()),
            "LF_p5": float(sims["LF"].quantile(0.05)),
            "LF_p10": float(sims["LF"].quantile(0.10)),
            "LF_p90": float(sims["LF"].quantile(0.90)),
            "LF_p95": float(sims["LF"].quantile(0.95)),
            "U_mean": float(sims["U"].mean()),
            "B_mean": float(sims["B"].mean()),
            "total_se": total_se,
        },
        "cand_summary": sims[cand_all].describe(percentiles=[0.05, 0.10, 0.50, 0.90, 0.95]).T,
        "top2_pairs": (sims.groupby(["top1", "top2"]).size() / n_sims).sort_values(ascending=False),
        "sims": sims,
        "polls_df": df,
    }
    return out


# =============================================================================
# VISUALIZACIÓN
# =============================================================================
def create_plots(out: Dict) -> None:
    sims = out["sims"]
    summ = out["summary"]

    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    fig.suptitle(
        "SIMULACIÓN ELECTORAL COSTA RICA 2026 - PRIMERA RONDA (v3.0)\n"
        f"Actualización: {UPDATE_DATE} | CIEP-UCR: Laura Fernández 43.8%",
        fontsize=14, fontweight="bold"
    )

    # Panel 1: Distribución de Laura Fernández
    ax = axes[0, 0]
    ax.hist(sims["LF"], bins=80, alpha=0.7, edgecolor="black", color="#2E86AB")
    ax.axvline(40, color="red", linestyle="--", linewidth=2.5, label="Umbral 40%")
    ax.axvline(sims["LF"].mean(), color="darkblue", linestyle="-", linewidth=2,
               label=f"Media: {sims['LF'].mean():.1f}%")
    ax.axvline(sims["LF"].median(), color="green", linestyle="-", linewidth=2,
               label=f"Mediana: {sims['LF'].median():.1f}%")
    ax.axvspan(40, sims["LF"].max(), alpha=0.15, color='green')
    ax.set_xlabel("% del voto válido", fontsize=11)
    ax.set_ylabel("Frecuencia", fontsize=11)
    ax.set_title("Laura Fernández - Distribución simulada", fontweight="bold")
    ax.legend(loc='upper left')
    ax.grid(alpha=0.3)

    # Panel 2: CDF
    ax = axes[0, 1]
    sorted_lf = np.sort(sims["LF"].to_numpy())
    cum_prob = np.arange(1, len(sorted_lf) + 1) / len(sorted_lf)
    ax.plot(sorted_lf, cum_prob * 100, linewidth=2, color="#2E86AB")
    ax.axvline(40, color="red", linestyle="--", linewidth=2.5)
    ax.axhline(summ["p_LF_win_round1"] * 100, color="green", linestyle="--",
               label=f"P(≥40%) = {summ['p_LF_win_round1']*100:.1f}%")
    ax.fill_between(sorted_lf, cum_prob * 100, where=(sorted_lf >= 40), alpha=0.3, color="green")
    ax.set_xlabel("% del voto válido", fontsize=11)
    ax.set_ylabel("Probabilidad acumulada (%)", fontsize=11)
    ax.set_title("Función de distribución acumulada", fontweight="bold")
    ax.legend(loc='upper left')
    ax.grid(alpha=0.3)

    # Panel 3: Indecisos
    ax = axes[0, 2]
    ax.hist(sims["U"], bins=60, alpha=0.7, color="#F18F01", edgecolor="black")
    ax.axvline(sims["U"].mean(), color="red", linestyle="--", linewidth=2,
               label=f"Media: {sims['U'].mean():.1f}%")
    ax.axvline(25.9, color="blue", linestyle=":", linewidth=2, label="CIEP 28-ene: 25.9%")
    ax.set_xlabel("% Indecisos + No responde", fontsize=11)
    ax.set_ylabel("Frecuencia", fontsize=11)
    ax.set_title("Distribución de Indecisos (U)", fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 4: Boxplots por candidato
    ax = axes[1, 0]
    top_cands = ["LAURA FERNÁNDEZ", "ÁLVARO RAMOS", "CLAUDIA DOBLES",
                 "ARIEL ROBLES", "JOSÉ AGUILAR", "JUAN CARLOS HIDALGO", "FABRICIO ALVARADO"]
    top_cands = [c for c in top_cands if c in sims.columns]
    data_box = [sims[c].values for c in top_cands]
    labels = [c.split()[0] if c != "JUAN CARLOS HIDALGO" else "HIDALGO" for c in top_cands]
    bp = ax.boxplot(data_box, tick_labels=labels, patch_artist=True)
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#95C623', '#6B4C9A', '#3B1F2B']
    for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.axhline(40, color="red", linestyle="--", linewidth=2, alpha=0.7, label="Umbral 40%")
    ax.set_ylabel("% del voto válido", fontsize=11)
    ax.set_title("Distribución por candidato", fontweight="bold")
    ax.grid(axis='y', alpha=0.3)
    ax.legend(loc='upper right')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Panel 5: Laura vs Segundo lugar
    ax = axes[1, 1]
    if "ÁLVARO RAMOS" in sims.columns:
        segundo = sims["ÁLVARO RAMOS"]
        ax.scatter(sims["LF"], segundo, alpha=0.02, s=1, c="#2E86AB")
        ax.axhline(segundo.mean(), color="red", linestyle="--", alpha=0.7,
                   label=f"Ramos: {segundo.mean():.1f}%")
        ax.axvline(sims["LF"].mean(), color="blue", linestyle="--", alpha=0.7,
                   label=f"Laura: {sims['LF'].mean():.1f}%")
        ax.axvline(40, color="green", linestyle=":", linewidth=2, alpha=0.7, label="Umbral 40%")
        ax.set_xlabel("Laura Fernández (%)", fontsize=11)
        ax.set_ylabel("Álvaro Ramos (%)", fontsize=11)
        ax.set_title("Laura vs Segundo Lugar", fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)

    # Panel 6: Top combinaciones
    ax = axes[1, 2]
    top_pairs = out["top2_pairs"].head(8)
    pairs_labels = [f"{a.split()[0]} vs\n{b.split()[0]}" for a, b in top_pairs.index]
    bars = ax.barh(range(len(top_pairs)), top_pairs.values * 100, color="#2E86AB")
    ax.set_yticks(range(len(top_pairs)))
    ax.set_yticklabels(pairs_labels, fontsize=9)
    ax.set_xlabel("Probabilidad (%)", fontsize=11)
    ax.set_title("Top combinaciones 1º vs 2º", fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    for bar, val in zip(bars, top_pairs.values * 100):
        ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%", va='center', fontsize=8)

    plt.tight_layout()
    plt.savefig("simulacion_cr2026_v3.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Visualización guardada: simulacion_cr2026_v3.png")


# =============================================================================
# REPORTE
# =============================================================================
def print_report(out: Dict) -> None:
    print("\n" + "="*80)
    print("📊 REPORTE FINAL - SIMULACIÓN COSTA RICA 2026 (v3.0)")
    print(f"   Actualización: {UPDATE_DATE}")
    print("="*80)

    summ = out["summary"]
    agg = out["aggregation"]

    print(f"\nSimulaciones: {summ['n_sims']:,}")
    print(f"Fecha elección: {summ['election_date']}")
    print(f"Encuestas usadas: {out['polls_used']} | última: {agg['last_date'].date()}")
    print(f"Última encuesta CIEP-UCR: Laura Fernández = {out['last_poll_lf']:.1f}%")
    
    print("\n" + "─"*80)
    print("🏆 LAURA FERNÁNDEZ - RESULTADO PROYECTADO")
    print("─"*80)
    print(f"\n  ✓ Probabilidad 1ª ronda (≥40%): {summ['p_LF_win_round1']*100:.1f}%")
    print(f"  ✓ Probabilidad 1º lugar:        {summ['p_LF_top1']*100:.1f}%")
    print(f"\n  • Media:     {summ['LF_mean']:.1f}%")
    print(f"  • Mediana:   {summ['LF_median']:.1f}%")
    print(f"  • IC 90%:    [{summ['LF_p5']:.1f}% - {summ['LF_p95']:.1f}%]")
    print(f"  • IC 80%:    [{summ['LF_p10']:.1f}% - {summ['LF_p90']:.1f}%]")
    print(f"\n  • U (indecisos+no resp): {summ['U_mean']:.1f}%")
    print(f"  • B (nulo/blanco):       {summ['B_mean']:.1f}%")
    print(f"  • SE total:              {summ['total_se']:.2f}%")
    
    print("\n" + "─"*80)
    print("📈 COMPARACIÓN CON VERSIONES ANTERIORES")
    print("─"*80)
    print("\n  Versión    | P(≥40%)  | Media LF | IC 80%        | Indecisos")
    print("  " + "-"*60)
    print(f"  v1.0 (dic) | 56.7%    | 45.0%    | [18.2, 71.8]% | 41.9%")
    print(f"  v2.0 (21e) | 59.4%    | 40.8%    | [36.2, 45.3]% | 31.2%")
    print(f"  v3.0 (28e) | {summ['p_LF_win_round1']*100:.1f}%    | {summ['LF_mean']:.1f}%    | [{summ['LF_p10']:.1f}, {summ['LF_p90']:.1f}]% | {summ['U_mean']:.1f}%")
    
    print("\n" + "─"*80)
    print("🎯 INTERPRETACIÓN")
    print("─"*80)
    prob = summ['p_LF_win_round1'] * 100
    if prob >= 85:
        print(f"\n  🟢 VICTORIA EN PRIMERA RONDA: ALTAMENTE PROBABLE ({prob:.0f}%)")
        print("     La candidata está posicionada claramente por encima del umbral")
        print("     constitucional (43.8% vs 40% requerido).")
    elif prob >= 70:
        print(f"\n  🟢 VICTORIA EN PRIMERA RONDA: MUY PROBABLE ({prob:.0f}%)")
    elif prob >= 50:
        print(f"\n  🟡 VICTORIA EN PRIMERA RONDA: PROBABLE ({prob:.0f}%)")
    elif prob >= 30:
        print(f"\n  🟡 ESCENARIO COMPETIDO (P1ª≈{prob:.0f}%)")
    else:
        print(f"\n  🔴 SEGUNDA RONDA MUY PROBABLE (P1ª≈{prob:.0f}%)")
    
    print("\n" + "─"*80)
    print("📋 RESUMEN POR CANDIDATO")
    print("─"*80)
    cand_summ = out["cand_summary"]
    print(f"\n  {'Candidato':<22} {'Media':>8} {'Mediana':>8} {'P10':>8} {'P90':>8}")
    print("  " + "-"*56)
    for c in ["LAURA FERNÁNDEZ", "ÁLVARO RAMOS", "CLAUDIA DOBLES", 
              "ARIEL ROBLES", "JOSÉ AGUILAR", "JUAN CARLOS HIDALGO", "FABRICIO ALVARADO"]:
        if c in cand_summ.index:
            row = cand_summ.loc[c]
            print(f"  {c:<22} {row['mean']:>7.1f}% {row['50%']:>7.1f}% {row['10%']:>7.1f}% {row['90%']:>7.1f}%")
    
    print("\n" + "="*80)


# =============================================================================
# MAIN
# =============================================================================
def main() -> None:
    out = run_simulation(n_sims=N_SIMS, seed=SEED)
    print_report(out)

    print("\n⏳ Guardando resultados...")
    out["sims"].to_csv("simulacion_cr2026_v3.csv", index=False)
    out["cand_summary"].to_csv("resumen_candidatos_v3.csv")
    out["top2_pairs"].head(20).to_csv("top2_pairs_v3.csv")
    out["polls_df"].to_csv("encuestas_input_v3.csv", index=False)

    create_plots(out)

    print("\n✅ SIMULACIÓN COMPLETADA (v3.0)")
    print("\nArchivos generados:")
    print("  • simulacion_cr2026_v3.csv")
    print("  • resumen_candidatos_v3.csv")
    print("  • top2_pairs_v3.csv")
    print("  • encuestas_input_v3.csv")
    print("  • simulacion_cr2026_v3.png")


if __name__ == "__main__":
    main()
