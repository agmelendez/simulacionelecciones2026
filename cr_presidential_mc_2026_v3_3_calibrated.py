#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMULACIÓN ELECTORAL COSTA RICA 2026 - VERSIÓN 3.1 CON CALIBRACIÓN HISTÓRICA
================================================================================
Actualización: 28 de enero de 2026

NUEVO EN V3.1:
- Módulo de calibración histórica basado en CIEP-UCR e IDESPO-UNA (2014-2022)
- Análisis del error sistemático encuesta vs resultado TSE
- Ajuste dinámico de incertidumbre según nivel de indecisión
- Modelado empírico de redistribución de indecisos

Fuentes de datos históricos:
- Encuestas: CIEP-UCR (última antes de elección, ventana 2 meses)
- Resultados oficiales: TSE Costa Rica (primera ronda)
- Elecciones analizadas: 2022, 2018, 2014 (+ referencias 2010, 2006)

Metodología:
Este script incorpora un factor de calibración empírico derivado del análisis
histórico de errores encuesta-resultado en Costa Rica. La calibración ajusta:
1. El error esperado según el nivel de indecisión observado
2. La dirección típica del sesgo (hacia frontrunner o hacia "sorpresa")
3. La incertidumbre total del modelo

Autor: Agustín Gómez Meléndez (CIOdD-UCR)
Fecha: 28 de enero de 2026
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')

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

# =============================================================================
# MÓDULO DE CALIBRACIÓN HISTÓRICA
# =============================================================================
@dataclass
class HistoricalElection:
    """Datos de una elección histórica para calibración."""
    year: int
    election_date: str
    # Última encuesta CIEP dentro de 2 meses (candidato líder)
    ciep_leader: str
    ciep_leader_pct: float
    ciep_second: str
    ciep_second_pct: float
    ciep_undecided: float
    ciep_date: str
    # Resultado TSE primera ronda
    tse_first: str
    tse_first_pct: float
    tse_second: str
    tse_second_pct: float
    # Observaciones
    notes: str = ""


# =============================================================================
# APROBACIÓN PRESIDENCIAL - DATOS CIEP-UCR (Calibración continuismo)
# =============================================================================
@dataclass
class PresidentialApproval:
    """
    Datos de aprobación presidencial CIEP-UCR para calibrar efecto continuista.
    
    Hipótesis: La aprobación del presidente saliente predice el desempeño
    del candidato continuista en la siguiente elección.
    """
    president: str
    term: str  # "2010-2014", etc.
    party: str
    approval_start: float  # % buena/muy buena al inicio
    approval_start_date: str
    approval_end: float  # % buena/muy buena al final
    approval_end_date: str
    # Resultado de la siguiente elección
    continuist_candidate: str
    continuist_result_r1: float  # % en primera ronda
    continuist_won: bool
    notes: str = ""


PRESIDENTIAL_APPROVAL_DATA: List[PresidentialApproval] = [
    PresidentialApproval(
        president="Laura Chinchilla",
        term="2010-2014",
        party="PLN",
        approval_start=65.0,  # "dos terceras partes" según CIEP
        approval_start_date="2010-Q3",
        approval_end=15.0,
        approval_end_date="2013-04",
        continuist_candidate="Johnny Araya (PLN)",
        continuist_result_r1=29.71,
        continuist_won=False,
        notes="Desplome de -50pp; PLN pasó a 2ª ronda pero abandonó campaña"
    ),
    PresidentialApproval(
        president="Luis Guillermo Solís",
        term="2014-2018",
        party="PAC",
        approval_start=35.7,
        approval_start_date="2014-07",
        approval_end=25.0,
        approval_end_date="2018-03",
        continuist_candidate="Carlos Alvarado (PAC)",
        continuist_result_r1=21.66,
        continuist_won=True,  # Ganó en 2ª ronda
        notes="Caída moderada -10.7pp; PAC ganó pero en 2ª ronda muy competida"
    ),
    PresidentialApproval(
        president="Carlos Alvarado",
        term="2018-2022",
        party="PAC",
        approval_start=66.0,  # Pico pandemia abril 2020
        approval_start_date="2020-04",
        approval_end=18.0,
        approval_end_date="2022-03",
        continuist_candidate="Welmer Ramos (PAC)",
        continuist_result_r1=0.66,  # Colapso total
        continuist_won=False,
        notes="Desplome de -48pp; PAC prácticamente desapareció"
    ),
    PresidentialApproval(
        president="Rodrigo Chaves",
        term="2022-2026",
        party="PPSD",
        approval_start=79.0,  # Récord histórico
        approval_start_date="2022-08",
        approval_end=52.0,  # Estimación actual (enero 2026)
        approval_end_date="2026-01",
        continuist_candidate="Laura Fernández (PPSD)",
        continuist_result_r1=None,  # Pendiente
        continuist_won=None,
        notes="Caída moderada ~-27pp; sigue siendo el más popular al final"
    ),
]


def analyze_approval_effect() -> Dict:
    """
    Analiza el efecto de la aprobación presidencial en el voto continuista.
    
    Calcula:
    - Correlación aprobación final → resultado continuista
    - Umbral de aprobación para victoria
    - Factor de ajuste para 2026
    """
    # Excluir Chaves (sin resultado aún)
    historical = [p for p in PRESIDENTIAL_APPROVAL_DATA if p.continuist_result_r1 is not None]
    
    approvals_end = [p.approval_end for p in historical]
    results = [p.continuist_result_r1 for p in historical]
    approval_changes = [p.approval_end - p.approval_start for p in historical]
    
    # Correlación aprobación final → resultado
    corr_approval_result = np.corrcoef(approvals_end, results)[0, 1]
    
    # Regresión simple: resultado = a + b * aprobación
    if len(approvals_end) > 1:
        slope, intercept = np.polyfit(approvals_end, results, 1)
    else:
        slope, intercept = 0, np.mean(results)
    
    # Datos de Chaves para proyección
    chaves = PRESIDENTIAL_APPROVAL_DATA[-1]
    
    # Proyección para 2026 usando regresión histórica
    projected_continuist = intercept + slope * chaves.approval_end
    
    # Factor de ajuste: comparar aprobación de Chaves vs promedio histórico
    avg_approval_end = np.mean(approvals_end)
    approval_advantage = chaves.approval_end - avg_approval_end
    
    # Calcular "bonus" para continuista basado en aprobación excepcional
    # Chaves con 52% vs promedio histórico ~19% = +33pp de ventaja
    if approval_advantage > 20:
        continuist_bonus = 3.0  # Fuerte efecto positivo
    elif approval_advantage > 10:
        continuist_bonus = 1.5
    elif approval_advantage > 0:
        continuist_bonus = 0.5
    else:
        continuist_bonus = -1.0  # Efecto negativo si está bajo promedio
    
    return {
        'historical_data': historical,
        'correlation_approval_result': float(corr_approval_result),
        'regression_slope': float(slope),
        'regression_intercept': float(intercept),
        'avg_approval_end_historical': float(avg_approval_end),
        'chaves_approval_current': float(chaves.approval_end),
        'approval_advantage_pp': float(approval_advantage),
        'projected_continuist_r1': float(np.clip(projected_continuist, 20, 60)),
        'continuist_bonus_pp': float(continuist_bonus),
        # Análisis adicional
        'min_approval_for_win': 25.0,  # Solís con 25% → PAC ganó en 2ª
        'approval_collapse_threshold': -30.0,  # Caída > 30pp = colapso
        'chaves_approval_change': float(chaves.approval_end - chaves.approval_start),
    }


