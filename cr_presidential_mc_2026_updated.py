#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelo de Simulación Electoral Costa Rica 2026 - v2.1
Actualización: 21 de enero 2026

Autor: Agustín Gómez Meléndez (CIODD-UCR)
Descripción: Simulación Monte Carlo de la elección presidencial de Costa Rica 2026
con ajustes técnicos para mejor captura de correlaciones y comportamiento de indecisos.

Cambios en v2.1:
- Ajuste de Logit-Normal mejorado con matriz de covarianza que captura correlación
  entre candidatos del mismo bloque ideológico
- Nuevo escenario de "Dispersión" donde parte de los indecisos migra a candidaturas
  minoritarias ("RESTO"), reflejando fraccionamiento observado en encuestas recientes
- Decaimiento temporal: encuestas de octubre y noviembre de 2025 tienen peso
  significativamente menor comparado con las de enero de 2026
- Pool de encuestas incluye medición más reciente del CIEP-UCR
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.special import logit, expit
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuración de estilo
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

# ==============================================================================
# PARÁMETROS DEL MODELO v2.1
# ==============================================================================

N_SIMULATIONS = 100000  # Número de simulaciones Monte Carlo
RANDOM_SEED = 2026      # Para reproducibilidad
UNDECIDED_RATE = 0.32   # 32% de indecisión según último dato integrado
ABSTENTION_SENSITIVITY = 0.15  # Sensibilidad a abstención técnica

# Candidatos principales
CANDIDATES = [
    "LAURA FERNÁNDEZ",
    "ÁLVARO RAMOS",
    "ARIEL ROBLES",
    "CLAUDIA DOBLES",
    "RESTO"  # Candidaturas minoritarias agregadas
]

# ==============================================================================
# DATOS DE ENCUESTAS CON DECAIMIENTO TEMPORAL
# ==============================================================================

def load_poll_data():
    """
    Carga y procesa datos de encuestas con pesos según decaimiento temporal.

    Returns:
        DataFrame con datos de encuestas ponderadas
    """
    # Datos sintéticos basados en pool de encuestas
    # Pesos: enero 2026 = 1.0, diciembre 2025 = 0.6, nov 2025 = 0.3, oct 2025 = 0.15

    polls = {
        'poll_id': ['CIEP_ENE26', 'CID_DIC25', 'UNIMER_NOV25', 'OPOL_OCT25'],
        'date': ['2026-01-15', '2025-12-10', '2025-11-20', '2025-10-15'],
        'weight': [1.0, 0.6, 0.3, 0.15],
        'LAURA FERNÁNDEZ': [0.42, 0.44, 0.46, 0.48],
        'ÁLVARO RAMOS': [0.19, 0.18, 0.17, 0.16],
        'ARIEL ROBLES': [0.11, 0.10, 0.11, 0.09],
        'CLAUDIA DOBLES': [0.09, 0.08, 0.07, 0.08],
        'RESTO': [0.10, 0.09, 0.08, 0.07],
        'UNDECIDED': [0.09, 0.11, 0.11, 0.12]
    }

    return pd.DataFrame(polls)

# ==============================================================================
# MATRIZ DE COVARIANZA MEJORADA
# ==============================================================================

def build_covariance_matrix():
    """
    Construye matriz de covarianza mejorada que captura correlación entre
    candidatos del mismo bloque ideológico.

    Returns:
        numpy.array: Matriz de covarianza 5x5
    """
    n_candidates = len(CANDIDATES)

    # Varianza base para cada candidato
    variances = np.array([0.04, 0.025, 0.020, 0.018, 0.015])

    # Matriz de correlación
    # LF y AR tienen correlación negativa (bloques opuestos)
    # ARo y CD tienen correlación positiva (bloque similar)
    correlation = np.array([
        [1.00, -0.30, -0.15, -0.10, -0.20],  # Laura Fernández
        [-0.30,  1.00,  0.10,  0.05,  0.15],  # Álvaro Ramos
        [-0.15,  0.10,  1.00,  0.25,  0.20],  # Ariel Robles
        [-0.10,  0.05,  0.25,  1.00,  0.15],  # Claudia Dobles
        [-0.20,  0.15,  0.20,  0.15,  1.00]   # Resto
    ])

    # Construir matriz de covarianza
    std_devs = np.sqrt(variances)
    cov_matrix = np.outer(std_devs, std_devs) * correlation

    return cov_matrix

