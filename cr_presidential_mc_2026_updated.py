#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monte Carlo – Elecciones Presidenciales Costa Rica 2026 (actualizado con CIEP 21-ene-2026)

Objetivo
--------
Estimar (vía simulación Monte Carlo) la probabilidad de que un(a) candidato(a) supere el 40% de los votos válidos
en 1ª ronda. El modelo está diseñado para ser:

- Reproducible (semilla fija, exporta simulaciones).
- Auditable (separación explícita entre: datos de encuestas, supuestos, y simulación).
- Sensible a incertidumbre clave: comportamiento de indecisos.

Importante
----------
1) NO es un pronóstico “determinista”; devuelve distribuciones y sensibilidad.
2) Este script trabaja con un "pool" de encuestas agregadas (no microdatos).
3) El supuesto más influyente sigue siendo la asignación de indecisos.

Cómo correr
-----------
pip install numpy pandas matplotlib
python cr_presidential_mc_2026_updated.py

Salidas
-------
- simulaciones_mc_2026.csv (si EXPORT_SIMULATIONS=True)
- resumen_mc_2026.json
- figura_mc_2026.png
"""

from __future__ import annotations

import math
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =========================
# Configuración principal
# =========================
ELECTION_DATE = pd.Timestamp("2026-02-01")  # Ajustá si querés simular otra fecha
SEED = 20260121
N_SIMS = 200_000  # subir/bajar según tu hardware

EXPORT_SIMULATIONS = True
SIM_CSV_PATH = "simulaciones_mc_2026.csv"
SUMMARY_JSON_PATH = "resumen_mc_2026.json"
FIG_PATH = "figura_mc_2026.png"

# Candidatos a modelar explícitamente.
# Todo lo no incluido se agrega como "RESTO".
CANDIDATES = [
    "LAURA FERNÁNDEZ",
    "ÁLVARO RAMOS",
    "CLAUDIA DOBLES",
    "ARIEL ROBLES",
    "FABRICIO ALVARADO",
    "JOSÉ AGUILAR",
    "OTROS",
]

# Mezcla (por defecto) de escenarios de indecisos.
# Podés ajustar con evidencia empírica (p.ej. backtesting 2010–2022).
INDECISION_MIX = {
    "proporcional": 0.35,
    "momentum": 0.30,
    "dispersion": 0.20,
    "abstencion": 0.15,
}

# Parámetros del escenario "momentum" (bandwagon/arrastre hacia el líder).
# factor>1 aumenta el peso del líder al repartir indecisos.
MOMENTUM_FACTOR_MEAN = 1.50
MOMENTUM_FACTOR_SD = 0.15

# Escenario "abstención": fracción de indecisos que finalmente NO emite voto válido.
ABSTENTION_FRAC_MEAN = 0.70
ABSTENTION_FRAC_SD = 0.10

# Escenario "dispersión": una porción de indecisos va a "RESTO" (anti-establishment / fragmentación).
DISPERSION_TO_RESTO_MEAN = 0.35
DISPERSION_TO_RESTO_SD = 0.10

# Nulo/blanco: si no está en la tabla, se modela como variable pequeña (para votos válidos).
# Se usa Beta en [0, 0.08] con media ~2% y sd ~1%.
NULL_BLANK_MEAN = 0.02
NULL_BLANK_SD = 0.01
NULL_BLANK_MAX = 0.08


# =========================
# Datos de encuestas (pool)
# =========================
@dataclass
class Poll:
    poll_id: str
    pollster: str
    publish_date: str  # YYYY-MM-DD
    question_type: str  # abierta/papeleta/lista/panel
    moe: float  # margen de error 95%
    values: Dict[str, Optional[float]]  # % sobre total (incluye indecisos), puede tener missing

    def to_row(self) -> Dict:
        row = {
            "poll_id": self.poll_id,
            "pollster": self.pollster,
            "publish_date": self.publish_date,
            "question_type": self.question_type,
            "moe": self.moe,
        }
        row.update(self.values)
        return row


# NOTA:
# - Estos datos se basan en tu tabla consolidada y el resumen nuevo del CIEP (21-ene-2026).
# - Si agregás más encuestas, insertalas aquí con la misma estructura.
POLLS: List[Poll] = [
    Poll("ciep_ucr_1", "CIEP-UCR", "2025-10-22", "abierta", 2.7, {
        "INDECISOS": 55.0, "LAURA FERNÁNDEZ": 25.0, "ÁLVARO RAMOS": 7.0, "ARIEL ROBLES": 3.0,
        "CLAUDIA DOBLES": 3.0, "OTROS": 4.1, "NULO/BLANCO": 2.5
    }),
    Poll("idespo_una_1", "IDESPO-UNA", "2025-11-06", "abierta", 3.3, {
        "INDECISOS": 52.4, "LAURA FERNÁNDEZ": 28.1, "ÁLVARO RAMOS": 6.2, "ARIEL ROBLES": 2.3,
        "CLAUDIA DOBLES": 2.9, "OTROS": 3.3, "NO RESPONDE": 1.6, "NULO/BLANCO": 2.0
    }),
    Poll("opol_1", "OPOL", "2025-10-29", "papeleta", 2.2, {
        "INDECISOS": 38.79, "LAURA FERNÁNDEZ": 31.2, "ÁLVARO RAMOS": 7.41, "FABRICIO ALVARADO": 4.84,
        "ARIEL ROBLES": 3.72, "CLAUDIA DOBLES": 2.92, "OTROS": 2.24, "NO RESPONDE": 0.24, "NULO/BLANCO": 1.8
    }),
    Poll("demoscopia_1", "Demoscopia", "2025-11-13", "abierta", 2.83, {
        "INDECISOS": 56.7, "LAURA FERNÁNDEZ": 21.4, "ÁLVARO RAMOS": 9.0, "FABRICIO ALVARADO": 3.7,
        "ARIEL ROBLES": 2.1, "CLAUDIA DOBLES": 3.0, "OTROS": 4.1,
        # NULO/BLANCO no reportado en ese corte
    }),
    Poll("opol_2", "OPOL", "2025-11-12", "papeleta", 2.16, {
        "INDECISOS": 42.3, "LAURA FERNÁNDEZ": 21.0, "ÁLVARO RAMOS": 10.4, "FABRICIO ALVARADO": 6.5,
        "ARIEL ROBLES": 4.1, "CLAUDIA DOBLES": 2.9, "OTROS": 2.7
    }),
    Poll("opol_3", "OPOL", "2025-11-25", "papeleta", 2.10, {
        "INDECISOS": 37.37, "LAURA FERNÁNDEZ": 37.85, "ÁLVARO RAMOS": 7.19, "FABRICIO ALVARADO": 3.97,
        "ARIEL ROBLES": 2.35, "CLAUDIA DOBLES": 1.29, "OTROS": 2.11, "NO RESPONDE": 0.5, "NULO/BLANCO": 1.03
    }),
    Poll("ciep_ucr_2", "CIEP-UCR", "2025-12-03", "papeleta", 2.3, {
        "INDECISOS": 45.0, "LAURA FERNÁNDEZ": 30.0, "ÁLVARO RAMOS": 8.0, "FABRICIO ALVARADO": 1.0,
        "ARIEL ROBLES": 5.0, "CLAUDIA DOBLES": 4.0, "OTROS": 1.5, "NULO/BLANCO": 2.6
    }),
    Poll("idespo_una_2", "IDESPO-UNA", "2025-12-08", "panel", 3.3, {
        "INDECISOS": 43.9, "LAURA FERNÁNDEZ": 32.8, "ÁLVARO RAMOS": 6.6, "ARIEL ROBLES": 3.7,
        "CLAUDIA DOBLES": 5.2, "OTROS": 4.4, "NO RESPONDE": 1.6, "NULO/BLANCO": 1.8
    }),
    Poll("opol_4", "OPOL", "2025-12-10", "abierta", 2.24, {
        "INDECISOS": 32.67, "LAURA FERNÁNDEZ": 38.01, "ÁLVARO RAMOS": 6.12, "FABRICIO ALVARADO": 3.81,
        "ARIEL ROBLES": 3.63, "CLAUDIA DOBLES": 2.39, "OTROS": 3.91, "NULO/BLANCO": 2.15
    }),
    Poll("demoscopia_2", "Demoscopia", "2025-12-16", "papeleta", 2.83, {
        "INDECISOS": 41.7, "LAURA FERNÁNDEZ": 27.4, "ÁLVARO RAMOS": 11.3, "FABRICIO ALVARADO": 3.6,
        "ARIEL ROBLES": 4.8, "CLAUDIA DOBLES": 3.1, "OTROS": 3.1, "NO RESPONDE": 2.15, "NULO/BLANCO": 2.91
    }),
    Poll("opol_5", "OPOL", "2025-12-23", "papeleta", 2.11, {
        "INDECISOS": 33.77, "LAURA FERNÁNDEZ": 39.45, "ÁLVARO RAMOS": 5.64, "FABRICIO ALVARADO": 2.98,
        "ARIEL ROBLES": 3.13, "CLAUDIA DOBLES": 2.63, "OTROS": 2.64, "NULO/BLANCO": 2.91
    }),
    Poll("cid_gallup", "CID Gallup", "2026-01-06", "lista", 2.87, {
        "INDECISOS": 14.0, "LAURA FERNÁNDEZ": 41.0, "ÁLVARO RAMOS": 9.0, "FABRICIO ALVARADO": 6.0,
        "ARIEL ROBLES": 4.0, "CLAUDIA DOBLES": 4.0, "JOSÉ AGUILAR": 2.0, "OTROS": 4.0, "NO RESPONDE": 11.0
    }),
    # NUEVO: CIEP-UCR 21-ene-2026 (resumen provisto por vos)
    Poll("ciep_ucr_3", "CIEP-UCR", "2026-01-21", "papeleta", 3.1, {
        "INDECISOS": 32.0,
        "LAURA FERNÁNDEZ": 40.0,
        "ÁLVARO RAMOS": 8.0,
        "CLAUDIA DOBLES": 5.0,
        "ARIEL ROBLES": 4.0,
        "FABRICIO ALVARADO": 4.0,
        "JOSÉ AGUILAR": 4.0,
        "OTROS": 3.0,
        # NULO/BLANCO y NO RESPONDE no están en el resumen; se imputan/estiman en el modelo.
    }),
]


# =========================
# Preparación de datos
# =========================
def polls_to_frame(polls: List[Poll]) -> pd.DataFrame:
    df = pd.DataFrame([p.to_row() for p in polls])
    df["publish_date"] = pd.to_datetime(df["publish_date"])
    # n_eff aproximado a partir de margen de error (95%): moe ≈ 1.96*sqrt(p(1-p)/n)*100, usando p=0.5 => n_eff
    df["n_eff"] = 0.25 * (1.96 * 100.0 / df["moe"]) ** 2

    # Normalizar columnas esperadas
    for c in ["INDECISOS", "NO RESPONDE", "NULO/BLANCO"] + CANDIDATES:
        if c not in df.columns:
            df[c] = np.nan

    df["NO RESPONDE"] = df["NO RESPONDE"].fillna(0.0)

    # Imputación suave para NULO/BLANCO si falta (no domina el resultado, pero evita inconsistencias)
    # Regla: usar la mediana de NULO/BLANCO observada en encuestas tipo papeleta/lista; si no existe, usar 2%.
    nb_med = df.loc[df["question_type"].isin(["papeleta", "lista"]), "NULO/BLANCO"].median()
    if np.isnan(nb_med):
        nb_med = 2.0
    df["NULO/BLANCO"] = df["NULO/BLANCO"].fillna(nb_med)

    # Sumar "RESTO" implícito si las candidaturas explícitas no cubren todo
    df["U"] = (df["INDECISOS"].fillna(0.0) + df["NO RESPONDE"].fillna(0.0)).clip(lower=0.0, upper=95.0)
    df["B"] = df["NULO/BLANCO"].clip(lower=0.0, upper=20.0)
    df["DECIDED_TOTAL"] = (100.0 - df["U"] - df["B"]).clip(lower=1e-6)

    # Completar missings de candidatos como 0 (si no aparece reportado en esa encuesta)
    for c in CANDIDATES:
        df[c] = df[c].fillna(0.0)

    # Voto "resto" dentro del total (antes de normalizar a decididos)
    df["RESTO_TOTAL"] = (df["DECIDED_TOTAL"] - df[CANDIDATES].sum(axis=1)).clip(lower=0.0)

    # Shares dentro de decididos (suman 1 con RESTO_SHARE)
    for c in CANDIDATES:
        df[f"S_{c}"] = (df[c] / df["DECIDED_TOTAL"]).clip(lower=0.0)
    df["S_RESTO"] = (df["RESTO_TOTAL"] / df["DECIDED_TOTAL"]).clip(lower=0.0)

    # Normalizar por si hay pequeños desajustes de suma
    share_cols = [f"S_{c}" for c in CANDIDATES] + ["S_RESTO"]
    ssum = df[share_cols].sum(axis=1).replace(0, 1.0)
    df[share_cols] = df[share_cols].div(ssum, axis=0)

    return df.sort_values("publish_date").reset_index(drop=True)


def compute_weights(df: pd.DataFrame, half_life_days: float = 21.0) -> pd.Series:
    """
    Ponderación:
      w = n_eff * exp(-ln(2)*days_to_election/half_life)
    + penaliza (ligeramente) instrumentos no equivalentes a papeleta/lista.
    """
    days_to_election = (ELECTION_DATE - df["publish_date"]).dt.days.clip(lower=0)
    decay = np.exp(-math.log(2.0) * (days_to_election / half_life_days))
    w = df["n_eff"] * decay

    # downweight "abierta" y "panel" (puede ajustar)
    q = df["question_type"].str.lower()
    factor = np.where(q == "papeleta", 1.0,
             np.where(q == "lista", 1.0,
             np.where(q == "abierta", 0.75,
             np.where(q == "panel", 0.85, 0.8))))
    return w * factor


# =========================
# Estimación paramétrica (pool de encuestas)
# =========================
def weighted_mean_and_var(x: np.ndarray, w: np.ndarray) -> Tuple[float, float]:
    w = np.asarray(w, float)
    x = np.asarray(x, float)
    wm = np.sum(w * x) / np.sum(w)
    # Var ponderada (tipo "population" ajustada)
    v = np.sum(w * (x - wm) ** 2) / np.sum(w)
    return float(wm), float(v)


def fit_undecided_beta(df: pd.DataFrame, w: np.ndarray) -> Tuple[float, float]:
    """
    Ajusta Beta para U (indecisos+no responde) en proporción (0-1).
    Usa media y var ponderadas; si var es muy baja, agrega piso.
    """
    u = (df["U"].values / 100.0).clip(1e-4, 1 - 1e-4)
    mu, v = weighted_mean_and_var(u, w)
    v = max(v, 1e-5)

    # Beta: var = mu(1-mu)/(a+b+1)
    k = (mu * (1 - mu) / v) - 1
    k = max(k, 2.0)
    a = mu * k
    b = (1 - mu) * k
    return float(a), float(b)


def fit_null_blank_beta() -> Tuple[float, float]:
    """
    Beta truncada a [0, NULL_BLANK_MAX]; construimos Beta en [0,1] y luego escalamos.
    """
    mu = NULL_BLANK_MEAN / NULL_BLANK_MAX
    sd = NULL_BLANK_SD / NULL_BLANK_MAX
    v = max(sd * sd, 1e-6)
    k = (mu * (1 - mu) / v) - 1
    k = max(k, 5.0)
    a = mu * k
    b = (1 - mu) * k
    return float(a), float(b)


def fit_shares_logit_normal(df: pd.DataFrame, w: np.ndarray, eps: float = 1e-6) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Ajusta distribución Normal multivariada para logits de shares en decididos:
      y_j = log(s_j / s_base)
    donde base = S_RESTO.
    """
    share_cols = [f"S_{c}" for c in CANDIDATES] + ["S_RESTO"]
    S = df[share_cols].values
    base = np.clip(S[:, -1], eps, 1.0)
    Y = []
    names = []
    for j, c in enumerate(CANDIDATES):
        sj = np.clip(S[:, j], eps, 1.0)
        Y.append(np.log(sj / base))
        names.append(c)
    Y = np.vstack(Y).T  # n_polls x k

    # Media ponderada
    w = w / np.sum(w)
    mu = np.sum(Y * w[:, None], axis=0)

    # Cov ponderada con "shrinkage" simple
    Z = Y - mu[None, :]
    cov = (Z.T @ (Z * w[:, None]))  # weighted cov (population)
    # piso diagonal para evitar singularidad con pocos puntos
    cov = cov + np.eye(cov.shape[0]) * 0.02
    return mu, cov, names