def print_approval_analysis(approval_analysis: Dict) -> None:
    """Imprime análisis de aprobación presidencial."""
    print("\n" + "─"*80)
    print("👑 APROBACIÓN PRESIDENCIAL - EFECTO EN VOTO CONTINUISTA")
    print("─"*80)
    
    print(f"\n  Fuente: CIEP-UCR (% buena/muy buena gestión presidente)")
    
    print(f"\n  {'Presidente':<20} {'Aprob. inicio':<14} {'Aprob. final':<14} {'Cambio':<10} {'Continuista R1':<15}")
    print("  " + "-"*73)
    
    for p in PRESIDENTIAL_APPROVAL_DATA:
        change = p.approval_end - p.approval_start
        result = f"{p.continuist_result_r1:.1f}%" if p.continuist_result_r1 else "Pendiente"
        print(f"  {p.president:<20} {p.approval_start:>6.0f}%{'':<6} {p.approval_end:>6.0f}%{'':<6} {change:>+6.0f}pp{'':<2} {result:<15}")
    
    aa = approval_analysis
    print(f"\n  Análisis estadístico:")
    print(f"    • Correlación aprobación final → resultado: {aa['correlation_approval_result']:.2f}")
    print(f"    • Regresión: Resultado = {aa['regression_intercept']:.1f} + {aa['regression_slope']:.2f} × Aprobación")
    print(f"    • Promedio histórico aprobación final: {aa['avg_approval_end_historical']:.1f}%")
    
    print(f"\n  Situación Chaves 2026:")
    print(f"    • Aprobación actual: {aa['chaves_approval_current']:.0f}%")
    print(f"    • Ventaja vs promedio histórico: {aa['approval_advantage_pp']:+.0f} pp")
    print(f"    • Cambio desde inicio: {aa['chaves_approval_change']:+.0f} pp")
    print(f"    • Proyección continuista (regresión): {aa['projected_continuist_r1']:.1f}%")
    print(f"    • Bonus estimado para Laura: {aa['continuist_bonus_pp']:+.1f} pp")


# =============================================================================
# APROBACIÓN PRESIDENCIAL - FACTOR DE AJUSTE (CIEP-UCR)
# =============================================================================
@dataclass
class PresidentialApproval:
    """Datos de aprobación presidencial CIEP-UCR para calibración."""
    president: str
    term: str
    party: str
    approval_start: float  # % buena/muy buena al inicio (100 días o pico temprano)
    approval_end: float    # % buena/muy buena al final (última medición pre-elección)
    approval_delta: float  # Cambio en aprobación
    next_election_year: int
    continuist_candidate: str
    continuist_result_pct: float  # % primera ronda del candidato continuista
    continuist_won_first_round: bool
    notes: str = ""


PRESIDENTIAL_APPROVAL_DATA: List[PresidentialApproval] = [
    PresidentialApproval(
        president="Laura Chinchilla",
        term="2010-2014",
        party="PLN",
        approval_start=65.0,  # "dos terceras partes" según CIEP
        approval_end=15.0,    # Abril 2013, una de las peores mediciones
        approval_delta=-50.0,
        next_election_year=2014,
        continuist_candidate="Johnny Araya (PLN)",
        continuist_result_pct=29.71,
        continuist_won_first_round=False,
        notes="Araya abandonó campaña antes de segunda ronda"
    ),
    PresidentialApproval(
        president="Luis Guillermo Solís",
        term="2014-2018",
        party="PAC",
        approval_start=35.7,  # 100 días, julio 2014
        approval_end=25.0,    # Marzo 2018
        approval_delta=-10.7,
        next_election_year=2018,
        continuist_candidate="Carlos Alvarado (PAC)",
        continuist_result_pct=21.66,
        continuist_won_first_round=False,
        notes="PAC ganó en segunda ronda (60.7%) gracias a coalición anti-Fabricio"
    ),
    PresidentialApproval(
        president="Carlos Alvarado",
        term="2018-2022",
        party="PAC",
        approval_start=66.0,  # Pico pandemia abril 2020
        approval_end=18.0,    # Marzo 2022
        approval_delta=-48.0,
        next_election_year=2022,
        continuist_candidate="Welmer Ramos (PAC)",
        continuist_result_pct=0.66,  # Colapso total del PAC
        continuist_won_first_round=False,
        notes="PAC colapsó; Chaves surgió como outsider"
    ),
    PresidentialApproval(
        president="Rodrigo Chaves",
        term="2022-2026",
        party="PPSD",
        approval_start=79.0,  # 100 días, agosto 2022 - récord histórico
        approval_end=52.0,    # Estimación enero 2026 (última CIEP ~52-58%)
        approval_delta=-27.0,
        next_election_year=2026,
        continuist_candidate="Laura Fernández (PPSD)",
        continuist_result_pct=43.8,  # Última encuesta CIEP
        continuist_won_first_round=None,  # Por determinar
        notes="Aprobación final 3-4x mayor que predecesores; situación atípica"
    ),
]


def analyze_presidential_approval_effect() -> Dict:
    """
    Analiza el efecto de la aprobación presidencial en el resultado del candidato continuista.
    
    Hipótesis: Mayor aprobación final → Mayor votación del candidato continuista
    """
    # Excluir 2026 (aún no hay resultado)
    historical = [p for p in PRESIDENTIAL_APPROVAL_DATA if p.next_election_year < 2026]
    
    approvals_end = [p.approval_end for p in historical]
    results = [p.continuist_result_pct for p in historical]
    deltas = [p.approval_delta for p in historical]
    
    # Correlaciones
    corr_approval_result = np.corrcoef(approvals_end, results)[0, 1] if len(approvals_end) > 1 else 0
    corr_delta_result = np.corrcoef(deltas, results)[0, 1] if len(deltas) > 1 else 0
    
    # Regresión simple: resultado = a + b * aprobación_final
    if len(approvals_end) > 1:
        slope, intercept = np.polyfit(approvals_end, results, 1)
    else:
        slope, intercept = 0, 0
    
    # Proyección para Chaves (52% aprobación)
    chaves = [p for p in PRESIDENTIAL_APPROVAL_DATA if p.next_election_year == 2026][0]
    projected_result = intercept + slope * chaves.approval_end
    
    # Umbral histórico: ¿qué aprobación mínima necesita para ganar en primera ronda?
    # Ningún presidente con aprobación < 30% tuvo candidato ganando en primera ronda
    
    return {
        'correlation_approval_result': float(corr_approval_result),
        'correlation_delta_result': float(corr_delta_result),
        'regression_slope': float(slope),
        'regression_intercept': float(intercept),
        'avg_approval_end_historical': float(np.mean(approvals_end)),
        'chaves_approval_end': float(chaves.approval_end),
        'chaves_approval_advantage': float(chaves.approval_end - np.mean(approvals_end)),
        'projected_result_from_approval': float(projected_result),
        'approval_is_outlier': chaves.approval_end > max(approvals_end) * 1.5,
        'historical_data': historical,
    }