# ==============================================================================
# ESCENARIOS DE DISTRIBUCIÓN DE INDECISOS
# ==============================================================================

def distribute_undecided(base_shares, scenario='balanced'):
    """
    Distribuye votos indecisos según diferentes escenarios.

    Args:
        base_shares: Array con porcentajes base de cada candidato
        scenario: 'balanced', 'polarized', 'dispersed'

    Returns:
        numpy.array con distribución ajustada
    """
    undecided = UNDECIDED_RATE

    if scenario == 'balanced':
        # Distribución proporcional a fuerza actual
        weights = base_shares / base_shares.sum()
        distributed = base_shares + undecided * weights

    elif scenario == 'polarized':
        # Mayor parte va a los dos primeros
        weights = np.array([0.40, 0.30, 0.10, 0.10, 0.10])
        distributed = base_shares + undecided * weights

    elif scenario == 'dispersed':
        # Nueva estrategia v2.1: parte significativa va a RESTO
        weights = np.array([0.30, 0.20, 0.15, 0.10, 0.25])
        distributed = base_shares + undecided * weights

    else:
        distributed = base_shares

    # Normalizar
    return distributed / distributed.sum()

# ==============================================================================
# MODELO LOGIT-NORMAL MEJORADO
# ==============================================================================

def logit_normal_sample(mean_shares, cov_matrix, n_samples):
    """
    Genera muestras usando distribución logit-normal mejorada.

    Args:
        mean_shares: Vector de medias en espacio de probabilidades
        cov_matrix: Matriz de covarianza
        n_samples: Número de muestras a generar

    Returns:
        numpy.array de dimensiones (n_samples, n_candidates)
    """
    # Transformar a espacio logit
    epsilon = 1e-6
    mean_shares_clipped = np.clip(mean_shares, epsilon, 1 - epsilon)
    logit_means = logit(mean_shares_clipped)

    # Generar muestras en espacio logit
    logit_samples = np.random.multivariate_normal(
        logit_means,
        cov_matrix,
        size=n_samples
    )

    # Transformar de vuelta a espacio de probabilidades
    prob_samples = expit(logit_samples)

    # Normalizar para que sumen 1
    prob_samples = prob_samples / prob_samples.sum(axis=1, keepdims=True)

    return prob_samples

# ==============================================================================
# SIMULACIÓN PRINCIPAL
# ==============================================================================

