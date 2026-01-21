#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMULACIÓN ELECTORAL COSTA RICA 2026 - VERSIÓN ACTUALIZADA Y ESTABILIZADA
================================================================================
Actualización: 21 de enero de 2026

Metodología revisada para mayor estabilidad:
- Promedio ponderado con decay temporal exponencial
- Modelado de tendencia lineal simplificado
- Distribución de indecisos basada en patrones históricos CR
- Monte Carlo con incertidumbre apropiadamente acotada

Autor: Agustín Gómez (CIOdD-UCR)
Fecha: 21 de enero de 2026
================================================================================
"""

from __future__ import annotations

import re
import math
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Configuración
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================
ELECTION_DATE = pd.Timestamp("2026-02-01")
SEED = 20260121
N_SIMS = 200_000

# Patrones de variabilidad electoral (PEN 2024)
VOTANTES_HABITUALES = 0.31
VOTANTES_OCASIONALES = 0.44
ABSTIENEN_SIEMPRE = 0.01

# =============================================================================
# DATOS DE ENCUESTAS (ACTUALIZADOS AL 21 DE ENERO 2026)
# =============================================================================
@dataclass
class Poll:
    poll_id: str
    pollster: str
    publish_date: str
    question_type: str
    moe: float
    values: Dict[str, Optional[float]]

POLLS: List[Poll] = [
    Poll("ciep_ucr_1", "CIEP-UCR", "2025-10-22", "abierta", 2.7, 
         {"INDECISOS": 55.0, "LAURA FERNÁNDEZ": 25.0, "ÁLVARO RAMOS": 7.0, 
          "ARIEL ROBLES": 3.0, "CLAUDIA DOBLES": 3.0, "OTROS": 4.1, "NULO/BLANCO": 2.5}),
    Poll("idespo_una_1", "IDESPO-UNA", "2025-11-06", "abierta", 3.3, 
         {"INDECISOS": 52.4, "LAURA FERNÁNDEZ": 28.1, "ÁLVARO RAMOS": 6.2, 
          "ARIEL ROBLES": 2.3, "CLAUDIA DOBLES": 2.9, "OTROS": 3.3, "NO RESPONDE": 1.6, "NULO/BLANCO": 2.0}),
    Poll("opol_1", "OPOL", "2025-10-29", "papeleta", 2.2, 
         {"INDECISOS": 38.79, "LAURA FERNÁNDEZ": 31.2, "ÁLVARO RAMOS": 7.41, 
          "FABRICIO ALVARADO": 4.84, "ARIEL ROBLES": 3.72, "CLAUDIA DOBLES": 2.92, 
          "OTROS": 2.24, "NO RESPONDE": 0.24, "NULO/BLANCO": 1.8}),
    Poll("demoscopia_1", "Demoscopia", "2025-11-13", "abierta", 2.83, 
         {"INDECISOS": 56.7, "LAURA FERNÁNDEZ": 21.4, "ÁLVARO RAMOS": 9.0, 
          "FABRICIO ALVARADO": 3.7, "ARIEL ROBLES": 2.1, "CLAUDIA DOBLES": 3.0, "OTROS": 4.1}),
    Poll("opol_2", "OPOL", "2025-11-12", "papeleta", 2.16, 
         {"INDECISOS": 42.3, "LAURA FERNÁNDEZ": 21.0, "ÁLVARO RAMOS": 10.4, 
          "FABRICIO ALVARADO": 6.5, "ARIEL ROBLES": 4.1, "CLAUDIA DOBLES": 2.9, "OTROS": 2.7}),
    Poll("opol_3", "OPOL", "2025-11-25", "papeleta", 2.10, 
         {"INDECISOS": 37.37, "LAURA FERNÁNDEZ": 37.85, "ÁLVARO RAMOS": 7.19, 
          "FABRICIO ALVARADO": 3.97, "ARIEL ROBLES": 2.35, "CLAUDIA DOBLES": 1.29, 
          "OTROS": 2.11, "NO RESPONDE": 0.5, "NULO/BLANCO": 1.03}),
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
    Poll("cid_gallup", "CID Gallup", "2026-01-06", "lista", 2.87, 
         {"INDECISOS": 14.0, "LAURA FERNÁNDEZ": 41.0, "ÁLVARO RAMOS": 9.0, 
          "FABRICIO ALVARADO": 6.0, "ARIEL ROBLES": 4.0, "CLAUDIA DOBLES": 4.0, 
          "JOSÉ AGUILAR": 2.0, "OTROS": 4.0, "NO RESPONDE": 11.0}),
    # NUEVA ENCUESTA CIEP ENERO 2026
    Poll("ciep_ucr_3", "CIEP-UCR", "2026-01-21", "papeleta", 3.1, 
         {"INDECISOS": 32.0, "LAURA FERNÁNDEZ": 40.0, "ÁLVARO RAMOS": 8.0, 
          "CLAUDIA DOBLES": 5.0, "ARIEL ROBLES": 4.0, "FABRICIO ALVARADO": 4.0, 
          "JOSÉ AGUILAR": 4.0, "OTROS": 3.0}),
]

CANDIDATES = [
    "LAURA FERNÁNDEZ",
    "ÁLVARO RAMOS", 
    "CLAUDIA DOBLES",
    "ARIEL ROBLES",
    "FABRICIO ALVARADO",
    "JOSÉ AGUILAR",
    "OTROS",
]

# =============================================================================
# CONSTRUCCIÓN DE DATOS
# =============================================================================
def polls_to_frame(polls: List[Poll]) -> pd.DataFrame:
    """Convierte lista de encuestas a DataFrame"""
    rows = []
    for p in polls:
        row = {
            "poll_id": p.poll_id,
            "pollster": p.pollster,
            "publish_date": pd.Timestamp(p.publish_date),
            "question_type": p.question_type,
            "moe": p.moe
        }
        row.update(p.values)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df["n_eff"] = 0.25 * (1.96 * 100.0 / df["moe"]) ** 2
    
    # Asegurar columnas
    for c in ["INDECISOS", "NO RESPONDE", "NULO/BLANCO"] + CANDIDATES:
        if c not in df.columns:
            df[c] = np.nan
    
    df["NO RESPONDE"] = df["NO RESPONDE"].fillna(0.0)
    df["NULO/BLANCO"] = df["NULO/BLANCO"].fillna(df["NULO/BLANCO"].median())
    
    # Calcular totales
    df["U"] = (df["INDECISOS"].fillna(0.0) + df["NO RESPONDE"]).clip(0, 95)
    df["B"] = df["NULO/BLANCO"].clip(0, 20)
    df["DECIDED_TOTAL"] = (100.0 - df["U"] - df["B"]).clip(1e-6)
    
    # Shares sobre decididos
    for c in CANDIDATES:
        df[c] = df[c].fillna(0.0)
        df[f"S_{c}"] = (df[c] / df["DECIDED_TOTAL"]).clip(0, 1)
    
    df["RESTO_TOTAL"] = (df["DECIDED_TOTAL"] - df[CANDIDATES].sum(axis=1)).clip(0)
    df["S_RESTO"] = (df["RESTO_TOTAL"] / df["DECIDED_TOTAL"]).clip(0, 1)
    
    # Normalizar shares
    share_cols = [f"S_{c}" for c in CANDIDATES] + ["S_RESTO"]
    total_shares = df[share_cols].sum(axis=1).replace(0, 1.0)
    for col in share_cols:
        df[col] = df[col] / total_shares
    
    return df.sort_values("publish_date").reset_index(drop=True)

def compute_weights(df: pd.DataFrame, half_life_days: float = 14.0) -> np.ndarray:
    """Calcula pesos con decay temporal"""
    days_to_election = (ELECTION_DATE - df["publish_date"]).dt.days.clip(lower=0)
    decay = np.exp(-np.log(2.0) * (days_to_election / half_life_days))
    
    # Factor por tipo de pregunta
    q = df["question_type"].str.lower()
    factor = np.where(q == "papeleta", 1.0, 
             np.where(q == "lista", 1.0, 
             np.where(q == "panel", 0.8,
             np.where(q == "abierta", 0.7, 0.6))))
    
    return (df["n_eff"] * decay * factor).values

# =============================================================================
# MODELO DE AGREGACIÓN ROBUSTO
# =============================================================================
def aggregate_polls(df: pd.DataFrame, weights: np.ndarray) -> Dict:
    """
    Agrega encuestas con promedio ponderado y estima tendencia
    """
    # Filtrar solo papeleta/lista para estimación principal
    mask = df["question_type"].isin(["papeleta", "lista"])
    df_main = df[mask].copy()
    w_main = weights[mask]
    
    if len(df_main) == 0:
        df_main = df.copy()
        w_main = weights
    
    # Normalizar pesos
    w_norm = w_main / w_main.sum()
    
    # Estimar tendencia para Laura Fernández
    days = (df_main["publish_date"] - df_main["publish_date"].min()).dt.days.values
    y_lf = df_main["LAURA FERNÁNDEZ"].values
    
    # Regresión lineal ponderada simple
    X = np.column_stack([np.ones(len(days)), days])
    W = np.diag(w_main)
    try:
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y_lf)
    except np.linalg.LinAlgError:
        beta = np.array([y_lf.mean(), 0])
    
    # Proyectar a día de elección
    days_to_election = (ELECTION_DATE - df_main["publish_date"].min()).days
    lf_projected = beta[0] + beta[1] * days_to_election
    
    # Calcular incertidumbre
    residuals = y_lf - (beta[0] + beta[1] * days)
    rmse = np.sqrt(np.average(residuals**2, weights=w_main))
    
    # Promedio ponderado para todos los candidatos
    estimates = {}
    for c in CANDIDATES:
        col = f"S_{c}" if f"S_{c}" in df_main.columns else c
        if c in df_main.columns:
            estimates[c] = np.average(df_main[c].values, weights=w_norm)
        else:
            estimates[c] = 0.0
    
    # Indecisos
    estimates["U"] = np.average(df_main["U"].values, weights=w_norm)
    estimates["B"] = np.average(df_main["B"].values, weights=w_norm)
    
    return {
        "estimates": estimates,
        "lf_projected": float(np.clip(lf_projected, 20, 60)),
        "lf_trend": float(beta[1]),
        "rmse": float(rmse),
        "n_polls": len(df_main),
        "last_date": df_main["publish_date"].max(),
    }

# =============================================================================
# SIMULACIÓN MONTE CARLO
# =============================================================================
def run_simulation(n_sims: int = N_SIMS, seed: int = SEED) -> Dict:
    """
    Simulación Monte Carlo con distribución robusta de incertidumbre
    """
    print("\n" + "="*80)
    print("🎲 SIMULACIÓN MONTE CARLO - COSTA RICA 2026")
    print("   Actualización: 21 de enero de 2026")
    print("="*80)
    
    # Preparar datos
    df = polls_to_frame(POLLS)
    weights = compute_weights(df)
    agg = aggregate_polls(df, weights)
    
    print(f"\nEncuestas disponibles: {len(df)}")
    print(f"Encuestas papeleta/lista: {agg['n_polls']}")
    print(f"Última encuesta: {agg['last_date'].date()}")
    print(f"Laura Fernández proyectada: {agg['lf_projected']:.1f}%")
    print(f"Tendencia diaria: {agg['lf_trend']:.3f}% por día")
    
    rng = np.random.default_rng(seed)
    
    # === SIMULACIÓN ===
    print(f"\n⏳ Generando {n_sims:,} simulaciones...")
    
    # Parámetros base
    estimates = agg["estimates"]
    lf_base = agg["lf_projected"]
    
    # Incertidumbre total (combinación de error de encuesta + tendencia)
    # Usamos error estándar más conservador basado en última encuesta
    last_poll = df.iloc[-1]
    se_lf = last_poll["moe"] / 1.96  # Error estándar de la última encuesta
    trend_uncertainty = agg["rmse"]  # Incertidumbre por tendencia
    
    # Error total combinado (suma en cuadratura)
    total_se = np.sqrt(se_lf**2 + trend_uncertainty**2 + 1.5**2)  # +1.5 por sesgo sistemático
    
    # Simular Laura Fernández
    sims = pd.DataFrame(index=np.arange(n_sims))
    
    # Distribución de Laura con sesgo ligeramente negativo (conservador)
    lf_sims = rng.normal(lf_base, total_se, size=n_sims)
    
    # Aplicar ajuste por patrones históricos CR
    # Votantes ocasionales pueden movilizarse hacia el líder claro
    tipo_elector = rng.choice(
        ['habitual', 'ocasional_vota', 'ocasional_abstiene', 'abstiene'],
        size=n_sims,
        p=[0.31, 0.30, 0.15, 0.24]
    )
    
    ajuste = np.zeros(n_sims)
    ajuste[tipo_elector == 'ocasional_vota'] = rng.normal(0.5, 0.3, size=(tipo_elector == 'ocasional_vota').sum())
    ajuste[tipo_elector == 'ocasional_abstiene'] = rng.normal(-0.5, 0.3, size=(tipo_elector == 'ocasional_abstiene').sum())
    ajuste[tipo_elector == 'abstiene'] = rng.normal(-1.0, 0.5, size=(tipo_elector == 'abstiene').sum())
    
    sims["LAURA FERNÁNDEZ"] = (lf_sims + ajuste).clip(20, 60)
    
    # Simular otros candidatos con correlación negativa con Laura
    remaining = 100.0 - sims["LAURA FERNÁNDEZ"]
    
    # Proporciones base para distribución del resto
    props = {}
    total_others = sum(estimates[c] for c in CANDIDATES if c != "LAURA FERNÁNDEZ")
    for c in CANDIDATES:
        if c != "LAURA FERNÁNDEZ":
            base_prop = estimates[c] / total_others if total_others > 0 else 0.1
            # Añadir ruido
            noise = rng.normal(0, 0.02, size=n_sims)
            props[c] = np.clip(base_prop + noise, 0.01, 0.5)
    
    # Normalizar proporciones
    total_props = sum(props.values())
    for c in props:
        props[c] = props[c] / total_props
    
    # Distribuir el resto
    # Primero indecisos
    u_base = max(estimates["U"], 25)  # Mínimo 25% para día de elección
    u_se = 4.0  # Incertidumbre en indecisos
    sims["U"] = rng.normal(u_base, u_se, size=n_sims).clip(15, 50)
    
    # Blancos/nulos
    sims["B"] = rng.normal(estimates["B"], 1.0, size=n_sims).clip(0, 8)
    
    # Voto decidido disponible para otros candidatos
    decided = 100.0 - sims["U"] - sims["B"]
    available_for_others = decided - sims["LAURA FERNÁNDEZ"]
    
    # Distribuir entre otros candidatos
    for c in CANDIDATES:
        if c != "LAURA FERNÁNDEZ":
            base = estimates[c]
            se_c = 2.0  # Error estándar para otros candidatos
            sims[c] = rng.normal(base, se_c, size=n_sims).clip(1, 20)
    
    # Añadir RESTO
    sims["RESTO"] = (available_for_others - sims[[c for c in CANDIDATES if c != "LAURA FERNÁNDEZ"]].sum(axis=1)).clip(0, 20)
    
    # Normalizar para que sume 100%
    all_cols = ["LAURA FERNÁNDEZ"] + [c for c in CANDIDATES if c != "LAURA FERNÁNDEZ"] + ["RESTO", "U", "B"]
    total = sims[all_cols].sum(axis=1)
    for col in all_cols:
        sims[col] = 100.0 * sims[col] / total
    
    # === ANÁLISIS ===
    sims["LF"] = sims["LAURA FERNÁNDEZ"]
    sims["wins_round1"] = sims["LF"] >= 40.0
    
    # Top-2
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
    
    # Resumen
    out = {
        "polls_used": agg["n_polls"],
        "update_date": "2026-01-21",
        "aggregation": agg,
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
        },
        "cand_summary": sims[cand_all].describe(percentiles=[0.05, 0.10, 0.50, 0.90, 0.95]).T,
        "top2_pairs": (sims.groupby(["top1", "top2"]).size() / n_sims).sort_values(ascending=False),
        "sims": sims,
    }
    
    return out

# =============================================================================
# VISUALIZACIÓN
# =============================================================================
def create_plots(out: Dict) -> None:
    """Crea visualizaciones"""
    sims = out["sims"]
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    fig.suptitle("SIMULACIÓN ELECTORAL COSTA RICA 2026 - PRIMERA RONDA\n"
                 "Actualización: 21 de enero 2026 (incluye CIEP-UCR enero)",
                 fontsize=14, fontweight='bold')
    
    # 1. Distribución Laura Fernández
    ax = axes[0, 0]
    ax.hist(sims["LF"], bins=80, alpha=0.7, edgecolor='black', color='#2E86AB')
    ax.axvline(40, color='red', linestyle='--', linewidth=2, label='Umbral 40%')
    ax.axvline(sims["LF"].mean(), color='darkblue', linestyle='-', linewidth=2, 
               label=f'Media: {sims["LF"].mean():.1f}%')
    ax.axvline(sims["LF"].median(), color='green', linestyle='-', linewidth=2, 
               label=f'Mediana: {sims["LF"].median():.1f}%')
    ax.set_xlabel("% del voto válido", fontsize=11)
    ax.set_ylabel("Frecuencia", fontsize=11)
    ax.set_title("Laura Fernández - Distribución simulada", fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # 2. Probabilidad acumulada
    ax = axes[0, 1]
    sorted_lf = np.sort(sims["LF"])
    cum_prob = np.arange(1, len(sorted_lf)+1) / len(sorted_lf)
    ax.plot(sorted_lf, cum_prob*100, linewidth=2, color='#2E86AB')
    ax.axvline(40, color='red', linestyle='--', linewidth=2)
    ax.axhline(out["summary"]["p_LF_win_round1"]*100, color='green', linestyle='--',
               label=f'P(>40%) = {out["summary"]["p_LF_win_round1"]*100:.1f}%')
    ax.fill_between(sorted_lf, cum_prob*100, where=(sorted_lf >= 40), alpha=0.3, color='green')
    ax.set_xlabel("% del voto válido", fontsize=11)
    ax.set_ylabel("Probabilidad acumulada (%)", fontsize=11)
    ax.set_title("Función de distribución acumulada", fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # 3. Indecisos
    ax = axes[0, 2]
    ax.hist(sims["U"], bins=60, alpha=0.7, color='#F18F01', edgecolor='black')
    ax.axvline(sims["U"].mean(), color='red', linestyle='--', linewidth=2,
               label=f'Media: {sims["U"].mean():.1f}%')
    ax.axvline(32, color='blue', linestyle=':', linewidth=2, label='CIEP ene-26: 32%')
    ax.set_xlabel("% Indecisos + No responde", fontsize=11)
    ax.set_ylabel("Frecuencia", fontsize=11)
    ax.set_title("Distribución de Indecisos", fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # 4. Boxplot candidatos
    ax = axes[1, 0]
    top_cands = ["LAURA FERNÁNDEZ", "ÁLVARO RAMOS", "CLAUDIA DOBLES",
                 "ARIEL ROBLES", "FABRICIO ALVARADO", "JOSÉ AGUILAR"]
    top_cands = [c for c in top_cands if c in sims.columns]
    data_box = [sims[c].values for c in top_cands]
    bp = ax.boxplot(data_box, tick_labels=[c.split()[0] for c in top_cands], patch_artist=True)
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B', '#95C623']
    for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.axhline(40, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax.set_ylabel("% del voto válido", fontsize=11)
    ax.set_title("Distribución por candidato", fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 5. Laura vs Segundo
    ax = axes[1, 1]
    segundo = sims["ÁLVARO RAMOS"]
    ax.scatter(sims["LF"], segundo, alpha=0.03, s=1, c='#2E86AB')
    ax.axhline(segundo.mean(), color='red', linestyle='--', alpha=0.7,
               label=f'Ramos: {segundo.mean():.1f}%')
    ax.axvline(sims["LF"].mean(), color='blue', linestyle='--', alpha=0.7,
               label=f'Laura: {sims["LF"].mean():.1f}%')
    ax.axvline(40, color='green', linestyle=':', alpha=0.7, label='Umbral 40%')
    ax.set_xlabel("Laura Fernández (%)", fontsize=11)
    ax.set_ylabel("Álvaro Ramos (%)", fontsize=11)
    ax.set_title("Laura vs Segundo Lugar", fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # 6. Top-2 pares
    ax = axes[1, 2]
    top_pairs = out["top2_pairs"].head(8)
    pairs_labels = [f"{a.split()[0]} vs\n{b.split()[0]}" for a, b in top_pairs.index]
    bars = ax.barh(range(len(top_pairs)), top_pairs.values*100, color='#2E86AB')
    ax.set_yticks(range(len(top_pairs)))
    ax.set_yticklabels(pairs_labels, fontsize=9)
    ax.set_xlabel("Probabilidad (%)", fontsize=11)
    ax.set_title("Top combinaciones 1º vs 2º", fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    for bar, val in zip(bars, top_pairs.values*100):
        ax.text(val + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{val:.1f}%', va='center', fontsize=8)
    
    plt.tight_layout()
    plt.savefig("simulacion_cr2026_v2.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✅ Visualización guardada: simulacion_cr2026_v2.png")

# =============================================================================
# REPORTE
# =============================================================================
def print_report(out: Dict) -> None:
    """Imprime reporte"""
    print("\n" + "="*80)
    print("📊 REPORTE FINAL - SIMULACIÓN COSTA RICA 2026")
    print("   Actualización: 21 de enero de 2026")
    print("="*80)
    
    summ = out["summary"]
    agg = out["aggregation"]
    
    print(f"\nSimulaciones: {summ['n_sims']:,}")
    print(f"Fecha proyección: {summ['election_date']}")
    print(f"Encuestas usadas: {out['polls_used']} (papeleta/lista)")
    
    print("\n" + "─"*80)
    print("🏆 LAURA FERNÁNDEZ - RESULTADO PROYECTADO")
    print("─"*80)
    
    print(f"\n  ✓ Probabilidad 1ª ronda (>40%): {summ['p_LF_win_round1']*100:.1f}%")
    print(f"  ✓ Probabilidad 1º lugar:        {summ['p_LF_top1']*100:.1f}%")
    
    print(f"\n  • Media:     {summ['LF_mean']:.1f}%")
    print(f"  • Mediana:   {summ['LF_median']:.1f}%")
    print(f"  • IC 90%:    [{summ['LF_p5']:.1f}% - {summ['LF_p95']:.1f}%]")
    print(f"  • IC 80%:    [{summ['LF_p10']:.1f}% - {summ['LF_p90']:.1f}%]")
    
    print(f"\n  • Indecisos: {summ['U_mean']:.1f}%")
    print(f"  • Blancos:   {summ['B_mean']:.1f}%")
    
    print("\n" + "─"*80)
    print("🎯 INTERPRETACIÓN")
    print("─"*80)
    
    prob = summ['p_LF_win_round1'] * 100
    
    if prob >= 75:
        print("\n  🟢 VICTORIA EN PRIMERA RONDA: ALTA PROBABILIDAD")
        print(f"     Laura Fernández supera el 40% en {prob:.0f}% de escenarios.")
    elif prob >= 50:
        print("\n  🟡 VICTORIA EN PRIMERA RONDA: PROBABLE")
        print(f"     Laura Fernández supera el 40% en {prob:.0f}% de escenarios.")
    elif prob >= 30:
        print("\n  🟡 ESCENARIO COMPETIDO")
        print(f"     Probabilidad moderada ({prob:.0f}%) de victoria en 1ª ronda.")
    else:
        print("\n  🔴 SEGUNDA RONDA MUY PROBABLE")
        print(f"     Solo {prob:.0f}% de probabilidad de superar el 40%.")
    
    print("\n" + "─"*80)
    print("📋 DATOS CIEP-UCR ENERO 2026")
    print("─"*80)
    print("""
  • Muestra transversal: 1,006 entrevistas (±3.1 pp)
  • Trabajo de campo: 12-15 enero 2026
  • Filtro votantes probables (69% de muestra)
  
  Resultados:
  - Laura Fernández: 40% (umbral de 1ª ronda)
  - Álvaro Ramos: 8%
  - Claudia Dobles: 5%
  - Ariel Robles, Fabricio Alvarado, José Aguilar: 4% c/u
  - Indecisos: 32%
  
  Panel CIEP: Crecimiento de LF viene de captar indecisos,
  no de robar votos a otros partidos.
""")
    
    print("="*80)

# =============================================================================
# MAIN
# =============================================================================
def main() -> None:
    """Función principal"""
    out = run_simulation(n_sims=N_SIMS, seed=SEED)
    print_report(out)
    
    print("\n⏳ Guardando resultados...")
    out["sims"].to_csv("simulacion_cr2026_v2.csv", index=False)
    out["cand_summary"].to_csv("resumen_candidatos_v2.csv")
    out["top2_pairs"].head(20).to_csv("top2_pairs_v2.csv")
    
    create_plots(out)
    
    print("\n✅ SIMULACIÓN COMPLETADA")
    print("\nArchivos generados:")
    print("  • simulacion_cr2026_v2.csv")
    print("  • resumen_candidatos_v2.csv")
    print("  • top2_pairs_v2.csv")
    print("  • simulacion_cr2026_v2.png")

if __name__ == "__main__":
    main()