def calculate_approval_adjustment(current_approval: float) -> Dict:
    """
    Calcula el ajuste al modelo basado en la aprobación presidencial.
    
    Chaves con ~52% es un caso atípico:
    - 3.5x mayor que Chinchilla (15%)
    - 2.9x mayor que Alvarado (18%)
    - 2.1x mayor que Solís (25%)
    
    Esto sugiere un "bonus" para Laura Fernández que el modelo base no captura.
    """
    analysis = analyze_presidential_approval_effect()
    
    # Comparar con promedio histórico
    avg_historical = analysis['avg_approval_end_historical']  # ~19.3%
    advantage_ratio = current_approval / avg_historical if avg_historical > 0 else 1.0
    
    # Ajustes según nivel de aprobación
    if current_approval >= 50:
        # Aprobación muy alta (caso Chaves): fuerte bonus
        # Nunca visto en era post-2010, situación excepcional
        approval_bonus_pp = 2.5  # Bonus de +2.5 pp a la proyección base
        uncertainty_reduction = 0.85  # Reduce incertidumbre (votantes más decididos)
        confidence_factor = 1.2  # Mayor confianza en que encuestas reflejan realidad
    elif current_approval >= 35:
        # Aprobación moderada-alta
        approval_bonus_pp = 1.0
        uncertainty_reduction = 0.95
        confidence_factor = 1.1
    elif current_approval >= 25:
        # Aprobación moderada (similar a Solís)
        approval_bonus_pp = 0.0
        uncertainty_reduction = 1.0
        confidence_factor = 1.0
    else:
        # Aprobación baja (Chinchilla, Alvarado)
        approval_bonus_pp = -1.5  # Penalización
        uncertainty_reduction = 1.1  # Mayor incertidumbre
        confidence_factor = 0.9
    
    return {
        'current_approval': current_approval,
        'historical_average': avg_historical,
        'advantage_ratio': advantage_ratio,
        'approval_bonus_pp': approval_bonus_pp,
        'uncertainty_reduction': uncertainty_reduction,
        'confidence_factor': confidence_factor,
        'analysis': analysis,
    }


# =============================================================================
# VICTORIAS EN PRIMERA RONDA - DATOS HISTÓRICOS TSE (1982-2010)
# =============================================================================
@dataclass
class FirstRoundVictory:
    """Datos de victorias en primera ronda para calibración de umbral efectivo."""
    year: int
    winner: str
    party: str
    pct_valid_votes: float
    deputies: int
    notes: str = ""


# Únicas victorias en primera ronda desde 1982 (fuente: TSE)
FIRST_ROUND_VICTORIES: List[FirstRoundVictory] = [
    FirstRoundVictory(1982, "Luis Alberto Monge", "PLN", 58.80, 33, "Bipartidismo fuerte"),
    FirstRoundVictory(1986, "Óscar Arias Sánchez", "PLN", 52.34, 29, "Bipartidismo fuerte"),
    FirstRoundVictory(1990, "Rafael Ángel Calderón Fournier", "PUSC", 47.03, 25, "Bipartidismo estable"),
    FirstRoundVictory(1994, "José María Figueres Olsen", "PLN", 49.62, 28, "Bipartidismo estable"),
    FirstRoundVictory(2010, "Laura Chinchilla Miranda", "PLN", 46.78, 24, "Inicio fragmentación"),
    # Nota: Arias 2006 (40.92%) también ganó en primera ronda, pero por margen mínimo
    # No incluido arriba porque fue reconteo extendido y resultado atípico
]

# Elecciones CON segunda ronda (no se alcanzó 40% o hubo fragmentación extrema)
SECOND_ROUND_ELECTIONS = [2002, 2014, 2018, 2022]  # 4 de las últimas 6 elecciones


def analyze_first_round_victories(victories: List[FirstRoundVictory]) -> Dict:
    """
    Analiza patrones históricos de victorias en primera ronda.
    
    Hallazgos clave:
    - Ningún ganador en 1ª ronda ha bajado de 46.78% (Chinchilla 2010)
    - Tendencia descendente en % de victoria (fragmentación creciente)
    - Correlación fuerte entre % votos y diputados obtenidos
    """
    pcts = [v.pct_valid_votes for v in victories]
    deps = [v.deputies for v in victories]
    years = [v.year for v in victories]
    
    # Tendencia temporal (regresión simple)
    years_norm = np.array(years) - min(years)
    pcts_arr = np.array(pcts)
    if len(years) > 1:
        slope = np.polyfit(years_norm, pcts_arr, 1)[0]
    else:
        slope = 0.0
    
    return {
        'min_pct': min(pcts),
        'max_pct': max(pcts),
        'mean_pct': np.mean(pcts),
        'median_pct': np.median(pcts),
        'std_pct': np.std(pcts),
        'trend_per_decade': slope * 10,  # Cambio por década
        'min_deputies': min(deps),
        'correlation_pct_deputies': np.corrcoef(pcts, deps)[0, 1],
        'years_since_last': 2026 - max(years),  # Años sin victoria en 1ª ronda
        'n_victories': len(victories),
        'n_second_rounds_recent': len(SECOND_ROUND_ELECTIONS),
    }


# Base de datos histórica CIEP-UCR vs TSE (primera ronda)
HISTORICAL_DATA: List[HistoricalElection] = [
    # 2022: Alta sorpresa - Chaves pasó de 3% en encuestas a 16.7% en resultado
    HistoricalElection(
        year=2022,
        election_date="2022-02-06",
        ciep_leader="José María Figueres (PLN)",
        ciep_leader_pct=17.0,
        ciep_second="Lineth Saborío (PUSC)",
        ciep_second_pct=12.9,
        ciep_undecided=41.0,
        ciep_date="2022-01-21",
        tse_first="José María Figueres (PLN)",
        tse_first_pct=27.26,
        tse_second="Rodrigo Chaves (PPSD)",
        tse_second_pct=16.70,
        notes="Chaves no aparecía en top 3 de encuestas; alta volatilidad"
    ),
    # 2018: Sorpresa moderada - Fabricio Alvarado subió de ~6% a 24.9%
    HistoricalElection(
        year=2018,
        election_date="2018-02-04",
        ciep_leader="Juan Diego Castro (PIN)",
        ciep_leader_pct=18.0,  # Diciembre 2017
        ciep_second="Antonio Álvarez Desanti (PLN)",
        ciep_second_pct=17.0,
        ciep_undecided=27.0,
        ciep_date="2018-01-15",  # Aprox
        tse_first="Fabricio Alvarado (RN)",
        tse_first_pct=24.91,
        tse_second="Carlos Alvarado (PAC)",
        tse_second_pct=21.66,
        notes="Efecto CIDH/matrimonio igualitario; Castro colapsó, F. Alvarado subió"
    ),
    # 2014: Sorpresa significativa - Solís pasó de ~11% a 30.6%
    HistoricalElection(
        year=2014,
        election_date="2014-02-02",
        ciep_leader="Johnny Araya (PLN)",
        ciep_leader_pct=17.4,
        ciep_second="José María Villalta (FA)",
        ciep_second_pct=14.4,
        ciep_undecided=30.0,  # Aprox según fuentes
        ciep_date="2014-01-29",
        tse_first="Luis Guillermo Solís (PAC)",
        tse_first_pct=30.64,
        tse_second="Johnny Araya (PLN)",
        tse_second_pct=29.71,
        notes="Solís tercero en encuestas; gran movilización última semana"
    ),
    # 2010: Victoria clara de Chinchilla en primera ronda
    HistoricalElection(
        year=2010,
        election_date="2010-02-07",
        ciep_leader="Laura Chinchilla (PLN)",
        ciep_leader_pct=38.0,  # Estimación
        ciep_second="Ottón Solís (PAC)",
        ciep_second_pct=22.0,
        ciep_undecided=25.0,
        ciep_date="2010-01-20",
        tse_first="Laura Chinchilla (PLN)",
        tse_first_pct=46.76,
        tse_second="Ottón Solís (PAC)",
        tse_second_pct=25.15,
        notes="Continuidad PLN; encuestas acertaron en ranking"
    ),
    # 2006: Elección muy reñida, Arias apenas pasa 40%
    HistoricalElection(
        year=2006,
        election_date="2006-02-05",
        ciep_leader="Óscar Arias (PLN)",
        ciep_leader_pct=35.0,  # Estimación conservadora
        ciep_second="Ottón Solís (PAC)",
        ciep_second_pct=28.0,
        ciep_undecided=22.0,
        ciep_date="2006-01-20",
        tse_first="Óscar Arias (PLN)",
        tse_first_pct=40.92,
        tse_second="Ottón Solís (PAC)",
        tse_second_pct=39.80,
        notes="Margen mínimo; recuento extendido"
    ),
]