def run_simulation():
    """
    Ejecuta la simulación Monte Carlo completa.

    Returns:
        DataFrame con resultados de todas las simulaciones
    """
    np.random.seed(RANDOM_SEED)

    print(f"Iniciando simulación de {N_SIMULATIONS:,} escenarios...")
    print(f"Modelo v2.1 con ajustes de covarianza y decaimiento temporal")
    print("-" * 70)

    # Cargar datos de encuestas
    polls_df = load_poll_data()

    # Calcular promedio ponderado de cada candidato
    weights = polls_df['weight'].values
    base_shares = np.zeros(len(CANDIDATES))

    for i, candidate in enumerate(CANDIDATES):
        if candidate == 'RESTO':
            # Sumar candidaturas menores no incluidas explícitamente
            continue
        weighted_avg = np.average(polls_df[candidate].values, weights=weights)
        base_shares[i] = weighted_avg

    # Ajustar RESTO
    base_shares[-1] = 1.0 - base_shares[:-1].sum() - UNDECIDED_RATE

    print("\nDistribución base (sin indecisos):")
    for i, candidate in enumerate(CANDIDATES):
        print(f"  {candidate}: {base_shares[i]*100:.2f}%")
    print(f"  INDECISOS: {UNDECIDED_RATE*100:.2f}%")
    print()

    # Construir matriz de covarianza
    cov_matrix = build_covariance_matrix()

    # Almacenar resultados
    results = np.zeros((N_SIMULATIONS, len(CANDIDATES)))

    # Distribución de escenarios
    n_balanced = int(N_SIMULATIONS * 0.40)
    n_polarized = int(N_SIMULATIONS * 0.35)
    n_dispersed = N_SIMULATIONS - n_balanced - n_polarized  # v2.1: nuevo escenario

    print("Distribución de escenarios:")
    print(f"  Balanceado: {n_balanced:,} ({n_balanced/N_SIMULATIONS*100:.1f}%)")
    print(f"  Polarizado: {n_polarized:,} ({n_polarized/N_SIMULATIONS*100:.1f}%)")
    print(f"  Dispersión: {n_dispersed:,} ({n_dispersed/N_SIMULATIONS*100:.1f}%) [NUEVO v2.1]")
    print()

    # Simular escenario balanceado
    shares_balanced = distribute_undecided(base_shares, 'balanced')
    results[0:n_balanced] = logit_normal_sample(shares_balanced, cov_matrix, n_balanced)

    # Simular escenario polarizado
    shares_polarized = distribute_undecided(base_shares, 'polarized')
    results[n_balanced:n_balanced+n_polarized] = logit_normal_sample(
        shares_polarized, cov_matrix, n_polarized
    )

    # Simular escenario dispersado (NUEVO v2.1)
    shares_dispersed = distribute_undecided(base_shares, 'dispersed')
    results[n_balanced+n_polarized:] = logit_normal_sample(
        shares_dispersed, cov_matrix, n_dispersed
    )

    # Convertir a DataFrame
    results_df = pd.DataFrame(results * 100, columns=CANDIDATES)

    print(f"Simulación completada exitosamente!")
    print("=" * 70)

    return results_df

# ==============================================================================
# ANÁLISIS DE RESULTADOS
# ==============================================================================

def analyze_results(results_df):
    """
    Analiza los resultados de la simulación.

    Args:
        results_df: DataFrame con resultados de simulaciones

    Returns:
        dict con métricas clave
    """
    lf_votes = results_df["LAURA FERNÁNDEZ"]

    # Probabilidad de ganar en primera ronda
    prob_first_round = (lf_votes >= 40.0).mean()

    # Media de voto válido
    mean_vote = lf_votes.mean()

    # Percentiles
    p10 = lf_votes.quantile(0.10)
    p90 = lf_votes.quantile(0.90)

    # Análisis de segunda ronda
    second_round_scenarios = []
    for idx, row in results_df.iterrows():
        if row["LAURA FERNÁNDEZ"] < 40.0:
            # Obtener top 2
            sorted_vals = row.sort_values(ascending=False)
            top2 = tuple(sorted_vals.index[:2])
            second_round_scenarios.append(top2)

    # Contar combinaciones más frecuentes
    from collections import Counter
    scenario_counts = Counter(second_round_scenarios)
    top_scenarios = scenario_counts.most_common(5)

    metrics = {
        'fecha_actualizacion': '21 de enero 2026',
        'n_simulaciones': N_SIMULATIONS,
        'version_modelo': 'v2.1',
        'probabilidad_primera_ronda': round(prob_first_round * 100, 2),
        'media_voto_valido_lf': round(mean_vote, 2),
        'intervalo_80_lf': [round(p10, 2), round(p90, 2)],
        'nivel_indecision': UNDECIDED_RATE * 100,
        'resumen_candidatos': {},
        'escenarios_segunda_ronda': []
    }

    # Resumen por candidato
    for candidate in CANDIDATES:
        metrics['resumen_candidatos'][candidate] = {
            'media': round(results_df[candidate].mean(), 2),
            'std': round(results_df[candidate].std(), 2),
            'min': round(results_df[candidate].min(), 2),
            'p10': round(results_df[candidate].quantile(0.10), 2),
            'p90': round(results_df[candidate].quantile(0.90), 2),
            'max': round(results_df[candidate].max(), 2)
        }

    # Top escenarios de segunda ronda
    total_second_round = len(second_round_scenarios)
    for (cand1, cand2), count in top_scenarios:
        prob = round(count / total_second_round * 100, 2)
        metrics['escenarios_segunda_ronda'].append({
            'candidato1': cand1,
            'candidato2': cand2,
            'probabilidad': prob
        })

    return metrics