# =========================
# Simulación
# =========================
def draw_trunc_beta(rng: np.random.Generator, a: float, b: float, scale: float = 1.0, max_val: Optional[float] = None) -> float:
    x = rng.beta(a, b) * scale
    if max_val is not None:
        x = min(x, max_val)
    return float(x)


def simulate(df: pd.DataFrame, n_sims: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    w = compute_weights(df).values

    # Fit componentes
    aU, bU = fit_undecided_beta(df, w)
    aNB, bNB = fit_null_blank_beta()
    mu_y, cov_y, cand_names = fit_shares_logit_normal(df, w)

    # Precompute: mix CDF
    scen_names = list(INDECISION_MIX.keys())
    scen_probs = np.array([INDECISION_MIX[k] for k in scen_names], float)
    scen_probs = scen_probs / scen_probs.sum()
    scen_cdf = np.cumsum(scen_probs)

    # Resultados
    out = pd.DataFrame(index=np.arange(n_sims))

    for i in range(n_sims):
        # 1) U y B (sobre total)
        U = draw_trunc_beta(rng, aU, bU, scale=1.0, max_val=0.90)  # proporción
        B = draw_trunc_beta(rng, aNB, bNB, scale=NULL_BLANK_MAX, max_val=NULL_BLANK_MAX)  # proporción

        # 2) Shares en decididos (softmax con base "RESTO")
        y = rng.multivariate_normal(mu_y, cov_y)
        expy = np.exp(np.clip(y, -12, 12))
        den = 1.0 + expy.sum()
        s_base = 1.0 / den
        s = expy * s_base  # shares de candidatos en decididos
        shares_decided = dict(zip(cand_names, s))
        share_resto_decided = s_base

        # 3) Elegir escenario indecisos
        u = rng.random()
        scen = scen_names[int(np.searchsorted(scen_cdf, u))]

        # Cantidad de indecisos que termina emitiendo voto válido (proporción de U)
        if scen == "abstencion":
            abst = float(np.clip(rng.normal(ABSTENTION_FRAC_MEAN, ABSTENTION_FRAC_SD), 0.0, 1.0))
        else:
            abst = 0.0

        U_vota = U * (1.0 - abst)  # proporción del total que se suma a voto válido

        # Reparto de U_vota sobre candidaturas
        alloc = {c: 0.0 for c in cand_names}
        alloc_resto = 0.0

        if scen == "proporcional":
            # según shares de decididos (incluye resto)
            tot = sum(shares_decided.values()) + share_resto_decided
            for c in cand_names:
                alloc[c] = U_vota * (shares_decided[c] / tot)
            alloc_resto = U_vota * (share_resto_decided / tot)

        elif scen == "momentum":
            # líder recibe un peso multiplicado
            leader = max(shares_decided.items(), key=lambda kv: kv[1])[0]
            factor = float(np.clip(rng.normal(MOMENTUM_FACTOR_MEAN, MOMENTUM_FACTOR_SD), 1.05, 2.5))
            weights = {}
            for c in cand_names:
                weights[c] = shares_decided[c] * (factor if c == leader else 1.0)
            weights_resto = share_resto_decided
            tot = sum(weights.values()) + weights_resto
            for c in cand_names:
                alloc[c] = U_vota * (weights[c] / tot)
            alloc_resto = U_vota * (weights_resto / tot)

        elif scen == "dispersion":
            # una parte va directo a RESTO; el resto proporcional
            to_resto = float(np.clip(rng.normal(DISPERSION_TO_RESTO_MEAN, DISPERSION_TO_RESTO_SD), 0.0, 0.8))
            u_resto = U_vota * to_resto
            u_rem = U_vota - u_resto
            tot = sum(shares_decided.values()) + share_resto_decided
            for c in cand_names:
                alloc[c] = u_rem * (shares_decided[c] / tot)
            alloc_resto = u_resto + (u_rem * (share_resto_decided / tot))

        elif scen == "abstencion":
            # lo que sí vota, se reparte proporcional
            tot = sum(shares_decided.values()) + share_resto_decided
            for c in cand_names:
                alloc[c] = U_vota * (shares_decided[c] / tot)
            alloc_resto = U_vota * (share_resto_decided / tot)

        else:
            # fallback proporcional
            tot = sum(shares_decided.values()) + share_resto_decided
            for c in cand_names:
                alloc[c] = U_vota * (shares_decided[c] / tot)
            alloc_resto = U_vota * (share_resto_decided / tot)

        # 4) Construir voto total por candidatura (sobre el total de personas)
        decided_total = max(1e-9, 1.0 - U - B)  # proporción del total que ya está decidida y emite voto válido
        votes = {}
        for c in cand_names:
            votes[c] = decided_total * shares_decided[c] + alloc[c]
        votes["RESTO"] = decided_total * share_resto_decided + alloc_resto

        # 5) Convertir a VOTOS VÁLIDOS: excluir nulo/blanco
        valid_sum = sum(votes.values())
        # seguridad numérica
        valid_sum = max(valid_sum, 1e-9)
        for c in cand_names:
            out.at[i, c] = 100.0 * votes[c] / valid_sum
        out.at[i, "RESTO"] = 100.0 * votes["RESTO"] / valid_sum

        out.at[i, "U_pct_total"] = 100.0 * U
        out.at[i, "B_pct_total"] = 100.0 * B
        out.at[i, "scenario"] = scen

    # Métricas 1ª ronda
    out["LF"] = out["LAURA FERNÁNDEZ"]
    out["wins_round1"] = out["LF"] >= 40.0

    # Top-2
    cand_all = cand_names + ["RESTO"]
    vals = out[cand_all].values
    top1_idx = np.argmax(vals, axis=1)
    vals2 = vals.copy()
    vals2[np.arange(len(out)), top1_idx] = -1.0
    top2_idx = np.argmax(vals2, axis=1)

    out["top1"] = [cand_all[i] for i in top1_idx]
    out["top2"] = [cand_all[i] for i in top2_idx]

    return out


# =========================
# Reporte
# =========================
def summarize(sim: pd.DataFrame) -> Dict:
    def q(x, p): return float(np.quantile(x, p))

    summary = {
        "n_sims": int(sim.shape[0]),
        "p_LF_win_round1": float(sim["wins_round1"].mean()),
        "p_LF_top1": float((sim["top1"] == "LAURA FERNÁNDEZ").mean()),
        "LF_mean": float(sim["LF"].mean()),
        "LF_median": float(sim["LF"].median()),
        "LF_p05": q(sim["LF"], 0.05),
        "LF_p10": q(sim["LF"], 0.10),
        "LF_p90": q(sim["LF"], 0.90),
        "LF_p95": q(sim["LF"], 0.95),
        "U_mean_pct_total": float(sim["U_pct_total"].mean()),
        "U_p10_pct_total": q(sim["U_pct_total"], 0.10),
        "U_p90_pct_total": q(sim["U_pct_total"], 0.90),
        "scenario_freq": sim["scenario"].value_counts(normalize=True).to_dict(),
        "top2_pairs_top10": (sim.groupby(["top1", "top2"]).size() / sim.shape[0]).sort_values(ascending=False).head(10).to_dict(),
    }
    return summary


def plot(sim: pd.DataFrame) -> None:
    plt.figure(figsize=(10, 6))
    plt.hist(sim["LF"], bins=80)
    plt.axvline(40, linestyle="--")
    plt.title("Distribución simulada – Laura Fernández (% voto válido)")
    plt.xlabel("% voto válido")
    plt.ylabel("Frecuencia")
    plt.tight_layout()
    plt.savefig(FIG_PATH, dpi=200)
    plt.close()


def main() -> None:
    df = polls_to_frame(POLLS)

    sim = simulate(df, n_sims=N_SIMS, seed=SEED)
    summ = summarize(sim)

    print("\n=== RESUMEN MONTE CARLO (actualizado) ===")
    for k, v in summ.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")

    with open(SUMMARY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=2)

    if EXPORT_SIMULATIONS:
        sim.to_csv(SIM_CSV_PATH, index=False)

    plot(sim)
    print("\nArchivos generados:")
    print(f" - {SUMMARY_JSON_PATH}")
    if EXPORT_SIMULATIONS:
        print(f" - {SIM_CSV_PATH}")
    print(f" - {FIG_PATH}")


if __name__ == "__main__":
    main()