# =============================================================================
# VICTORIAS EN PRIMERA RONDA - DATOS HISTÓRICOS TSE
# =============================================================================
@dataclass
class FirstRoundVictory:
    """Datos de victorias en primera ronda (≥40%) desde 1982."""
    year: int
    winner: str
    party: str
    pct_first_round: float
    deputies: int  # Diputados del partido ganador
    era: str  # 'bipartidismo' o 'fragmentacion'


FIRST_ROUND_VICTORIES: List[FirstRoundVictory] = [
    # Era bipartidista (PLN-PUSC dominante)
    FirstRoundVictory(1982, "Luis Alberto Monge", "PLN", 58.80, 33, "bipartidismo"),
    FirstRoundVictory(1986, "Óscar Arias Sánchez", "PLN", 52.34, 29, "bipartidismo"),
    FirstRoundVictory(1990, "Rafael Ángel Calderón Fournier", "PUSC", 47.03, 25, "bipartidismo"),
    FirstRoundVictory(1994, "José María Figueres Olsen", "PLN", 49.62, 28, "bipartidismo"),
    FirstRoundVictory(1998, "Miguel Ángel Rodríguez", "PUSC", 46.96, 27, "bipartidismo"),
    # Transición (inicio de fragmentación)
    FirstRoundVictory(2006, "Óscar Arias Sánchez", "PLN", 40.92, 25, "transicion"),
    FirstRoundVictory(2010, "Laura Chinchilla Miranda", "PLN", 46.78, 24, "transicion"),
    # Era fragmentada: NO HAY VICTORIAS EN PRIMERA RONDA (2002, 2014, 2018, 2022)
]

# Elecciones SIN victoria en primera ronda (requirieron segunda vuelta)
SECOND_ROUND_ELECTIONS = [
    {"year": 2002, "first_pct": 38.58, "winner_first": "Abel Pacheco", "era": "transicion"},
    {"year": 2014, "first_pct": 30.64, "winner_first": "Luis Guillermo Solís", "era": "fragmentacion"},
    {"year": 2018, "first_pct": 24.91, "winner_first": "Fabricio Alvarado", "era": "fragmentacion"},
    {"year": 2022, "first_pct": 27.26, "winner_first": "José María Figueres", "era": "fragmentacion"},
]


def analyze_first_round_victories(victories: List[FirstRoundVictory]) -> Dict:
    """
    Analiza patrones históricos de victorias en primera ronda.
    
    Identifica:
    - Tendencia temporal del % ganador
    - Diferencias por era (bipartidismo vs fragmentación)
    - "Techo" realista para 2026
    """
    df = pd.DataFrame([{
        'year': v.year,
        'winner': v.winner,
        'party': v.party,
        'pct': v.pct_first_round,
        'deputies': v.deputies,
        'era': v.era,
    } for v in victories])
    
    # Estadísticas por era
    bipartidismo = df[df['era'] == 'bipartidismo']
    transicion = df[df['era'] == 'transicion']
    
    # Regresión temporal: tendencia decreciente
    years = df['year'].values.astype(float)
    pcts = df['pct'].values.astype(float)
    
    # Ajuste lineal simple
    slope = np.polyfit(years, pcts, 1)[0]
    
    # Proyección para 2026 (extrapolación de tendencia)
    projected_ceiling_2026 = np.polyval(np.polyfit(years, pcts, 1), 2026)
    
    # Correlación diputados ↔ % presidencial
    corr_deputies = df['deputies'].corr(df['pct'])
    
    return {
        'df': df,
        'avg_pct_bipartidismo': float(bipartidismo['pct'].mean()),
        'avg_pct_transicion': float(transicion['pct'].mean()),
        'min_victory_pct': float(df['pct'].min()),  # 40.92% (Arias 2006)
        'max_victory_pct': float(df['pct'].max()),  # 58.80% (Monge 1982)
        'last_victory_pct': float(df[df['year'] == df['year'].max()]['pct'].iloc[0]),
        'last_victory_year': int(df['year'].max()),
        'trend_slope_per_year': float(slope),  # Caída anual en pp
        'projected_ceiling_2026': float(np.clip(projected_ceiling_2026, 40, 55)),
        'corr_deputies_pct': float(corr_deputies),
        'years_since_last_victory': 2026 - int(df['year'].max()),
        'consecutive_second_rounds': 3,  # 2014, 2018, 2022
    }


def estimate_era_adjustment(current_year: int = 2026) -> Dict:
    """
    Estima ajustes según la era electoral actual.
    
    Era fragmentada (post-2002):
    - Mayor volatilidad
    - Menor probabilidad de alcanzar 40%
    - Candidatos "sorpresa" más frecuentes
    
    NOTA: El ajuste de techo NO debe aplicarse mecánicamente si el
    candidato ya supera el umbral en encuestas. Solo aumentamos incertidumbre.
    """
    # Desde 2014: 0 de 3 elecciones con victoria en primera ronda
    # Desde 2002: 2 de 6 elecciones con victoria en primera ronda (33%)
    
    if current_year >= 2014:
        era = "fragmentacion_extrema"
        base_prob_first_round = 0.33  # Histórico 2002-2022
        volatility_factor = 1.25  # Reducido de 1.4 - ya tenemos incertidumbre en otras partes
        ceiling_adjustment = 0.0  # NO reducir base si candidato ya supera 40%
    elif current_year >= 2002:
        era = "transicion"
        base_prob_first_round = 0.50
        volatility_factor = 1.15
        ceiling_adjustment = 0.0
    else:
        era = "bipartidismo"
        base_prob_first_round = 0.80
        volatility_factor = 1.0
        ceiling_adjustment = 0.0
    
    return {
        'era': era,
        'base_prob_first_round_victory': base_prob_first_round,
        'volatility_factor': volatility_factor,
        'ceiling_adjustment_pp': ceiling_adjustment,
        'years_without_first_round_victory': 16 if current_year == 2026 else 0,
    }


def analyze_historical_errors(data: List[HistoricalElection]) -> Dict:
    """
    Analiza errores históricos encuesta CIEP vs resultado TSE.
    
    Calcula:
    - Error promedio del líder en encuestas
    - Correlación indecisión → error
    - Dirección típica del sesgo
    """
    errors = []
    
    for h in data:
        # Error del líder en encuesta vs su resultado TSE
        if h.ciep_leader.split('(')[0].strip() == h.tse_first.split('(')[0].strip():
            # Líder en encuesta quedó primero
            error_leader = h.tse_first_pct - h.ciep_leader_pct
            leader_won = True
        else:
            # Líder en encuesta NO quedó primero (sorpresa)
            # Buscar cuánto sacó realmente el líder de encuestas
            # Asumimos quedó segundo si TSE second tiene mismo nombre
            if h.ciep_leader.split('(')[0].strip() == h.tse_second.split('(')[0].strip():
                error_leader = h.tse_second_pct - h.ciep_leader_pct
            else:
                # Líder de encuestas cayó a tercero o más (ej: Castro 2018)
                error_leader = -h.ciep_leader_pct  # Aproximación: perdió todo
            leader_won = False
        
        errors.append({
            'year': h.year,
            'undecided': h.ciep_undecided,
            'leader_error': error_leader,
            'leader_won': leader_won,
            'surprise': not leader_won,
            'tse_first_pct': h.tse_first_pct,
            'ciep_leader_pct': h.ciep_leader_pct,
        })
    
    df = pd.DataFrame(errors)
    
    # Análisis de correlación indecisión → error
    correlation = df['undecided'].corr(df['leader_error'].abs())
    
    # Error promedio según nivel de indecisión
    high_undecided = df[df['undecided'] > 30]
    low_undecided = df[df['undecided'] <= 30]
    
    return {
        'df': df,
        'avg_leader_error': float(df['leader_error'].mean()),
        'std_leader_error': float(df['leader_error'].std()),
        'avg_abs_error': float(df['leader_error'].abs().mean()),
        'surprise_rate': float(df['surprise'].mean()),
        'correlation_undecided_error': correlation,
        'avg_error_high_undecided': float(high_undecided['leader_error'].abs().mean()) if len(high_undecided) > 0 else np.nan,
        'avg_error_low_undecided': float(low_undecided['leader_error'].abs().mean()) if len(low_undecided) > 0 else np.nan,
        'elections_analyzed': len(df),
    }