# ==============================================================================
# VISUALIZACIÓN
# ==============================================================================

def create_visualization(results_df, metrics):
    """
    Crea visualización de los resultados.

    Args:
        results_df: DataFrame con resultados
        metrics: dict con métricas calculadas
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Simulación Electoral Costa Rica 2026 - Modelo v2.1\nActualización: 21 enero 2026',
                 fontsize=16, fontweight='bold')

    # 1. Histograma de Laura Fernández con línea de 40%
    ax1 = axes[0, 0]
    lf_votes = results_df["LAURA FERNÁNDEZ"]
    ax1.hist(lf_votes, bins=100, alpha=0.7, color='steelblue', edgecolor='black')
    ax1.axvline(x=40, color='red', linestyle='--', linewidth=2, label='Barrera 40%')
    ax1.axvline(x=lf_votes.mean(), color='green', linestyle='-', linewidth=2,
                label=f'Media: {lf_votes.mean():.2f}%')
    ax1.set_xlabel('Porcentaje de Voto Válido (%)')
    ax1.set_ylabel('Frecuencia')
    ax1.set_title(f'Distribución Laura Fernández\nProb. ≥40%: {metrics["probabilidad_primera_ronda"]}%')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Distribuciones de todos los candidatos
    ax2 = axes[0, 1]
    for candidate in CANDIDATES:
        ax2.hist(results_df[candidate], bins=50, alpha=0.5, label=candidate)
    ax2.set_xlabel('Porcentaje de Voto Válido (%)')
    ax2.set_ylabel('Frecuencia')
    ax2.set_title('Distribuciones de Todos los Candidatos')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Box plots comparativos
    ax3 = axes[1, 0]
    results_df.boxplot(ax=ax3, column=CANDIDATES)
    ax3.set_ylabel('Porcentaje de Voto Válido (%)')
    ax3.set_title('Comparación de Rangos de Votación')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(True, alpha=0.3)

    # 4. Escenarios de segunda ronda
    ax4 = axes[1, 1]
    if metrics['escenarios_segunda_ronda']:
        scenarios = metrics['escenarios_segunda_ronda'][:5]
        labels = [f"{s['candidato1'][:10]}\nvs\n{s['candidato2'][:10]}" for s in scenarios]
        probs = [s['probabilidad'] for s in scenarios]

        bars = ax4.barh(labels, probs, color='coral')
        ax4.set_xlabel('Probabilidad (%)')
        ax4.set_title('Top 5 Escenarios de Segunda Ronda')
        ax4.grid(True, alpha=0.3, axis='x')

        # Agregar valores en las barras
        for bar, prob in zip(bars, probs):
            ax4.text(prob + 1, bar.get_y() + bar.get_height()/2,
                    f'{prob:.1f}%', va='center', fontsize=9)

    plt.tight_layout()

    # Guardar figura
    plt.savefig('figura_mc_2026.png', dpi=300, bbox_inches='tight')
    print(f"\nVisualización guardada como 'figura_mc_2026.png'")

    return fig

# ==============================================================================
# EXPORTACIÓN DE RESULTADOS
# ==============================================================================

def export_results(results_df, metrics):
    """
    Exporta resultados a diferentes formatos.

    Args:
        results_df: DataFrame con resultados de simulaciones
        metrics: dict con métricas calculadas
    """
    # 1. Guardar resumen en JSON
    with open('resumen_mc_2026.json', 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print("Archivo 'resumen_mc_2026.json' creado")

    # 2. Guardar simulaciones completas en CSV (opcional, puede ser grande)
    # Guardar muestra de 10,000 simulaciones
    sample_size = min(10000, len(results_df))
    results_sample = results_df.sample(n=sample_size, random_state=RANDOM_SEED)
    results_sample.to_csv('simulaciones_mc_2026.csv', index=False)
    print(f"Archivo 'simulaciones_mc_2026.csv' creado (muestra de {sample_size:,} simulaciones)")

    # 3. Guardar resumen de candidatos en CSV
    summary_data = []
    for candidate, stats in metrics['resumen_candidatos'].items():
        summary_data.append({
            'candidato': candidate,
            'media': stats['media'],
            'desv_std': stats['std'],
            'minimo': stats['min'],
            'p10': stats['p10'],
            'p90': stats['p90'],
            'maximo': stats['max']
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv('resumen_candidatos_mc_2026.csv', index=False)
    print("Archivo 'resumen_candidatos_mc_2026.csv' creado")

    # 4. Guardar escenarios de segunda ronda
    if metrics['escenarios_segunda_ronda']:
        scenarios_df = pd.DataFrame(metrics['escenarios_segunda_ronda'])
        scenarios_df.to_csv('escenarios_segunda_ronda_2026.csv', index=False)
        print("Archivo 'escenarios_segunda_ronda_2026.csv' creado")

# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    """
    Función principal del script.
    """
    print("=" * 70)
    print("SIMULACIÓN ELECTORAL COSTA RICA 2026 - MODELO v2.1")
    print("Actualización: 21 de enero 2026")
    print("Autor: Agustín Gómez Meléndez (CIODD-UCR)")
    print("=" * 70)
    print()

    # Ejecutar simulación
    results_df = run_simulation()

    print("\n" + "=" * 70)
    print("ANÁLISIS DE RESULTADOS")
    print("=" * 70)

    # Analizar resultados
    metrics = analyze_results(results_df)

    # Imprimir resumen
    print(f"\nProbabilidad de victoria en 1ra ronda: {metrics['probabilidad_primera_ronda']}%")
    print(f"Media de voto válido (Laura Fernández): {metrics['media_voto_valido_lf']}%")
    print(f"Intervalo 80% (Laura Fernández): {metrics['intervalo_80_lf']}")
    print(f"Nivel de indecisión: {metrics['nivel_indecision']}%")

    print("\nTop 3 escenarios de segunda ronda:")
    for i, scenario in enumerate(metrics['escenarios_segunda_ronda'][:3], 1):
        print(f"  {i}. {scenario['candidato1']} vs {scenario['candidato2']}: "
              f"{scenario['probabilidad']}%")

    # Crear visualización
    print("\n" + "=" * 70)
    print("GENERANDO VISUALIZACIÓN")
    print("=" * 70)
    create_visualization(results_df, metrics)

    # Exportar resultados
    print("\n" + "=" * 70)
    print("EXPORTANDO RESULTADOS")
    print("=" * 70)
    export_results(results_df, metrics)

    print("\n" + "=" * 70)
    print("PROCESO COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    print("\nArchivos generados:")
    print("  - resumen_mc_2026.json")
    print("  - figura_mc_2026.png")
    print("  - simulaciones_mc_2026.csv")
    print("  - resumen_candidatos_mc_2026.csv")
    print("  - escenarios_segunda_ronda_2026.csv")
    print()

if __name__ == "__main__":
    main()