def estimate_calibration_factor(
    current_undecided: float, 
    analysis: Dict,
    current_presidential_approval: float = 52.0  # Chaves enero 2026
) -> Dict:
    """
    Estima factores de calibración para el modelo actual basándose en datos históricos.
    
    Args:
        current_undecided: % de indecisos en la última encuesta actual
        analysis: Resultado de analyze_historical_errors()
        current_presidential_approval: Aprobación actual del presidente (% buena/muy buena)
    
    Returns:
        Dict con factores de ajuste
    """
    # Base: error esperado según nivel de indecisión
    if current_undecided > 35:
        expected_error = analysis['avg_error_high_undecided']
        surprise_probability = 0.6
        uncertainty_multiplier = 1.3
    elif current_undecided > 25:
        expected_error = analysis['avg_abs_error']
        surprise_probability = 0.4
        uncertainty_multiplier = 1.1
    else:
        expected_error = analysis.get('avg_error_low_undecided', 5.0)
        if np.isnan(expected_error):
            expected_error = 5.0
        surprise_probability = 0.2
        uncertainty_multiplier = 0.9
    
    bias_direction = 1.0 if current_undecided < 30 else -0.5
    
    # Análisis de victorias en primera ronda
    victory_analysis = analyze_first_round_victories(FIRST_ROUND_VICTORIES)
    era_adjustment = estimate_era_adjustment(2026)
    
    # NUEVO: Factor de aprobación presidencial
    approval_adjustment = calculate_approval_adjustment(current_presidential_approval)
    
    # La alta aprobación de Chaves reduce la probabilidad de sorpresa
    # y añade un bonus al candidato continuista
    adjusted_surprise_prob = surprise_probability * (1 - approval_adjustment['confidence_factor'] + 1)
    adjusted_surprise_prob = np.clip(adjusted_surprise_prob, 0.1, 0.6)
    
    return {
        'expected_error_pp': expected_error,
        'surprise_probability': float(adjusted_surprise_prob),
        'uncertainty_multiplier': uncertainty_multiplier,
        'bias_direction': bias_direction,
        'current_undecided': current_undecided,
        # Factores de victorias históricas
        'victory_analysis': victory_analysis,
        'era_adjustment': era_adjustment,
        'historical_ceiling_2026': victory_analysis['projected_ceiling_2026'],
        'years_since_first_round_victory': victory_analysis['years_since_last_victory'],
        # NUEVO: Factores de aprobación presidencial
        'approval_adjustment': approval_adjustment,
        'approval_bonus_pp': approval_adjustment['approval_bonus_pp'],
        'approval_uncertainty_factor': approval_adjustment['uncertainty_reduction'],
    }


def print_calibration_report(analysis: Dict, calibration: Dict) -> None:
    """Imprime reporte de calibración histórica."""
    print("\n" + "="*80)
    print("📊 CALIBRACIÓN HISTÓRICA - CIEP-UCR vs TSE (Primera Ronda)")
    print("="*80)
    
    print(f"\nElecciones analizadas: {analysis['elections_analyzed']} (2006-2022)")
    print(f"Fuente encuestas: CIEP-UCR (última dentro de 2 meses)")
    print(f"Fuente resultados: TSE Costa Rica")
    
    print("\n" + "─"*80)
    print("📈 ANÁLISIS DE ERRORES HISTÓRICOS (Encuesta → Resultado)")
    print("─"*80)
    
    df = analysis['df']
    print(f"\n  {'Año':<6} {'Indec.':<8} {'Error líder':<12} {'Sorpresa':<10} {'Resultado 1º':<12}")
    print("  " + "-"*56)
    for _, row in df.iterrows():
        sorpresa = "SÍ" if row['surprise'] else "No"
        print(f"  {int(row['year']):<6} {row['undecided']:.0f}%{'':<4} {row['leader_error']:+.1f} pp{'':<4} {sorpresa:<10} {row['tse_first_pct']:.1f}%")
    
    print("\n" + "─"*80)
    print("📉 ESTADÍSTICAS DE ERROR")
    print("─"*80)
    print(f"\n  • Error promedio del líder: {analysis['avg_leader_error']:+.1f} pp")
    print(f"  • Error absoluto promedio: {analysis['avg_abs_error']:.1f} pp")
    print(f"  • Desv. estándar del error: {analysis['std_leader_error']:.1f} pp")
    print(f"  • Tasa de sorpresas: {analysis['surprise_rate']*100:.0f}%")
    print(f"  • Correlación indecisión↔error: {analysis['correlation_undecided_error']:.2f}")
    
    if not np.isnan(analysis['avg_error_high_undecided']):
        print(f"\n  • Error (indec. >30%): {analysis['avg_error_high_undecided']:.1f} pp")
    if not np.isnan(analysis['avg_error_low_undecided']):
        print(f"  • Error (indec. ≤30%): {analysis['avg_error_low_undecided']:.1f} pp")
    
    # NUEVO: Sección de victorias en primera ronda
    print("\n" + "─"*80)
    print("🏆 VICTORIAS EN PRIMERA RONDA (≥40%) - HISTORIA TSE")
    print("─"*80)
    
    va = calibration.get('victory_analysis', {})
    era = calibration.get('era_adjustment', {})
    
    if va:
        print(f"\n  Victorias desde 1982: {len(FIRST_ROUND_VICTORIES)}")
        print(f"  Última victoria 1ª ronda: {va.get('last_victory_year', 'N/A')} ({va.get('last_victory_pct', 0):.1f}%)")
        print(f"  Años sin victoria 1ª ronda: {va.get('years_since_last_victory', 0)} (desde 2010)")
        print(f"  Segundas rondas consecutivas: {va.get('consecutive_second_rounds', 0)} (2014, 2018, 2022)")
        
        print(f"\n  Tendencia histórica:")
        print(f"    • Promedio era bipartidismo (1982-1998): {va.get('avg_pct_bipartidismo', 0):.1f}%")
        print(f"    • Promedio era transición (2006-2010): {va.get('avg_pct_transicion', 0):.1f}%")
        print(f"    • Caída por año: {va.get('trend_slope_per_year', 0):.2f} pp")
        print(f"    • Techo proyectado 2026: {va.get('projected_ceiling_2026', 0):.1f}%")
        print(f"    • Mínima victoria histórica: {va.get('min_victory_pct', 0):.1f}% (Arias 2006)")
    
    if era:
        print(f"\n  Era actual: {era.get('era', 'N/A').upper()}")
        print(f"    • Prob. base victoria 1ª ronda (histórica): {era.get('base_prob_first_round_victory', 0)*100:.0f}%")
        print(f"    • Factor de volatilidad: {era.get('volatility_factor', 1.0):.2f}")
        print(f"    • Ajuste de techo: {era.get('ceiling_adjustment_pp', 0):+.1f} pp")
    
    print("\n" + "─"*80)
    print("🎯 FACTORES DE CALIBRACIÓN PARA 2026")
    print("─"*80)
    print(f"\n  Indecisos actuales: {calibration['current_undecided']:.1f}%")
    print(f"  • Error esperado: ±{calibration['expected_error_pp']:.1f} pp")
    print(f"  • Probabilidad de sorpresa: {calibration['surprise_probability']*100:.0f}%")
    print(f"  • Multiplicador de incertidumbre: {calibration['uncertainty_multiplier']:.2f}")
    print(f"  • Dirección del sesgo: {'Favorable al líder' if calibration['bias_direction'] > 0 else 'Cautela'}")
    
    # NUEVO: Sección de aprobación presidencial
    print("\n" + "─"*80)
    print("👑 APROBACIÓN PRESIDENCIAL - EFECTO CONTINUISTA (CIEP-UCR)")
    print("─"*80)
    
    aa = calibration.get('approval_adjustment', {})
    if aa:
        print(f"\n  {'Presidente':<18} {'Aprob. inicio':<14} {'Aprob. final':<14} {'Δ':<8} {'Continuista R1':<16}")
        print("  " + "-"*70)
        
        for p in PRESIDENTIAL_APPROVAL_DATA:
            delta = p.approval_delta
            if p.continuist_result_pct is not None:
                result = f"{p.continuist_result_pct:.1f}%"
            else:
                result = "Pendiente"
            print(f"  {p.president:<18} {p.approval_start:>6.0f}%{'':<6} {p.approval_end:>6.0f}%{'':<6} {delta:>+.0f}pp{'':<2} {result:<16}")
        
        analysis_aa = aa.get('analysis', {})
        print(f"\n  Análisis estadístico:")
        print(f"    • Correlación aprobación final → resultado: {analysis_aa.get('correlation_approval_result', 0):.2f}")
        print(f"    • Promedio histórico aprobación final: {aa.get('historical_average', 0):.1f}%")
        
        print(f"\n  ⭐ Situación Chaves 2026 (ATÍPICA):")
        print(f"    • Aprobación actual: {aa.get('current_approval', 0):.0f}%")
        print(f"    • Ratio vs promedio histórico: {aa.get('advantage_ratio', 1):.1f}x")
        print(f"    • Bonus estimado para Laura: {aa.get('approval_bonus_pp', 0):+.1f} pp")
        print(f"    • Factor de reducción incertidumbre: {aa.get('uncertainty_reduction', 1):.2f}")
        
        print(f"\n  💡 Interpretación:")
        print(f"    • Chaves termina con aprobación ~3x mayor que cualquier predecesor")
        print(f"    • Históricamente, baja aprobación = colapso del candidato continuista")
        print(f"    • Alta aprobación de Chaves favorece significativamente a Laura")


# =============================================================================
# DATOS DE ENCUESTAS 2026 (Actualizados al 28 de enero)
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
    
    # NUEVA: CIEP-UCR 28-ene-2026 (última encuesta)
    Poll("ciep_ucr_4", "CIEP-UCR", "2026-01-28", "abierta", 2.5,
         {"INDECISOS": 25.9, 
          "LAURA FERNÁNDEZ": 43.8, 
          "ÁLVARO RAMOS": 9.2,
          "CLAUDIA DOBLES": 8.6,
          "JOSÉ AGUILAR": 2.8,
          "JUAN CARLOS HIDALGO": 2.5,
          "FABRICIO ALVARADO": 1.5,
          "ARIEL ROBLES": 1.8,
          "OTROS": 1.9,
          "NULO/BLANCO": 2.0},
         n_eff=1501.0),
]

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
# FUNCIONES DE PROCESAMIENTO DE ENCUESTAS
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
    
    df["n_eff"] = df["n_eff_override"]
    missing = df["n_eff"].isna()
    df.loc[missing, "n_eff"] = 0.25 * (1.96 * 100.0 / df.loc[missing, "moe"]) ** 2

    for c in ["INDECISOS", "NO RESPONDE", "NULO/BLANCO"] + CANDIDATES:
        if c not in df.columns:
            df[c] = np.nan

    df["NO RESPONDE"] = df["NO RESPONDE"].fillna(0.0)
    df["NULO/BLANCO"] = df["NULO/BLANCO"].fillna(df["NULO/BLANCO"].median())
    df["U"] = (df["INDECISOS"].fillna(0.0) + df["NO RESPONDE"]).clip(0, 95)
    df["B"] = df["NULO/BLANCO"].clip(0, 20)
    df["DECIDED_TOTAL"] = (100.0 - df["U"] - df["B"]).clip(1e-6)

    for c in CANDIDATES:
        df[c] = df[c].fillna(0.0)

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


def aggregate_polls(df: pd.DataFrame, weights: np.ndarray) -> Dict:
    """Agrega encuestas ponderadamente."""
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

    estimates: Dict[str, float] = {}
    for c in CANDIDATES:
        if c in df_main.columns:
            estimates[c] = float(np.average(df_main[c].values.astype(float), weights=w_norm))
        else:
            estimates[c] = 0.0

    estimates["U"] = float(np.average(df_main["U"].values.astype(float), weights=w_norm))
    estimates["B"] = float(np.average(df_main["B"].values.astype(float), weights=w_norm))

    return {
        "estimates": estimates,
        "lf_projected": float(np.clip(lf_projected, 25, 55)),
        "lf_trend": float(beta[1]),
        "rmse": rmse,
        "n_polls": int(len(df_main)),
        "last_date": df_main["publish_date"].max(),
    }


# =============================================================================
# SIMULACIÓN MONTE CARLO CON CALIBRACIÓN
# =============================================================================
def run_simulation_calibrated(
    n_sims: int = N_SIMS, 
    seed: int = SEED,
    use_calibration: bool = True
) -> Dict:
    """
    Simulación Monte Carlo con calibración histórica.
    
    La calibración ajusta la incertidumbre del modelo basándose en:
    1. Error histórico encuestas CIEP-UCR vs resultados TSE
    2. Patrones de victorias en primera ronda (tendencia decreciente)
    3. Era electoral actual (fragmentación extrema desde 2014)
    """
    print("\n" + "="*80)
    print("🎲 SIMULACIÓN MONTE CARLO - COSTA RICA 2026 - V3.3 CALIBRADA")
    print(f"   Actualización: {UPDATE_DATE}")
    print(f"   Incluye: errores históricos + victorias 1ª ronda + aprobación presidencial")
    print("="*80)
    
    # Procesar encuestas
    df = polls_to_frame(POLLS)
    weights = compute_weights(df)
    agg = aggregate_polls(df, weights)
    
    # Última encuesta
    last_poll = df.iloc[-1]
    lf_base = float(last_poll["LAURA FERNÁNDEZ"])
    current_undecided = float(last_poll["INDECISOS"])
    
    print(f"\nEncuestas disponibles: {len(df)}")
    print(f"Última encuesta: CIEP-UCR {last_poll['publish_date'].date()}")
    print(f"Laura Fernández (última): {lf_base:.1f}%")
    print(f"Indecisos (última): {current_undecided:.1f}%")
    
    # Análisis de calibración histórica
    historical_analysis = analyze_historical_errors(HISTORICAL_DATA)
    calibration = estimate_calibration_factor(current_undecided, historical_analysis)
    
    if use_calibration:
        print_calibration_report(historical_analysis, calibration)
    
    # Extraer ajustes por era y victoria histórica
    era_adj = calibration.get('era_adjustment', {})
    victory_adj = calibration.get('victory_analysis', {})
    
    # Calcular incertidumbre total
    se_lf = float(last_poll["moe"] / 1.96)
    trend_uncertainty = float(agg["rmse"])
    
    # Ajuste por calibración histórica Y por era electoral
    if use_calibration:
        sigma_systematic = 1.2 * calibration['uncertainty_multiplier']
        # Añadir volatilidad por era fragmentada
        sigma_systematic *= era_adj.get('volatility_factor', 1.0)
        # NUEVO: Reducir si aprobación presidencial es alta (votantes más decididos)
        sigma_systematic *= calibration.get('approval_uncertainty_factor', 1.0)
        historical_error = calibration['expected_error_pp']
        approval_bonus = calibration.get('approval_bonus_pp', 0)
    else:
        sigma_systematic = 1.5
        historical_error = 0.0
        approval_bonus = 0.0
    
    total_se = float(np.sqrt(se_lf**2 + trend_uncertainty**2 + sigma_systematic**2))
    
    print(f"\n⏳ Generando {n_sims:,} simulaciones...")
    print(f"  SE muestral: {se_lf:.2f}%")
    print(f"  SE tendencia: {trend_uncertainty:.2f}%")
    print(f"  SE sistemático (calibrado + era + aprob.): {sigma_systematic:.2f}%")
    print(f"  SE total: {total_se:.2f}%")
    
    if use_calibration:
        print(f"  Techo histórico proyectado: {victory_adj.get('projected_ceiling_2026', 50):.1f}%")
        print(f"  Era electoral: {era_adj.get('era', 'N/A')}")
        print(f"  Bonus por aprobación presidencial: {approval_bonus:+.1f} pp")
    
    rng = np.random.default_rng(seed)
    
    # Ajuste base según tendencia
    days_remaining = 3
    trend_adjustment = agg['lf_trend'] * days_remaining * 0.5
    lf_base_adjusted = lf_base + trend_adjustment
    
    # NUEVO: Aplicar ajuste por era (más conservador en era fragmentada)
    if use_calibration:
        ceiling_adj = era_adj.get('ceiling_adjustment_pp', 0)
        lf_base_adjusted += ceiling_adj
        
        # NUEVO: Aplicar bonus por alta aprobación presidencial de Chaves
        approval_bonus = calibration.get('approval_bonus_pp', 0)
        lf_base_adjusted += approval_bonus
        
        # Reducir incertidumbre si aprobación es alta (votantes más decididos)
        approval_uncertainty = calibration.get('approval_uncertainty_factor', 1.0)
    else:
        approval_uncertainty = 1.0
    
    lf_base_adjusted = np.clip(lf_base_adjusted, 38, 52)
    
    # Incorporar posibilidad de sorpresa (calibración histórica)
    if use_calibration:
        # En algunas simulaciones, aplicar escenario de sorpresa
        # Ajustar según probabilidad base de la era
        era_prob = era_adj.get('base_prob_first_round_victory', 0.5)
        surprise_prob = calibration['surprise_probability'] * (1 - era_prob + 0.3)
        n_surprise = int(n_sims * surprise_prob * 0.4)
        n_normal = n_sims - n_surprise
        
        # Simulaciones normales
        lf_sims_normal = rng.normal(lf_base_adjusted, total_se, size=n_normal)
        
        # Simulaciones de sorpresa (mayor incertidumbre, sesgo según historia)
        # En era fragmentada: sesgo hacia abajo (no se alcanza el 40%)
        surprise_se = total_se * 1.6
        surprise_bias = -historical_error * 0.6  # Sesgo negativo más fuerte
        lf_sims_surprise = rng.normal(lf_base_adjusted + surprise_bias, surprise_se, size=n_surprise)
        
        lf_sims = np.concatenate([lf_sims_normal, lf_sims_surprise])
        rng.shuffle(lf_sims)
    else:
        lf_sims = rng.normal(lf_base_adjusted, total_se, size=n_sims)
    
    # Ajuste por tipología de votantes
    tipo_elector = rng.choice(
        ['habitual', 'ocasional_vota', 'ocasional_abstiene', 'abstiene'],
        size=n_sims,
        p=[0.31, 0.30, 0.15, 0.24]
    )
    
    ajuste = np.zeros(n_sims)
    m = (tipo_elector == 'ocasional_vota')
    ajuste[m] = rng.normal(0.3, 0.2, size=m.sum())
    m = (tipo_elector == 'ocasional_abstiene')
    ajuste[m] = rng.normal(-0.3, 0.2, size=m.sum())
    m = (tipo_elector == 'abstiene')
    ajuste[m] = rng.normal(-0.5, 0.3, size=m.sum())
    
    sims = pd.DataFrame(index=np.arange(n_sims))
    sims["LAURA FERNÁNDEZ"] = (lf_sims + ajuste).clip(28, 55)
    
    # Indecisos
    sims["U"] = rng.normal(current_undecided, 3.0, size=n_sims).clip(15, 40)
    
    # Blancos/nulos
    sims["B"] = rng.normal(2.0, 0.8, size=n_sims).clip(0, 6)
    
    # Otros candidatos
    estimates = agg["estimates"]
    for c in CANDIDATES:
        if c == "LAURA FERNÁNDEZ":
            continue
        base = float(last_poll.get(c, estimates.get(c, 0.0)))
        if base == 0:
            base = float(estimates.get(c, 1.0))
        sd = max(1.0, base * 0.2)
        sims[c] = rng.normal(base, sd, size=n_sims).clip(0.2, 20)
    
    # Resto y normalización
    others_cols = [c for c in CANDIDATES if c != "LAURA FERNÁNDEZ"]
    decided = 100.0 - sims["U"] - sims["B"]
    sims["RESTO"] = (decided - sims["LAURA FERNÁNDEZ"] - sims[others_cols].sum(axis=1)).clip(0, 20)
    
    all_cols = ["LAURA FERNÁNDEZ"] + others_cols + ["RESTO", "U", "B"]
    total = sims[all_cols].sum(axis=1)
    for col in all_cols:
        sims[col] = 100.0 * sims[col] / total
    
    # Variables de resultado
    sims["LF"] = sims["LAURA FERNÁNDEZ"]
    sims["wins_round1"] = sims["LF"] >= 40.0
    
    # Top 1 y 2
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
        "current_undecided": current_undecided,
        "historical_analysis": historical_analysis,
        "calibration": calibration,
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
            "calibration_used": use_calibration,
            "era": era_adj.get('era', 'unknown'),
            "historical_ceiling": victory_adj.get('projected_ceiling_2026', 50),
        },
        "cand_summary": sims[cand_all].describe(percentiles=[0.05, 0.10, 0.50, 0.90, 0.95]).T,
        "top2_pairs": (sims.groupby(["top1", "top2"]).size() / n_sims).sort_values(ascending=False),
        "sims": sims,
        "polls_df": df,
    }
    return out
    return out


# =============================================================================
# VISUALIZACIÓN
# =============================================================================
def create_plots(out: Dict) -> None:
    sims = out["sims"]
    summ = out["summary"]
    cal = out.get("calibration", {})

    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    
    title = "SIMULACIÓN ELECTORAL COSTA RICA 2026 - v3.1 CALIBRADA\n"
    title += f"Actualización: {UPDATE_DATE} | CIEP-UCR: Laura {out['last_poll_lf']:.1f}% | "
    title += f"Indecisos: {out['current_undecided']:.1f}%"
    fig.suptitle(title, fontsize=13, fontweight="bold")

    # Panel 1: Distribución LF
    ax = axes[0, 0]
    ax.hist(sims["LF"], bins=80, alpha=0.7, edgecolor="black", color="#2E86AB")
    ax.axvline(40, color="red", linestyle="--", linewidth=2.5, label="Umbral 40%")
    ax.axvline(sims["LF"].mean(), color="darkblue", linestyle="-", linewidth=2,
               label=f"Media: {sims['LF'].mean():.1f}%")
    ax.axvspan(40, sims["LF"].max(), alpha=0.15, color='green')
    ax.set_xlabel("% del voto válido", fontsize=11)
    ax.set_ylabel("Frecuencia", fontsize=11)
    ax.set_title("Laura Fernández - Distribución (calibrada)", fontweight="bold")
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

    # Panel 3: Comparación histórica del error
    ax = axes[0, 2]
    hist_df = out["historical_analysis"]["df"]
    colors = ['#E74C3C' if s else '#27AE60' for s in hist_df['surprise']]
    bars = ax.bar(hist_df['year'].astype(str), hist_df['leader_error'].abs(), color=colors, alpha=0.7, edgecolor='black')
    ax.axhline(cal.get('expected_error_pp', 10), color='blue', linestyle='--', linewidth=2, 
               label=f"Error esperado 2026: {cal.get('expected_error_pp', 10):.1f} pp")
    ax.set_xlabel("Año electoral", fontsize=11)
    ax.set_ylabel("Error absoluto (pp)", fontsize=11)
    ax.set_title("Error histórico CIEP → TSE\n(rojo=sorpresa, verde=acertó)", fontweight="bold")
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Panel 4: Boxplots
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
    ax.axhline(40, color="red", linestyle="--", linewidth=2, alpha=0.7)
    ax.set_ylabel("% del voto válido", fontsize=11)
    ax.set_title("Distribución por candidato", fontweight="bold")
    ax.grid(axis='y', alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Panel 5: Escenarios
    ax = axes[1, 1]
    scenarios = ['P(≥40%)\nBase', 'P(≥40%)\nOptimista', 'P(≥40%)\nPesimista', 'P(≥40%)\nSorpresa']
    # Calcular escenarios
    p_base = summ['p_LF_win_round1'] * 100
    p_optimistic = float((sims["LF"] + 2).ge(40).mean()) * 100  # +2pp
    p_pessimistic = float((sims["LF"] - 3).ge(40).mean()) * 100  # -3pp
    p_surprise = float((sims["LF"] - 5).ge(40).mean()) * 100  # -5pp (sorpresa histórica)
    probs = [p_base, p_optimistic, p_pessimistic, p_surprise]
    colors_scen = ['#2E86AB', '#27AE60', '#F39C12', '#E74C3C']
    bars = ax.bar(scenarios, probs, color=colors_scen, alpha=0.7, edgecolor='black')
    ax.axhline(50, color='gray', linestyle=':', alpha=0.7)
    ax.set_ylabel("Probabilidad (%)", fontsize=11)
    ax.set_title("Análisis de escenarios\n(sensibilidad a sorpresas)", fontweight="bold")
    ax.set_ylim(0, 100)
    for bar, val in zip(bars, probs):
        ax.text(bar.get_x() + bar.get_width()/2, val + 2, f"{val:.0f}%", 
                ha='center', fontsize=10, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

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
    plt.savefig("simulacion_cr2026_v3_1_calibrated.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Visualización guardada: simulacion_cr2026_v3_1_calibrated.png")


# =============================================================================
# REPORTE
# =============================================================================
def print_report(out: Dict) -> None:
    print("\n" + "="*80)
    print("📊 REPORTE FINAL - SIMULACIÓN COSTA RICA 2026 (v3.1 CALIBRADA)")
    print(f"   Actualización: {UPDATE_DATE}")
    print("="*80)

    summ = out["summary"]
    cal = out["calibration"]

    print(f"\nSimulaciones: {summ['n_sims']:,}")
    print(f"Fecha elección: {summ['election_date']}")
    print(f"Última encuesta CIEP-UCR: Laura = {out['last_poll_lf']:.1f}%, Indecisos = {out['current_undecided']:.1f}%")
    print(f"Calibración histórica: {'Activada' if summ['calibration_used'] else 'Desactivada'}")
    
    print("\n" + "─"*80)
    print("🏆 LAURA FERNÁNDEZ - RESULTADO PROYECTADO")
    print("─"*80)
    print(f"\n  ✓ Probabilidad 1ª ronda (≥40%): {summ['p_LF_win_round1']*100:.1f}%")
    print(f"  ✓ Probabilidad 1º lugar:        {summ['p_LF_top1']*100:.1f}%")
    print(f"\n  • Media:     {summ['LF_mean']:.1f}%")
    print(f"  • Mediana:   {summ['LF_median']:.1f}%")
    print(f"  • IC 90%:    [{summ['LF_p5']:.1f}% - {summ['LF_p95']:.1f}%]")
    print(f"  • IC 80%:    [{summ['LF_p10']:.1f}% - {summ['LF_p90']:.1f}%]")
    
    print("\n" + "─"*80)
    print("⚠️  ANÁLISIS DE RIESGO (Basado en calibración histórica)")
    print("─"*80)
    print(f"\n  Error esperado según historia: ±{cal['expected_error_pp']:.1f} pp")
    print(f"  Probabilidad de sorpresa: {cal['surprise_probability']*100:.0f}%")
    
    # Escenarios
    sims = out["sims"]
    print("\n  Escenarios de sensibilidad:")
    print(f"    • Base:       P(≥40%) = {summ['p_LF_win_round1']*100:.1f}%")
    print(f"    • Optimista (+2pp): P(≥40%) = {(sims['LF'] + 2).ge(40).mean()*100:.1f}%")
    print(f"    • Pesimista (-3pp): P(≥40%) = {(sims['LF'] - 3).ge(40).mean()*100:.1f}%")
    print(f"    • Sorpresa hist. (-5pp): P(≥40%) = {(sims['LF'] - 5).ge(40).mean()*100:.1f}%")
    
    print("\n" + "─"*80)
    print("🎯 INTERPRETACIÓN CALIBRADA")
    print("─"*80)
    prob = summ['p_LF_win_round1'] * 100
    
    # Ajustar interpretación según riesgo histórico
    if prob >= 85 and cal['surprise_probability'] < 0.3:
        print(f"\n  🟢 VICTORIA EN PRIMERA RONDA: ALTAMENTE PROBABLE ({prob:.0f}%)")
        print("     Bajo riesgo histórico de sorpresa dado nivel reducido de indecisos.")
    elif prob >= 75:
        print(f"\n  🟢 VICTORIA EN PRIMERA RONDA: MUY PROBABLE ({prob:.0f}%)")
        print(f"     Precaución: historia muestra {cal['surprise_probability']*100:.0f}% de sorpresas")
        print("     en elecciones con niveles similares de indecisión.")
    elif prob >= 50:
        print(f"\n  🟡 VICTORIA EN PRIMERA RONDA: PROBABLE ({prob:.0f}%)")
        print("     Escenario competido; los indecisos pueden alterar el resultado.")
    else:
        print(f"\n  🔴 SEGUNDA RONDA PROBABLE (P1ª≈{prob:.0f}%)")
    
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
    # Ejecutar con calibración
    out = run_simulation_calibrated(n_sims=N_SIMS, seed=SEED, use_calibration=True)
    print_report(out)

    print("\n⏳ Guardando resultados...")
    out["sims"].to_csv("simulacion_cr2026_v3_1_calibrated.csv", index=False)
    out["cand_summary"].to_csv("resumen_candidatos_v3_1.csv")
    out["top2_pairs"].head(20).to_csv("top2_pairs_v3_1.csv")
    out["polls_df"].to_csv("encuestas_input_v3_1.csv", index=False)
    
    # Guardar análisis histórico
    out["historical_analysis"]["df"].to_csv("calibracion_historica.csv", index=False)

    create_plots(out)

    print("\n✅ SIMULACIÓN COMPLETADA (v3.1 con calibración histórica)")
    print("\nArchivos generados:")
    print("  • simulacion_cr2026_v3_1_calibrated.csv")
    print("  • resumen_candidatos_v3_1.csv")
    print("  • top2_pairs_v3_1.csv")
    print("  • encuestas_input_v3_1.csv")
    print("  • calibracion_historica.csv")
    print("  • simulacion_cr2026_v3_1_calibrated.png")


if __name__ == "__main__":
    main()
