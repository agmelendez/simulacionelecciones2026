# =============================================================================
# SISTEMA DE GESTIÓN Y ANÁLISIS ELECTORAL - COSTA RICA 2026
# Elección Presidencial - Primera Ronda
# Versión 2.0 - Con métricas de Ciencia Política y Estadística Electoral
# =============================================================================
# Autor: CIOdD - Universidad de Costa Rica
# Fecha: 2025
# =============================================================================

options(shiny.maxRequestSize = 250 * 1024^2)  # 250 MB

# -----------------------------------------------------------------------------
# CARGA DE PAQUETES
# -----------------------------------------------------------------------------
required_packages <- c(
  
  "shiny", "shinydashboard", "DT", "plotly", "dplyr", "tidyr",
  "readxl", "scales", "viridis", "ggplot2", "shinycssloaders",
  "bslib", "htmltools", "writexl", "purrr", "stringr", "lubridate",
  "RColorBrewer", "shinyWidgets", "ggrepel"
)

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
  library(pkg, character.only = TRUE)
}

# =============================================================================
# SECCIÓN 1: UTILIDADES GENERALES
# =============================================================================

`%||%` <- function(a, b) if (!is.null(a) && length(a) > 0 && !all(is.na(a))) a else b

normalize_name <- function(x) {
  x <- trimws(x)
  x <- tolower(x)
  x <- iconv(x, from = "", to = "ASCII//TRANSLIT")
  x <- gsub("[^a-z0-9]+", "_", x)
  x <- gsub("^_+|_+$", "", x)
  x
}

.na_posix <- function(n, tz) {
  as.POSIXct(rep(NA_real_, n), origin = "1970-01-01", tz = tz)
}

safe_posix <- function(x, tz = "America/Costa_Rica") {
  if (is.null(x)) return(.na_posix(1, tz))
  n0 <- length(x)
  if (is.list(x)) {
    x <- tryCatch(unlist(x, use.names = FALSE), error = function(e) rep(NA, n0))
  }
  x <- as.vector(x)
  n <- length(x)
  if (n == 0) return(.na_posix(0, tz))
  if (all(is.na(x))) return(.na_posix(n, tz))
  
  tryCatch({
    if (inherits(x, "POSIXct")) return(x)
    if (inherits(x, "POSIXlt")) return(as.POSIXct(x, tz = tz))
    if (inherits(x, "Date"))    return(as.POSIXct(x, tz = tz))
    if (inherits(x, "hms") || inherits(x, "difftime")) {
      secs <- as.numeric(x, units = "secs")
      return(as.POSIXct(secs, origin = "1970-01-01", tz = tz))
    }
    if (is.numeric(x)) {
      return(as.POSIXct(x * 86400, origin = "1899-12-30", tz = tz))
    }
    if (is.factor(x)) x <- as.character(x)
    if (!is.character(x)) x <- as.character(x)
    x2 <- trimws(x)
    out <- suppressWarnings(as.POSIXct(
      x2, tz = tz,
      tryFormats = c(
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
        "%Y-%m-%d", "%d/%m/%Y"
      )
    ))
    if (all(is.na(out)) && all(grepl("^[0-9.]+$", x2))) {
      xn <- suppressWarnings(as.numeric(x2))
      if (!all(is.na(xn))) {
        out <- as.POSIXct(xn * 86400, origin = "1899-12-30", tz = tz)
      }
    }
    if (length(out) != n) out <- .na_posix(n, tz)
    out
  }, error = function(e) {
    .na_posix(n, tz)
  })
}

ensure_columns <- function(df, cols, default = NA) {
  for (cc in cols) if (!cc %in% names(df)) df[[cc]] <- default
  df
}

# Mapeo canónico de nombres de columnas
canonical_map <- list(
  NUMEROCORTE = c("numerocorte", "numero_corte", "corte", "numcorte"),
  FECHAHORACORTE = c("fechahoracorte", "fecha_hora_corte", "fecha_hora_del_corte", "fechacorte", "hora_corte"),
  fechaHoraFinCaptura = c("fechahorafincaptura", "fecha_hora_fin_captura", "fechafin", "fecha_fin_captura"),
  provincia = c("provincia", "cod_provincia", "codigo_provincia"),
  descProvincia = c("descprovincia", "provincia_desc", "nombre_provincia", "desc_provincia"),
  canton = c("canton", "cod_canton", "codigo_canton"),
  descCanton = c("desccanton", "canton_desc", "nombre_canton", "desc_canton"),
  distritoAdmin = c("distritoadmin", "distrito_admin", "distrito", "cod_distrito", "codigo_distrito"),
  descDistritoAdmin = c("descdistritoadmin", "distrito_desc", "nombre_distrito", "desc_distrito_admin"),
  codPartido = c("codpartido", "codigo_partido", "partido_codigo"),
  descPartido = c("descpartido", "partido", "nombre_partido", "partido_desc"),
  votos = c("votos", "voto", "cantidad_votos"),
  junta = c("junta", "juntareceptora", "junta_receptora", "numjunta", "numero_junta"),
  electores = c("electores", "padron", "elector", "cantidad_electores"),
  total = c("total", "total_votos", "votos_emitidos", "votosemitidos"),
  vNulos = c("vnulos", "votos_nulos", "nulos"),
  vBlancos = c("vblancos", "votos_blancos", "blancos"),
  estado = c("estado", "estatus", "status"),
  medioTransmision = c("descripcion_del_medio_de_transmision", "medio_transmision", "mediotransmision")
)

rename_to_canonical <- function(df) {
  original <- names(df)
  norm <- vapply(original, normalize_name, character(1))
  for (canon in names(canonical_map)) {
    candidates <- canonical_map[[canon]]
    idx <- match(TRUE, norm %in% candidates, nomatch = 0)
    if (idx > 0) names(df)[idx] <- canon
  }
  df
}

# =============================================================================
# SECCIÓN 2: CARGA Y PROCESAMIENTO DE DATOS
# =============================================================================

load_electoral_data <- function(filepath, original_name = NULL, tz = "America/Costa_Rica") {
  ext <- tolower(tools::file_ext(original_name %||% filepath))
  
  if (ext %in% c("xlsx", "xls")) {
    df <- readxl::read_excel(filepath)
  } else if (ext == "csv") {
    df <- read.csv(filepath, stringsAsFactors = FALSE, check.names = FALSE, fileEncoding = "UTF-8")
  } else {
    stop("Extensión no soportada. Use .xlsx, .xls o .csv")
  }
  
  df <- as.data.frame(df, stringsAsFactors = FALSE)
  names(df) <- trimws(names(df))
  df <- rename_to_canonical(df)
  
  df <- ensure_columns(
    df,
    cols = c(
      "NUMEROCORTE", "FECHAHORACORTE", "fechaHoraFinCaptura",
      "provincia", "descProvincia", "canton", "descCanton",
      "distritoAdmin", "descDistritoAdmin",
      "codPartido", "descPartido", "votos",
      "junta", "electores", "total", "vNulos", "vBlancos",
      "estado", "medioTransmision"
    ),
    default = NA
  )
  
  # Conversiones de fecha fuera de mutate para evitar errores
  df$NUMEROCORTE <- suppressWarnings(as.integer(df$NUMEROCORTE))
  df$FECHAHORACORTE <- safe_posix(df$FECHAHORACORTE, tz = tz)
  df$fechaHoraFinCaptura <- safe_posix(df$fechaHoraFinCaptura, tz = tz)
  
  df <- df %>%
    mutate(
      provincia = as.factor(provincia),
      descProvincia = as.factor(descProvincia),
      canton = as.factor(canton),
      descCanton = as.factor(descCanton),
      distritoAdmin = as.factor(distritoAdmin),
      descDistritoAdmin = as.factor(descDistritoAdmin),
      codPartido = suppressWarnings(as.character(codPartido)),
      descPartido = as.factor(descPartido),
      votos = suppressWarnings(as.numeric(votos)),
      junta = suppressWarnings(as.integer(junta)),
      electores = suppressWarnings(as.numeric(electores)),
      total = suppressWarnings(as.numeric(total)),
      vNulos = suppressWarnings(as.numeric(vNulos)),
      vBlancos = suppressWarnings(as.numeric(vBlancos)),
      estado = as.factor(estado),
      medioTransmision = as.character(medioTransmision)
    )
  
  df
}

# =============================================================================
# SECCIÓN 3: LÓGICA DE ACUMULACIÓN DE CORTES
# =============================================================================
# CRÍTICO: Cada corte representa información INCREMENTAL que debe sumarse
# para obtener el total acumulado hasta ese momento del escrutinio

#' Función segura para max que retorna NA en lugar de -Inf
safe_max <- function(x, na.rm = TRUE) {
  x <- x[!is.na(x)]
  if (length(x) == 0) return(NA_real_)
  max(x)
}

#' Función segura para max de fechas POSIXct
safe_max_date <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) == 0) return(as.POSIXct(NA, tz = "America/Costa_Rica"))
  max(x)
}

#' Calcula los datos acumulados hasta un corte específico
#' @param df Data frame con datos electorales
#' @param hasta_corte Número de corte hasta el cual acumular (inclusive)
#' @return Data frame con votos acumulados por junta/partido
calcular_acumulado_hasta_corte <- function(df, hasta_corte) {
  df %>%
    filter(NUMEROCORTE <= hasta_corte) %>%
    group_by(
      provincia, descProvincia, canton, descCanton,
      distritoAdmin, descDistritoAdmin, junta, codPartido, descPartido
    ) %>%
    summarise(
      votos = sum(votos, na.rm = TRUE),
      electores = safe_max(electores),  # El padrón no cambia
      total = sum(total, na.rm = TRUE),
      vNulos = sum(vNulos, na.rm = TRUE),
      vBlancos = sum(vBlancos, na.rm = TRUE),
      ultimo_corte = safe_max(NUMEROCORTE),
      .groups = "drop"
    )
}

#' Calcula el TOTAL FINAL sumando TODOS los cortes
#' @param df Data frame con datos electorales
#' @return Data frame con el total acumulado de todos los cortes
calcular_total_todos_cortes <- function(df) {
  cortes <- sort(unique(df$NUMEROCORTE[!is.na(df$NUMEROCORTE)]))
  max_corte <- max(cortes, na.rm = TRUE)
  calcular_acumulado_hasta_corte(df, max_corte)
}

#' Calcula el DELTA (incremento) de un corte específico
#' @param df Data frame con datos electorales
#' @param corte Número del corte a calcular
#' @return Data frame con los votos NUEVOS de ese corte
calcular_delta_corte <- function(df, corte) {
  df %>%
    filter(NUMEROCORTE == corte) %>%
    group_by(
      provincia, descProvincia, canton, descCanton,
      distritoAdmin, descDistritoAdmin, junta, codPartido, descPartido
    ) %>%
    summarise(
      votos_delta = sum(votos, na.rm = TRUE),
      electores = safe_max(electores),
      total_delta = sum(total, na.rm = TRUE),
      vNulos_delta = sum(vNulos, na.rm = TRUE),
      vBlancos_delta = sum(vBlancos, na.rm = TRUE),
      .groups = "drop"
    )
}

#' Genera resumen de evolución por corte
#' @param df Data frame con datos electorales
#' @return Data frame con métricas por corte (acumulado y delta)
generar_evolucion_cortes <- function(df) {
  cortes <- sort(unique(df$NUMEROCORTE[!is.na(df$NUMEROCORTE)]))
  
  map_dfr(cortes, function(c) {
    acum <- calcular_acumulado_hasta_corte(df, c)
    
    votos_partido <- acum %>%
      group_by(codPartido, descPartido) %>%
      summarise(votos = sum(votos, na.rm = TRUE), .groups = "drop")
    
    metricas_junta <- acum %>%
      group_by(junta) %>%
      summarise(
        electores = first(na.omit(electores)),
        total_votos = first(na.omit(total)),
        votos_nulos = first(na.omit(vNulos)),
        votos_blancos = first(na.omit(vBlancos)),
        .groups = "drop"
      ) %>%
      mutate(
        electores = replace_na(electores, 0),
        total_votos = replace_na(total_votos, 0),
        votos_nulos = replace_na(votos_nulos, 0),
        votos_blancos = replace_na(votos_blancos, 0)
      )
    
    # Obtener fecha del corte de forma segura
    fechas_corte <- df %>%
      filter(NUMEROCORTE == c) %>%
      pull(FECHAHORACORTE)
    fecha_corte <- safe_max_date(fechas_corte)
    
    tibble(
      corte = c,
      fecha_hora = fecha_corte,
      juntas_escrutadas = nrow(metricas_junta),
      electores = sum(metricas_junta$electores, na.rm = TRUE),
      votos_emitidos = sum(metricas_junta$total_votos, na.rm = TRUE),
      votos_validos = sum(votos_partido$votos, na.rm = TRUE),
      votos_nulos = sum(metricas_junta$votos_nulos, na.rm = TRUE),
      votos_blancos = sum(metricas_junta$votos_blancos, na.rm = TRUE)
    )
  }) %>%
    mutate(
      participacion = if_else(electores > 0, votos_emitidos / electores * 100, 0),
      pct_escrutado = juntas_escrutadas / max(juntas_escrutadas, na.rm = TRUE) * 100,
      # Calcular deltas respecto al corte anterior
      delta_votos = votos_emitidos - lag(votos_emitidos, default = 0),
      delta_juntas = juntas_escrutadas - lag(juntas_escrutadas, default = 0)
    )
}

# =============================================================================
# SECCIÓN 4: MÉTRICAS DE CIENCIA POLÍTICA
# =============================================================================

#' Índice de Fragmentación de Rae (1967)
#' F = 1 - Σ(p_i²)
#' Mide la probabilidad de que dos votantes elegidos al azar voten por partidos diferentes
#' Rango: 0 (hegemonía total) a 1 (fragmentación máxima)
calcular_indice_rae <- function(votos_partido) {
  total <- sum(votos_partido$votos, na.rm = TRUE)
  if (total == 0) return(NA_real_)
  proporciones <- votos_partido$votos / total
  1 - sum(proporciones^2)
}

#' Número Efectivo de Partidos - Laakso & Taagepera (1979)
#' NEP = 1 / Σ(p_i²)
#' Indica cuántos partidos "equivalentes" competirían si todos tuvieran igual fuerza
calcular_nep <- function(votos_partido) {
  total <- sum(votos_partido$votos, na.rm = TRUE)
  if (total == 0) return(NA_real_)
  proporciones <- votos_partido$votos / total
  proporciones <- proporciones[proporciones > 0]
  if (length(proporciones) == 0) return(NA_real_)
  1 / sum(proporciones^2)
}

#' Índice de Concentración (C2)
#' Suma de los porcentajes de los dos partidos más votados
#' Indica el grado de bipartidismo
calcular_concentracion_c2 <- function(votos_partido) {
  total <- sum(votos_partido$votos, na.rm = TRUE)
  if (total == 0) return(NA_real_)
  top2 <- votos_partido %>%
    arrange(desc(votos)) %>%
    head(2) %>%
    pull(votos)
  sum(top2) / total * 100
}

#' Índice de Competitividad Electoral
#' Diferencia porcentual entre el primero y segundo lugar
#' Menor valor = mayor competitividad
calcular_competitividad <- function(votos_partido) {
  total <- sum(votos_partido$votos, na.rm = TRUE)
  if (total == 0) return(NA_real_)
  top2 <- votos_partido %>%
    arrange(desc(votos)) %>%
    head(2) %>%
    mutate(pct = votos / total * 100) %>%
    pull(pct)
  if (length(top2) < 2) return(NA_real_)
  top2[1] - top2[2]
}

#' Índice de Herfindahl-Hirschman (HHI)
#' HHI = Σ(p_i² × 10000)
#' Usado en economía, aplicable a concentración electoral
#' Rango: 0 a 10000 (mayor = más concentrado)
calcular_hhi <- function(votos_partido) {
  total <- sum(votos_partido$votos, na.rm = TRUE)
  if (total == 0) return(NA_real_)
  proporciones <- votos_partido$votos / total
  sum(proporciones^2) * 10000
}

#' Umbral de victoria en primera ronda (Costa Rica: 40%)
#' Calcula si el líder supera el umbral
calcular_umbral_victoria <- function(votos_partido, umbral = 40) {
  total <- sum(votos_partido$votos, na.rm = TRUE)
  if (total == 0) return(list(supera = FALSE, pct_lider = 0, diferencia = -umbral))
  lider <- votos_partido %>%
    arrange(desc(votos)) %>%
    head(1)
  pct_lider <- lider$votos / total * 100
  list(
    supera = pct_lider >= umbral,
    pct_lider = pct_lider,
    diferencia = pct_lider - umbral,
    partido_lider = as.character(lider$descPartido)
  )
}

#' Índice de Desproporcionalidad de Gallagher (LSq)
#' Requiere comparar votos con escaños asignados
#' LSq = sqrt(0.5 × Σ(v_i - s_i)²)
#' Para uso futuro con datos de asignación de escaños
calcular_gallagher <- function(votos_partido, escanos_partido) {
  # Implementación para futuras versiones con datos legislativos
  NA_real_
}

#' Calcula todas las métricas de ciencia política
calcular_metricas_ciencia_politica <- function(votos_partido) {
  umbral <- calcular_umbral_victoria(votos_partido)
  
  list(
    # Fragmentación y concentración
    indice_rae = calcular_indice_rae(votos_partido),
    nep = calcular_nep(votos_partido),
    concentracion_c2 = calcular_concentracion_c2(votos_partido),
    hhi = calcular_hhi(votos_partido),
    
    # Competitividad
    margen_victoria = calcular_competitividad(votos_partido),
    
    # Umbral primera ronda
    supera_umbral_40 = umbral$supera,
    pct_lider = umbral$pct_lider,
    diferencia_umbral = umbral$diferencia,
    partido_lider = umbral$partido_lider,
    
    # Conteos básicos
    n_partidos = nrow(votos_partido),
    n_partidos_con_votos = sum(votos_partido$votos > 0),
    n_partidos_sobre_5pct = sum(votos_partido$votos / sum(votos_partido$votos) > 0.05, na.rm = TRUE)
  )
}

# =============================================================================
# SECCIÓN 5: FUNCIONES DE AGREGACIÓN
# =============================================================================

#' Resumen nacional para un corte específico (ACUMULADO)
calcular_resumen_nacional <- function(df, hasta_corte, modo = "acumulado") {
  if (modo == "acumulado") {
    df_proc <- calcular_acumulado_hasta_corte(df, hasta_corte)
  } else {
    df_proc <- calcular_delta_corte(df, hasta_corte)
  }
  
  # Métricas por junta
  metricas_junta <- df_proc %>%
    group_by(junta) %>%
    summarise(
      electores = first(na.omit(electores)),
      total_votos = if("total" %in% names(df_proc)) first(na.omit(total)) else first(na.omit(total_delta)),
      votos_nulos = if("vNulos" %in% names(df_proc)) first(na.omit(vNulos)) else first(na.omit(vNulos_delta)),
      votos_blancos = if("vBlancos" %in% names(df_proc)) first(na.omit(vBlancos)) else first(na.omit(vBlancos_delta)),
      .groups = "drop"
    ) %>%
    mutate(
      electores = replace_na(electores, 0),
      total_votos = replace_na(total_votos, 0),
      votos_nulos = replace_na(votos_nulos, 0),
      votos_blancos = replace_na(votos_blancos, 0)
    )
  
  # Votos por partido
  votos_partido <- df_proc %>%
    group_by(codPartido, descPartido) %>%
    summarise(
      votos = if("votos" %in% names(df_proc)) sum(votos, na.rm = TRUE) else sum(votos_delta, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    arrange(desc(votos)) %>%
    mutate(
      total_validos = sum(votos, na.rm = TRUE),
      porcentaje = if_else(total_validos > 0, votos / total_validos * 100, 0),
      porcentaje_acum = cumsum(porcentaje)
    )
  
  total_electores <- sum(metricas_junta$electores, na.rm = TRUE)
  total_votos <- sum(metricas_junta$total_votos, na.rm = TRUE)
  total_validos <- sum(votos_partido$votos, na.rm = TRUE)
  total_nulos <- sum(metricas_junta$votos_nulos, na.rm = TRUE)
  total_blancos <- sum(metricas_junta$votos_blancos, na.rm = TRUE)
  
  # Calcular métricas de ciencia política
  metricas_cp <- calcular_metricas_ciencia_politica(votos_partido)
  
  list(
    # Datos básicos
    juntas = nrow(metricas_junta),
    electores = total_electores,
    votos_emitidos = total_votos,
    votos_validos = total_validos,
    votos_nulos = total_nulos,
    votos_blancos = total_blancos,
    participacion = if (total_electores > 0) total_votos / total_electores * 100 else 0,
    abstencion = if (total_electores > 0) (1 - total_votos / total_electores) * 100 else 0,
    
    # Datos por partido
    votos_partido = votos_partido,
    
    # Métricas de ciencia política
    metricas_cp = metricas_cp
  )
}

#' Resumen del TOTAL de todos los cortes
calcular_resumen_total <- function(df) {
  cortes <- sort(unique(df$NUMEROCORTE[!is.na(df$NUMEROCORTE)]))
  max_corte <- max(cortes, na.rm = TRUE)
  res <- calcular_resumen_nacional(df, max_corte, modo = "acumulado")
  res$total_cortes <- length(cortes)
  res$ultimo_corte <- max_corte
  res
}

#' Análisis geográfico por nivel
calcular_resultados_geograficos <- function(df, hasta_corte, nivel = "provincia") {
  df_acum <- calcular_acumulado_hasta_corte(df, hasta_corte)
  
  if (nivel == "provincia") {
    grupo <- c("provincia", "descProvincia")
  } else if (nivel == "canton") {
    grupo <- c("descProvincia", "canton", "descCanton")
  } else {
    grupo <- c("descProvincia", "descCanton", "distritoAdmin", "descDistritoAdmin")
  }
  
  # Métricas base por unidad geográfica
  metricas <- df_acum %>%
    group_by(across(all_of(grupo)), junta) %>%
    summarise(
      electores = first(na.omit(electores)),
      total_votos = sum(total, na.rm = TRUE) / n_distinct(codPartido),
      votos_nulos = sum(vNulos, na.rm = TRUE) / n_distinct(codPartido),
      votos_blancos = sum(vBlancos, na.rm = TRUE) / n_distinct(codPartido),
      .groups = "drop"
    ) %>%
    group_by(across(all_of(grupo))) %>%
    summarise(
      juntas = n(),
      electores = sum(electores, na.rm = TRUE),
      votos_emitidos = sum(total_votos, na.rm = TRUE),
      votos_nulos = sum(votos_nulos, na.rm = TRUE),
      votos_blancos = sum(votos_blancos, na.rm = TRUE),
      .groups = "drop"
    )
  
  # Votos por partido y unidad geográfica
  votos_partido <- df_acum %>%
    group_by(across(all_of(grupo)), descPartido) %>%
    summarise(votos = sum(votos, na.rm = TRUE), .groups = "drop")
  
  # Identificar ganadores
  ganadores <- votos_partido %>%
    group_by(across(all_of(grupo))) %>%
    slice_max(votos, n = 1, with_ties = FALSE) %>%
    ungroup() %>%
    rename(partido_ganador = descPartido, votos_ganador = votos)
  
  # Calcular segundo lugar para margen
  segundo <- votos_partido %>%
    group_by(across(all_of(grupo))) %>%
    arrange(desc(votos)) %>%
    slice(2) %>%
    ungroup() %>%
    rename(partido_segundo = descPartido, votos_segundo = votos)
  
  # Combinar resultados
  resultado <- metricas %>%
    left_join(ganadores, by = grupo) %>%
    left_join(segundo %>% select(all_of(grupo), votos_segundo), by = grupo) %>%
    mutate(
      votos_segundo = replace_na(votos_segundo, 0),
      participacion = if_else(electores > 0, votos_emitidos / electores * 100, 0),
      validos = pmax(votos_emitidos - votos_nulos - votos_blancos, 0),
      pct_ganador = if_else(validos > 0, votos_ganador / validos * 100, 0),
      margen = if_else(validos > 0, (votos_ganador - votos_segundo) / validos * 100, 0)
    ) %>%
    select(-validos)
  
  list(resumen = resultado, detalle_partidos = votos_partido)
}

#' Evolución de un partido específico por corte
evolucion_partido <- function(df, codigo_partido = NULL, nombre_partido = NULL) {
  cortes <- sort(unique(df$NUMEROCORTE[!is.na(df$NUMEROCORTE)]))
  
  map_dfr(cortes, function(c) {
    acum <- calcular_acumulado_hasta_corte(df, c)
    
    votos_totales <- sum(acum$votos, na.rm = TRUE)
    
    if (!is.null(codigo_partido)) {
      votos_p <- acum %>% filter(codPartido == codigo_partido)
    } else if (!is.null(nombre_partido)) {
      votos_p <- acum %>% filter(grepl(nombre_partido, descPartido, ignore.case = TRUE))
    } else {
      return(tibble())
    }
    
    tibble(
      corte = c,
      votos = sum(votos_p$votos, na.rm = TRUE),
      total_validos = votos_totales,
      porcentaje = if(votos_totales > 0) sum(votos_p$votos, na.rm = TRUE) / votos_totales * 100 else 0
    )
  })
}

# =============================================================================
# SECCIÓN 6: COLORES DE PARTIDOS
# =============================================================================

colores_partidos <- c(
  "PUEBLO SOBERANO" = "#6A0DAD",
  "LIBERACION NACIONAL" = "#228B22",
  "COALICION AGENDA CIUDADANA" = "#FF6B35",
  "FRENTE AMPLIO" = "#E31937",
  "UNIDAD SOCIAL CRISTIANA" = "#DC143C",
  "NUEVA REPUBLICA" = "#1E90FF",
  "AVANZA" = "#FFD700",
  "UNIDOS PODEMOS" = "#00CED1",
  "PROGRESO SOCIAL DEMOCRATICO" = "#8B4513",
  "LIBERAL PROGRESISTA" = "#4169E1",
  "NUEVA GENERACION" = "#32CD32",
  "CENTRO DEMOCRATICO Y SOCIAL" = "#FF69B4",
  "INTEGRACION NACIONAL" = "#808080",
  "JUSTICIA SOCIAL COSTARRICENSE" = "#9932CC",
  "DE LA CLASE TRABAJADORA" = "#B22222",
  "UNION COSTARRICENSE DEMOCRATICA" = "#20B2AA",
  "ESPERANZA NACIONAL" = "#DAA520",
  "ESPERANZA Y LIBERTAD" = "#7B68EE",
  "ALIANZA COSTA RICA PRIMERO" = "#2E8B57",
  "AQUI COSTA RICA MANDA" = "#CD853F"
)

get_color_partido <- function(partido) {
  partido_upper <- toupper(as.character(partido))
  if (partido_upper %in% names(colores_partidos)) {
    return(colores_partidos[[partido_upper]])
  }
  # Color por defecto basado en hash del nombre
  hash_val <- sum(utf8ToInt(partido_upper)) %% 12
  paleta_default <- RColorBrewer::brewer.pal(12, "Set3")
  paleta_default[hash_val + 1]
}

# =============================================================================
# SECCIÓN 7: INTERFAZ DE USUARIO (UI)
# =============================================================================

ui <- dashboardPage(
  skin = "blue",
  
  dashboardHeader(
    title = span(
      icon("vote-yea"), 
      "Sistema Electoral CR 2026",
      style = "font-size: 16px; font-weight: bold;"
    ),
    titleWidth = 300
  ),
  
  dashboardSidebar(
    width = 300,
    sidebarMenu(
      id = "tabs",
      menuItem("Resumen Nacional", tabName = "resumen", icon = icon("chart-pie")),
      menuItem("Métricas de Ciencia Política", tabName = "ciencia_politica", icon = icon("university")),
      menuItem("Evolución Temporal", tabName = "temporal", icon = icon("clock")),
      menuItem("Análisis Geográfico", tabName = "geografico", icon = icon("map")),
      menuItem("Comparativo Partidos", tabName = "partidos", icon = icon("users")),
      menuItem("Análisis por Corte", tabName = "cortes", icon = icon("layer-group")),
      menuItem("Análisis por Junta", tabName = "juntas", icon = icon("table")),
      menuItem("Exportar Datos", tabName = "exportar", icon = icon("download")),
      menuItem("Recursos y Datos", tabName = "recursos", icon = icon("database"))
    ),
    hr(),
    
    # Panel de carga de datos
    box(
      width = 12,
      title = "Carga de Datos",
      status = "primary",
      solidHeader = TRUE,
      collapsible = TRUE,
      fileInput(
        "archivo", 
        "Archivo TSE:",
        accept = c(".xlsx", ".xls", ".csv"),
        buttonLabel = "Buscar...",
        placeholder = "Ningún archivo"
      ),
      actionButton(
        "btn_load", 
        "Cargar / Recargar",
        icon = icon("upload"),
        class = "btn-primary btn-block"
      )
    ),
    
    uiOutput("file_status"),
    hr(),
    
    # Selector de corte
    box(
      width = 12,
      title = "Selección de Corte",
      status = "info",
      solidHeader = TRUE,
      radioButtons(
        "modo_corte",
        "Modo de visualización:",
        choices = c(
          "Acumulado hasta corte" = "acumulado",
          "Solo este corte (delta)" = "delta",
          "Total todos los cortes" = "total"
        ),
        selected = "total"
      ),
      conditionalPanel(
        condition = "input.modo_corte != 'total'",
        selectInput(
          "corte_global", 
          "Número de corte:",
          choices = NULL,
          selected = NULL
        )
      )
    )
  ),
  
  dashboardBody(
    tags$head(
      tags$style(HTML("
      /* ============================================ */
      /* ESTILOS GENERALES */
      /* ============================================ */
      .content-wrapper { 
        background-color: #f4f6f9; 
        overflow-x: auto;
      }
      
      /* ============================================ */
      /* SIDEBAR - MEJORAR VISIBILIDAD */
      /* ============================================ */
      .main-sidebar {
        width: 300px !important;
      }
      .main-sidebar .sidebar {
        padding-bottom: 50px;
      }
      
      /* Asegurar que el texto del sidebar sea visible */
      .sidebar-menu > li > a {
        white-space: normal !important;
        line-height: 1.3;
        padding: 12px 15px !important;
        font-size: 14px !important;
      }
      .sidebar-menu > li > a > .fa,
      .sidebar-menu > li > a > .glyphicon,
      .sidebar-menu > li > a > .ion {
        margin-right: 8px;
      }
      
      /* Box de carga de datos en sidebar */
      .sidebar .box {
        margin: 10px;
        background: rgba(255,255,255,0.1);
        border: none;
      }
      .sidebar .box-header {
        color: white;
        padding: 8px 10px;
      }
      .sidebar .box-title {
        font-size: 13px;
      }
      .sidebar .box-body {
        padding: 10px;
      }
      
      /* File input en sidebar */
      .sidebar .form-group {
        margin-bottom: 10px;
      }
      .sidebar .btn-file {
        width: 100%;
      }
      .sidebar .progress {
        margin-bottom: 5px;
      }
      
      /* Radio buttons en sidebar */
      .sidebar .radio label {
        color: white;
        font-size: 12px;
        padding-left: 20px;
      }
      
      /* Select input en sidebar */
      .sidebar .selectize-input {
        font-size: 12px;
      }
      
      /* ============================================ */
      /* BOXES Y TARJETAS */
      /* ============================================ */
      .small-box { 
        border-radius: 10px;
        min-height: 100px; 
      }
      .small-box h3 {
        font-size: 28px;
      }
      .small-box p {
        font-size: 14px;
      }
      
      .box { 
        border-radius: 10px; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        overflow: visible; 
      }
      .box-header {
        padding: 10px 15px;
      }
      .box-title {
        font-size: 16px;
        font-weight: 600;
      }
      
      .info-box { 
        border-radius: 10px;
        min-height: 90px; 
      }
      .info-box-icon {
        border-radius: 10px 0 0 10px;
        width: 70px;
      }
      .info-box-content {
        padding: 10px;
        margin-left: 70px;
      }
      .info-box-text {
        font-size: 13px;
        white-space: normal;
      }
      .info-box-number {
        font-size: 22px;
      }
      
      .nav-tabs-custom > .tab-content { 
        padding: 15px; 
      }
      
      /* ============================================ */
      /* MÉTRICAS PERSONALIZADAS */
      /* ============================================ */
      .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        margin-bottom: 15px;
      }
      .metric-value { 
        font-size: 2.2em; 
        font-weight: bold; 
      }
      .metric-label { 
        font-size: 0.9em; 
        opacity: 0.9; 
      }
      
      /* Umbral de victoria */
      .umbral-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 1.1em;
      }
      .umbral-box h3 {
        margin: 10px 0;
        font-size: 1.4em;
      }
      .umbral-box p {
        margin: 5px 0;
      }
      .umbral-si { 
        background-color: #28a745; 
        color: white; 
      }
      .umbral-no { 
        background-color: #dc3545; 
        color: white; 
      }
      
      /* ============================================ */
      /* TABLAS */
      /* ============================================ */
      .dataTables_wrapper {
        font-size: 13px;
      }
      .dataTables_filter input {
        border-radius: 4px;
        border: 1px solid #ddd;
        padding: 5px 10px;
      }
      
      /* ============================================ */
      /* GRÁFICOS PLOTLY */
      /* ============================================ */
      .plotly {
        min-height: 300px;
      }
      
      /* ============================================ */
      /* RESPONSIVIDAD */
      /* ============================================ */
      @media (max-width: 768px) {
        .main-sidebar {
          width: 250px !important;
        }
        .small-box h3 {
          font-size: 22px;
        }
        .info-box-number {
          font-size: 18px;
        }
        .box-title {
          font-size: 14px;
        }
      }
      
      /* ============================================ */
      /* SCROLL Y OVERFLOW */
      /* ============================================ */
      .tab-content {
        overflow-x: auto;
      }
      .box-body {
        overflow-x: auto;
      }
      
      /* Ocultar scrollbar pero permitir scroll */
      .sidebar::-webkit-scrollbar {
        width: 5px;
      }
      .sidebar::-webkit-scrollbar-track {
        background: transparent;
      }
      .sidebar::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.3);
        border-radius: 3px;
      }
    "))
    ),
    
    tabItems(
      # =========================================================================
      # TAB: RESUMEN NACIONAL
      # =========================================================================
      tabItem(
        tabName = "resumen",
        
        fluidRow(
          valueBoxOutput("vb_juntas", width = 3),
          valueBoxOutput("vb_electores", width = 3),
          valueBoxOutput("vb_participacion", width = 3),
          valueBoxOutput("vb_votos_validos", width = 3)
        ),
        
        fluidRow(
          box(
            title = "Resultados por Partido",
            status = "primary",
            solidHeader = TRUE,
            width = 8,
            withSpinner(plotlyOutput("grafico_barras_partidos", height = "500px"))
          ),
          box(
            title = "Distribución del Voto",
            status = "info",
            solidHeader = TRUE,
            width = 4,
            withSpinner(plotlyOutput("grafico_pie_partidos", height = "500px"))
          )
        ),
        
        fluidRow(
          box(
            title = "Tabla de Resultados",
            status = "success",
            solidHeader = TRUE,
            width = 12,
            withSpinner(DTOutput("tabla_resultados_nacional"))
          )
        )
      ),
      
      # =========================================================================
      # TAB: MÉTRICAS DE CIENCIA POLÍTICA
      # =========================================================================
      tabItem(
        tabName = "ciencia_politica",
        
        fluidRow(
          box(
            title = "Umbral de Victoria en Primera Ronda (40%)",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            uiOutput("umbral_victoria_box")
          )
        ),
        
        fluidRow(
          infoBoxOutput("ib_nep", width = 4),
          infoBoxOutput("ib_rae", width = 4),
          infoBoxOutput("ib_concentracion", width = 4)
        ),
        
        fluidRow(
          infoBoxOutput("ib_competitividad", width = 4),
          infoBoxOutput("ib_hhi", width = 4),
          infoBoxOutput("ib_partidos_relevantes", width = 4)
        ),
        
        fluidRow(
          box(
            title = "Interpretación de Métricas",
            status = "info",
            solidHeader = TRUE,
            width = 12,
            collapsible = TRUE,
            collapsed = FALSE,
            HTML("
            <h4>Guía de Interpretación</h4>
            <table class='table table-striped'>
              <tr>
                <th>Métrica</th>
                <th>Descripción</th>
                <th>Interpretación</th>
              </tr>
              <tr>
                <td><strong>NEP (Número Efectivo de Partidos)</strong></td>
                <td>Laakso & Taagepera (1979). Mide cuántos partidos 'equivalentes' compiten.</td>
                <td>NEP < 2.5: Sistema de partido dominante<br>2.5-3.5: Bipartidismo moderado<br>>3.5: Multipartidismo</td>
              </tr>
              <tr>
                <td><strong>Índice de Rae</strong></td>
                <td>Fragmentación electoral (Rae, 1967). Probabilidad de que dos votantes aleatorios voten diferente.</td>
                <td>0-0.5: Baja fragmentación<br>0.5-0.7: Moderada<br>>0.7: Alta fragmentación</td>
              </tr>
              <tr>
                <td><strong>Concentración C2</strong></td>
                <td>Suma de porcentajes de los dos principales partidos.</td>
                <td>>80%: Sistema bipartidista<br>60-80%: Competencia moderada<br><60%: Alta dispersión</td>
              </tr>
              <tr>
                <td><strong>Margen de Victoria</strong></td>
                <td>Diferencia entre primero y segundo lugar.</td>
                <td><5%: Elección muy competida<br>5-15%: Competitiva<br>>15%: Victoria clara</td>
              </tr>
              <tr>
                <td><strong>HHI (Herfindahl-Hirschman)</strong></td>
                <td>Índice de concentración del mercado electoral.</td>
                <td><1500: Mercado competitivo<br>1500-2500: Moderadamente concentrado<br>>2500: Altamente concentrado</td>
              </tr>
            </table>
          ")
          )
        ),
        
        fluidRow(
          box(
            title = "Curva de Lorenz Electoral",
            status = "warning",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("grafico_lorenz", height = "400px"))
          ),
          box(
            title = "Evolución del NEP por Corte",
            status = "success",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("grafico_nep_evolucion", height = "400px"))
          )
        )
      ),
      
      # =========================================================================
      # TAB: EVOLUCIÓN TEMPORAL
      # =========================================================================
      tabItem(
        tabName = "temporal",
        
        fluidRow(
          box(
            title = "Evolución del Escrutinio",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            withSpinner(plotlyOutput("grafico_evolucion_escrutinio", height = "350px"))
          )
        ),
        
        fluidRow(
          box(
            title = "Evolución de Votos por Partido",
            status = "info",
            solidHeader = TRUE,
            width = 8,
            withSpinner(plotlyOutput("grafico_evolucion_partidos", height = "450px"))
          ),
          box(
            title = "Selección de Partidos",
            status = "warning",
            solidHeader = TRUE,
            width = 4,
            uiOutput("selector_partidos_evolucion"),
            checkboxInput("mostrar_porcentaje", "Mostrar porcentaje", value = TRUE)
          )
        ),
        
        fluidRow(
          box(
            title = "Velocidad del Escrutinio",
            status = "success",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("grafico_velocidad_escrutinio", height = "300px"))
          ),
          box(
            title = "Tabla de Evolución por Corte",
            status = "primary",
            solidHeader = TRUE,
            width = 6,
            withSpinner(DTOutput("tabla_evolucion_cortes"))
          )
        )
      ),
      
      # =========================================================================
      # TAB: ANÁLISIS GEOGRÁFICO
      # =========================================================================
      tabItem(
        tabName = "geografico",
        
        fluidRow(
          box(
            title = "Nivel de Agregación",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            radioButtons(
              "nivel_geo",
              NULL,
              choices = c(
                "Provincia" = "provincia",
                "Cantón" = "canton",
                "Distrito" = "distrito"
              ),
              selected = "provincia",
              inline = TRUE
            )
          )
        ),
        
        fluidRow(
          box(
            title = "Ganador por Unidad Geográfica",
            status = "info",
            solidHeader = TRUE,
            width = 8,
            withSpinner(plotlyOutput("grafico_geo_ganador", height = "500px"))
          ),
          box(
            title = "Participación Electoral",
            status = "warning",
            solidHeader = TRUE,
            width = 4,
            withSpinner(plotlyOutput("grafico_geo_participacion", height = "500px"))
          )
        ),
        
        fluidRow(
          box(
            title = "Tabla de Resultados Geográficos",
            status = "success",
            solidHeader = TRUE,
            width = 12,
            withSpinner(DTOutput("tabla_resultados_geo"))
          )
        )
      ),
      
      # =========================================================================
      # TAB: COMPARATIVO PARTIDOS
      # =========================================================================
      tabItem(
        tabName = "partidos",
        
        fluidRow(
          box(
            title = "Comparación de Desempeño",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            fluidRow(
              column(6, uiOutput("selector_partido_1")),
              column(6, uiOutput("selector_partido_2"))
            )
          )
        ),
        
        fluidRow(
          box(
            title = "Comparación de Votos",
            status = "info",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("grafico_comparativo_votos", height = "400px"))
          ),
          box(
            title = "Comparación Geográfica",
            status = "warning",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("grafico_comparativo_geo", height = "400px"))
          )
        ),
        
        fluidRow(
          box(
            title = "Ranking de Partidos por Provincia",
            status = "success",
            solidHeader = TRUE,
            width = 12,
            withSpinner(plotlyOutput("heatmap_partidos_provincia", height = "500px"))
          )
        )
      ),
      
      # =========================================================================
      # TAB: ANÁLISIS POR CORTE
      # =========================================================================
      tabItem(
        tabName = "cortes",
        
        fluidRow(
          box(
            title = "Resumen de Cortes",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            HTML("<p><strong>Nota metodológica:</strong> Cada corte representa información 
               <em>incremental</em> del escrutinio. Los totales se calculan sumando 
               todos los cortes acumulativamente.</p>")
          )
        ),
        
        fluidRow(
          box(
            title = "Comparación entre Cortes",
            status = "info",
            solidHeader = TRUE,
            width = 12,
            fluidRow(
              column(4, uiOutput("selector_corte_comparar_1")),
              column(4, uiOutput("selector_corte_comparar_2")),
              column(4, actionButton("btn_comparar_cortes", "Comparar", 
                                     icon = icon("balance-scale"), class = "btn-primary btn-lg"))
            )
          )
        ),
        
        fluidRow(
          box(
            title = "Votos Incrementales por Corte",
            status = "warning",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("grafico_delta_cortes", height = "400px"))
          ),
          box(
            title = "Acumulado por Corte",
            status = "success",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("grafico_acumulado_cortes", height = "400px"))
          )
        ),
        
        fluidRow(
          box(
            title = "Tabla Detallada de Cortes",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            withSpinner(DTOutput("tabla_detalle_cortes"))
          )
        )
      ),
      
      # =========================================================================
      # TAB: ANÁLISIS POR JUNTA
      # =========================================================================
      tabItem(
        tabName = "juntas",
        
        fluidRow(
          box(
            title = "Filtros",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            fluidRow(
              column(3, uiOutput("filtro_provincia_junta")),
              column(3, uiOutput("filtro_canton_junta")),
              column(3, uiOutput("filtro_distrito_junta")),
              column(3, uiOutput("filtro_partido_junta"))
            )
          )
        ),
        
        fluidRow(
          box(
            title = "Resultados por Junta Receptora",
            status = "info",
            solidHeader = TRUE,
            width = 12,
            withSpinner(DTOutput("tabla_juntas"))
          )
        ),
        
        fluidRow(
          box(
            title = "Distribución de Votos por Junta",
            status = "warning",
            solidHeader = TRUE,
            width = 6,
            withSpinner(plotlyOutput("histograma_votos_junta", height = "350px"))
          ),
          box(
            title = "Estadísticas por Junta",
            status = "success",
            solidHeader = TRUE,
            width = 6,
            withSpinner(DTOutput("stats_juntas"))
          )
        )
      ),
      
      # =========================================================================
      # TAB: EXPORTAR DATOS
      # =========================================================================
      tabItem(
        tabName = "exportar",
        
        fluidRow(
          box(
            title = "Exportar Resultados",
            status = "primary",
            solidHeader = TRUE,
            width = 6,
            selectInput(
              "tipo_exportacion",
              "Tipo de datos:",
              choices = c(
                "Resumen Nacional (Total)" = "resumen_total",
                "Resumen Nacional (Por Corte)" = "resumen_corte",
                "Resultados por Provincia" = "provincia",
                "Resultados por Cantón" = "canton",
                "Resultados por Distrito" = "distrito",
                "Evolución Temporal" = "evolucion",
                "Métricas de Ciencia Política" = "metricas_cp",
                "Datos Completos" = "completo"
              )
            ),
            radioButtons(
              "formato_exportacion",
              "Formato:",
              choices = c("Excel (.xlsx)" = "xlsx", "CSV (.csv)" = "csv"),
              selected = "xlsx",
              inline = TRUE
            ),
            downloadButton("btn_descargar", "Descargar", class = "btn-success btn-lg btn-block")
          ),
          box(
            title = "Vista Previa",
            status = "info",
            solidHeader = TRUE,
            width = 6,
            withSpinner(DTOutput("preview_exportacion"))
          )
        ),
        
        fluidRow(
          box(
            title = "Exportar Gráficos",
            status = "warning",
            solidHeader = TRUE,
            width = 12,
            HTML("<p>Los gráficos pueden exportarse directamente desde cada visualización
               usando el menú de Plotly (icono de cámara en la esquina superior derecha).</p>")
          )
        )
      ),

      # =========================================================================
      # TAB: RECURSOS Y DATOS
      # =========================================================================
      tabItem(
        tabName = "recursos",

        fluidRow(
          box(
            title = "Resultados Preliminares - Elecciones 2026",
            status = "primary",
            solidHeader = TRUE,
            width = 12,
            HTML("
              <div style='padding: 15px;'>
                <h4><i class='fa fa-info-circle'></i> Acerca de este Visor</h4>
                <p style='font-size: 14px;'>
                  Este visor interactivo de datos electorales está actualmente <strong>ajustado únicamente
                  para el archivo de resultados de Presidente</strong>. Próximamente se habilitará la
                  funcionalidad para visualizar los resultados de Diputaciones.
                </p>
                <hr>
                <h4><i class='fa fa-calendar'></i> Datos Disponibles (Corte: 3 de Febrero de 2026)</h4>
                <p>Los siguientes archivos contienen los resultados preliminares de las elecciones:</p>
              </div>
            ")
          )
        ),

        fluidRow(
          box(
            title = "Archivo de Resultados - Presidente",
            status = "success",
            solidHeader = TRUE,
            width = 6,
            HTML("
              <div style='text-align: center; padding: 20px;'>
                <i class='fa fa-file-excel' style='font-size: 48px; color: #28a745;'></i>
                <h4 style='margin-top: 15px;'>Elección Presidencial</h4>
                <p><strong>Archivo:</strong> consolidadoResultadosEleccionPresidencial2026 – Presidente.xlsx</p>
                <p><em>Resultados preliminares de la elección presidencial al 3 de febrero de 2026</em></p>
                <span class='label label-success'>Disponible para visualización</span>
              </div>
            "),
            footer = HTML("<p style='font-size: 12px; color: #666;'><i class='fa fa-check-circle'></i> Compatible con este visor</p>")
          ),
          box(
            title = "Archivo de Resultados - Diputados",
            status = "warning",
            solidHeader = TRUE,
            width = 6,
            HTML("
              <div style='text-align: center; padding: 20px;'>
                <i class='fa fa-file-excel' style='font-size: 48px; color: #ffc107;'></i>
                <h4 style='margin-top: 15px;'>Elección de Diputados</h4>
                <p><strong>Archivo:</strong> consolidadoResultadosEleccionPresidencial2026 – Diputado.xlsx</p>
                <p><em>Resultados preliminares de la elección de diputados al 3 de febrero de 2026</em></p>
                <span class='label label-warning'>Próximamente disponible</span>
              </div>
            "),
            footer = HTML("<p style='font-size: 12px; color: #999;'><i class='fa fa-clock'></i> Visualización en desarrollo</p>")
          )
        ),

        fluidRow(
          box(
            title = "Instrucciones de Uso",
            status = "info",
            solidHeader = TRUE,
            width = 12,
            collapsible = TRUE,
            HTML("
              <div style='padding: 10px;'>
                <h5><i class='fa fa-upload'></i> Para visualizar los datos de Presidente:</h5>
                <ol>
                  <li>En el panel lateral izquierdo, haga clic en <strong>'Buscar...'</strong> en la sección 'Carga de Datos'</li>
                  <li>Seleccione el archivo <code>consolidadoResultadosEleccionPresidencial2026 – Presidente.xlsx</code></li>
                  <li>Haga clic en <strong>'Cargar / Recargar'</strong></li>
                  <li>Navegue por las diferentes secciones para explorar los resultados</li>
                </ol>
                <hr>
                <h5><i class='fa fa-cogs'></i> Funcionalidades disponibles:</h5>
                <ul>
                  <li><strong>Resumen Nacional:</strong> Vista general de resultados y distribución del voto</li>
                  <li><strong>Métricas de Ciencia Política:</strong> Índices NEP, Rae, concentración y competitividad</li>
                  <li><strong>Evolución Temporal:</strong> Seguimiento del escrutinio por cortes</li>
                  <li><strong>Análisis Geográfico:</strong> Resultados por provincia, cantón y distrito</li>
                  <li><strong>Comparativo Partidos:</strong> Análisis detallado por partido político</li>
                  <li><strong>Exportar Datos:</strong> Descarga de datos en formato Excel o CSV</li>
                </ul>
              </div>
            ")
          )
        ),

        fluidRow(
          box(
            title = "Información del Sistema",
            status = "default",
            solidHeader = TRUE,
            width = 12,
            HTML("
              <div style='padding: 10px; background-color: #f9f9f9; border-radius: 5px;'>
                <p><strong>Sistema de Gestión y Análisis Electoral - Costa Rica 2026</strong></p>
                <p><i class='fa fa-university'></i> Desarrollado por: CIOdD - Universidad de Costa Rica</p>
                <p><i class='fa fa-code-branch'></i> Versión: 2.0</p>
                <p><i class='fa fa-calendar-alt'></i> Última actualización de datos: 3 de febrero de 2026</p>
              </div>
            ")
          )
        )
      )
    )
  )
)

# =============================================================================
# SECCIÓN 8: SERVIDOR (SERVER)
# =============================================================================

server <- function(input, output, session) {
  
  # ---------------------------------------------------------------------------
  # REACTIVE VALUES
  # ---------------------------------------------------------------------------
  datos <- reactiveVal(NULL)
  file_meta <- reactiveVal(NULL)
  evolucion_data <- reactiveVal(NULL)
  
  # ---------------------------------------------------------------------------
  # CARGA DE DATOS
  # ---------------------------------------------------------------------------
  output$file_status <- renderUI({
    m <- file_meta()
    df <- datos()
    if (is.null(m)) {
      return(HTML("<div style='padding:10px;background:#fff3cd;border-radius:8px;margin:10px;'>
                 <i class='fa fa-exclamation-triangle'></i> Sin archivo cargado.</div>"))
    }
    
    cortes_txt <- ""
    if (!is.null(df)) {
      cortes <- sort(unique(df$NUMEROCORTE[!is.na(df$NUMEROCORTE)]))
      if (length(cortes) > 0) {
        cortes_txt <- paste0("<br><strong>Cortes:</strong> ", min(cortes), " – ", max(cortes), 
                             " (", length(cortes), " cortes)")
      }
    }
    
    HTML(paste0(
      "<div style='padding:10px;background:#d4edda;border-radius:8px;margin:10px;'>",
      "<i class='fa fa-check-circle'></i> <strong>", htmltools::htmlEscape(m$name), "</strong>",
      "<br><small>", round(m$size/(1024^2), 2), " MB</small>",
      cortes_txt,
      "</div>"
    ))
  })
  
  load_selected_file <- function() {
    req(input$archivo)
    tryCatch({
      withProgress(message = 'Cargando datos...', value = 0.3, {
        df <- load_electoral_data(
          filepath = input$archivo$datapath,
          original_name = input$archivo$name,
          tz = "America/Costa_Rica"
        )
        
        setProgress(0.6, detail = "Procesando cortes...")
        
        cortes <- sort(unique(df$NUMEROCORTE[!is.na(df$NUMEROCORTE)]))
        if (length(cortes) == 0) stop("El archivo no contiene NUMEROCORTE válido.")
        
        datos(df)
        file_meta(list(name = input$archivo$name, size = input$archivo$size))
        
        # Generar datos de evolución
        setProgress(0.8, detail = "Calculando evolución...")
        evolucion_data(generar_evolucion_cortes(df))
        
        updateSelectInput(session, "corte_global",
                          choices = setNames(cortes, paste("Corte", cortes)),
                          selected = max(cortes))
        
        setProgress(1, detail = "Completado")
      })
      
      showNotification("Archivo cargado correctamente.", type = "message", duration = 3)
    }, error = function(e) {
      datos(NULL)
      evolucion_data(NULL)
      showModal(modalDialog(
        title = "Error al cargar archivo",
        paste("Detalle:", e$message),
        easyClose = TRUE,
        footer = modalButton("Cerrar")
      ))
    })
  }
  
  observeEvent(input$archivo, { load_selected_file() })
  observeEvent(input$btn_load, { load_selected_file() })
  
  # ---------------------------------------------------------------------------
  # DATOS PROCESADOS REACTIVOS
  # ---------------------------------------------------------------------------
  resumen_actual <- reactive({
    req(datos())
    
    if (input$modo_corte == "total") {
      calcular_resumen_total(datos())
    } else {
      req(input$corte_global)
      calcular_resumen_nacional(
        datos(), 
        as.integer(input$corte_global),
        modo = input$modo_corte
      )
    }
  })
  
  datos_geo <- reactive({
    req(datos(), input$nivel_geo)
    
    if (input$modo_corte == "total") {
      cortes <- sort(unique(datos()$NUMEROCORTE[!is.na(datos()$NUMEROCORTE)]))
      hasta_corte <- max(cortes)
    } else {
      req(input$corte_global)
      hasta_corte <- as.integer(input$corte_global)
    }
    
    calcular_resultados_geograficos(datos(), hasta_corte, input$nivel_geo)
  })
  
  # ---------------------------------------------------------------------------
  # TAB: RESUMEN NACIONAL
  # ---------------------------------------------------------------------------
  output$vb_juntas <- renderValueBox({
    req(resumen_actual())
    valueBox(
      format(resumen_actual()$juntas, big.mark = ","),
      "Juntas Escrutadas",
      icon = icon("building"),
      color = "blue"
    )
  })
  
  output$vb_electores <- renderValueBox({
    req(resumen_actual())
    valueBox(
      format(resumen_actual()$electores, big.mark = ","),
      "Electores en Padrón",
      icon = icon("users"),
      color = "green"
    )
  })
  
  output$vb_participacion <- renderValueBox({
    req(resumen_actual())
    valueBox(
      paste0(round(resumen_actual()$participacion, 1), "%"),
      "Participación Electoral",
      icon = icon("percent"),
      color = "yellow"
    )
  })
  
  output$vb_votos_validos <- renderValueBox({
    req(resumen_actual())
    valueBox(
      format(resumen_actual()$votos_validos, big.mark = ","),
      "Votos Válidos",
      icon = icon("check-circle"),
      color = "purple"
    )
  })
  
  output$grafico_barras_partidos <- renderPlotly({
    req(resumen_actual())
    
    df_plot <- resumen_actual()$votos_partido %>%
      head(15) %>%
      mutate(
        descPartido = factor(descPartido, levels = rev(descPartido)),
        color = sapply(descPartido, get_color_partido)
      )
    
    plot_ly(df_plot, 
            x = ~porcentaje, 
            y = ~descPartido,
            type = 'bar',
            orientation = 'h',
            marker = list(color = ~color),
            text = ~paste0(format(votos, big.mark = ","), " votos (", 
                           round(porcentaje, 2), "%)"),
            hovertemplate = "<b>%{y}</b><br>%{text}<extra></extra>") %>%
      layout(
        xaxis = list(title = "Porcentaje de Votos Válidos", ticksuffix = "%"),
        yaxis = list(title = ""),
        showlegend = FALSE,
        margin = list(l = 200),
        shapes = list(
          list(
            type = "line",
            x0 = 40, x1 = 40,
            y0 = 0, y1 = 1,
            yref = "paper",
            line = list(color = "red", width = 2, dash = "dash")
          )
        ),
        annotations = list(
          list(
            x = 41, y = 1,
            yref = "paper",
            text = "Umbral 40%",
            showarrow = FALSE,
            xanchor = "left",
            font = list(color = "red", size = 10)
          )
        )
      )
  })
  
  output$grafico_pie_partidos <- renderPlotly({
    req(resumen_actual())
    
    df_plot <- resumen_actual()$votos_partido %>%
      mutate(
        grupo = if_else(porcentaje >= 3, as.character(descPartido), "Otros"),
        color = sapply(descPartido, get_color_partido)
      )
    
    df_agrupado <- df_plot %>%
      group_by(grupo) %>%
      summarise(votos = sum(votos), .groups = "drop") %>%
      mutate(porcentaje = votos / sum(votos) * 100)
    
    plot_ly(df_agrupado,
            labels = ~grupo,
            values = ~votos,
            type = 'pie',
            textposition = 'inside',
            textinfo = 'label+percent',
            hovertemplate = "<b>%{label}</b><br>%{value:,.0f} votos<br>%{percent}<extra></extra>") %>%
      layout(showlegend = TRUE)
  })
  
  output$tabla_resultados_nacional <- renderDT({
    req(resumen_actual())
    
    df_tabla <- resumen_actual()$votos_partido %>%
      mutate(
        votos = format(votos, big.mark = ","),
        porcentaje = paste0(round(porcentaje, 2), "%"),
        porcentaje_acum = paste0(round(porcentaje_acum, 2), "%")
      ) %>%
      select(
        Partido = descPartido,
        Votos = votos,
        `%` = porcentaje,
        `% Acum.` = porcentaje_acum
      )
    
    datatable(
      df_tabla,
      options = list(
        pageLength = 20,
        dom = 'Bfrtip',
        buttons = c('copy', 'csv', 'excel')
      ),
      rownames = FALSE,
      class = 'stripe hover'
    )
  })
  
  # ---------------------------------------------------------------------------
  # TAB: MÉTRICAS DE CIENCIA POLÍTICA
  # ---------------------------------------------------------------------------
  output$umbral_victoria_box <- renderUI({
    req(resumen_actual())
    mc <- resumen_actual()$metricas_cp
    
    if (mc$supera_umbral_40) {
      div(
        class = "umbral-box umbral-si",
        icon("trophy", "fa-3x"),
        h3(paste0(mc$partido_lider, " GANA EN PRIMERA RONDA")),
        p(paste0(round(mc$pct_lider, 2), "% de los votos válidos (+", 
                 round(mc$diferencia_umbral, 2), " sobre el umbral)"))
      )
    } else {
      div(
        class = "umbral-box umbral-no",
        icon("balance-scale", "fa-3x"),
        h3("SE REQUIERE SEGUNDA RONDA"),
        p(paste0("Líder actual: ", mc$partido_lider, " con ", round(mc$pct_lider, 2), "%")),
        p(paste0("Faltan ", round(abs(mc$diferencia_umbral), 2), " puntos para alcanzar el 40%"))
      )
    }
  })
  
  output$ib_nep <- renderInfoBox({
    req(resumen_actual())
    infoBox(
      "NEP",
      round(resumen_actual()$metricas_cp$nep, 2),
      subtitle = "Número Efectivo de Partidos",
      icon = icon("users"),
      color = "blue",
      fill = TRUE
    )
  })
  
  output$ib_rae <- renderInfoBox({
    req(resumen_actual())
    infoBox(
      "Índice de Rae",
      round(resumen_actual()$metricas_cp$indice_rae, 3),
      subtitle = "Fragmentación Electoral",
      icon = icon("chart-pie"),
      color = "purple",
      fill = TRUE
    )
  })
  
  output$ib_concentracion <- renderInfoBox({
    req(resumen_actual())
    infoBox(
      "C2",
      paste0(round(resumen_actual()$metricas_cp$concentracion_c2, 1), "%"),
      subtitle = "Concentración (2 primeros)",
      icon = icon("compress-arrows-alt"),
      color = "green",
      fill = TRUE
    )
  })
  
  output$ib_competitividad <- renderInfoBox({
    req(resumen_actual())
    infoBox(
      "Margen",
      paste0(round(resumen_actual()$metricas_cp$margen_victoria, 1), " pp"),
      subtitle = "Diferencia 1° vs 2°",
      icon = icon("arrows-alt-h"),
      color = "yellow",
      fill = TRUE
    )
  })
  
  output$ib_hhi <- renderInfoBox({
    req(resumen_actual())
    infoBox(
      "HHI",
      format(round(resumen_actual()$metricas_cp$hhi), big.mark = ","),
      subtitle = "Índice Herfindahl-Hirschman",
      icon = icon("chart-bar"),
      color = "red",
      fill = TRUE
    )
  })
  
  output$ib_partidos_relevantes <- renderInfoBox({
    req(resumen_actual())
    infoBox(
      "Partidos >5%",
      resumen_actual()$metricas_cp$n_partidos_sobre_5pct,
      subtitle = "Partidos Relevantes",
      icon = icon("flag"),
      color = "orange",
      fill = TRUE
    )
  })
  
  output$grafico_lorenz <- renderPlotly({
    req(resumen_actual())
    
    df_lorenz <- resumen_actual()$votos_partido %>%
      arrange(votos) %>%
      mutate(
        pct_partidos = row_number() / n() * 100,
        pct_votos_acum = cumsum(votos) / sum(votos) * 100
      )
    
    # Añadir punto origen
    df_lorenz <- bind_rows(
      tibble(pct_partidos = 0, pct_votos_acum = 0),
      df_lorenz
    )
    
    plot_ly() %>%
      add_trace(
        data = df_lorenz,
        x = ~pct_partidos,
        y = ~pct_votos_acum,
        type = 'scatter',
        mode = 'lines+markers',
        name = 'Distribución real',
        line = list(color = '#1f77b4', width = 3),
        marker = list(size = 6)
      ) %>%
      add_trace(
        x = c(0, 100),
        y = c(0, 100),
        type = 'scatter',
        mode = 'lines',
        name = 'Igualdad perfecta',
        line = list(color = 'gray', dash = 'dash')
      ) %>%
      layout(
        xaxis = list(title = "% Acumulado de Partidos"),
        yaxis = list(title = "% Acumulado de Votos"),
        showlegend = TRUE
      )
  })
  
  output$grafico_nep_evolucion <- renderPlotly({
    req(datos())
    
    cortes <- sort(unique(datos()$NUMEROCORTE[!is.na(datos()$NUMEROCORTE)]))
    
    nep_evol <- map_dfr(cortes, function(c) {
      res <- calcular_resumen_nacional(datos(), c, "acumulado")
      tibble(
        corte = c,
        nep = res$metricas_cp$nep,
        rae = res$metricas_cp$indice_rae,
        c2 = res$metricas_cp$concentracion_c2
      )
    })
    
    plot_ly(nep_evol, x = ~corte) %>%
      add_trace(y = ~nep, name = "NEP", type = 'scatter', mode = 'lines+markers') %>%
      layout(
        xaxis = list(title = "Número de Corte"),
        yaxis = list(title = "Valor del Índice"),
        showlegend = TRUE
      )
  })
  
  # ---------------------------------------------------------------------------
  # TAB: EVOLUCIÓN TEMPORAL
  # ---------------------------------------------------------------------------
  output$grafico_evolucion_escrutinio <- renderPlotly({
    req(evolucion_data())
    
    plot_ly(evolucion_data(), x = ~corte) %>%
      add_trace(y = ~votos_emitidos, name = "Votos Emitidos", 
                type = 'scatter', mode = 'lines+markers',
                yaxis = "y") %>%
      add_trace(y = ~participacion, name = "Participación %",
                type = 'scatter', mode = 'lines+markers',
                yaxis = "y2") %>%
      layout(
        xaxis = list(title = "Número de Corte"),
        yaxis = list(title = "Votos Emitidos"),
        yaxis2 = list(
          title = "Participación (%)",
          overlaying = "y",
          side = "right",
          ticksuffix = "%"
        ),
        legend = list(x = 0.1, y = 0.9)
      )
  })
  
  output$selector_partidos_evolucion <- renderUI({
    req(datos())
    partidos <- unique(datos()$descPartido)
    partidos <- partidos[!is.na(partidos)]
    
    # Seleccionar los top 5 por defecto
    if (length(resumen_actual()$votos_partido$descPartido) >= 5) {
      default_sel <- as.character(resumen_actual()$votos_partido$descPartido[1:5])
    } else {
      default_sel <- as.character(partidos[1:min(5, length(partidos))])
    }
    
    checkboxGroupInput(
      "partidos_evolucion",
      "Partidos a mostrar:",
      choices = sort(as.character(partidos)),
      selected = default_sel
    )
  })
  
  output$grafico_evolucion_partidos <- renderPlotly({
    req(datos(), input$partidos_evolucion)
    
    cortes <- sort(unique(datos()$NUMEROCORTE[!is.na(datos()$NUMEROCORTE)]))
    
    evol_partidos <- map_dfr(cortes, function(c) {
      acum <- calcular_acumulado_hasta_corte(datos(), c)
      total_votos <- sum(acum$votos, na.rm = TRUE)
      
      acum %>%
        filter(descPartido %in% input$partidos_evolucion) %>%
        group_by(descPartido) %>%
        summarise(votos = sum(votos, na.rm = TRUE), .groups = "drop") %>%
        mutate(
          corte = c,
          porcentaje = if(total_votos > 0) votos / total_votos * 100 else 0
        )
    })
    
    y_var <- if (input$mostrar_porcentaje) "porcentaje" else "votos"
    y_title <- if (input$mostrar_porcentaje) "Porcentaje (%)" else "Votos"
    
    # Definir shapes condicionalmente
    my_shapes <- if (input$mostrar_porcentaje) {
      list(
        list(
          type = "line",
          x0 = 0, x1 = 1,
          xref = "paper",
          y0 = 40, y1 = 40,
          line = list(color = "red", width = 2, dash = "dash")
        )
      )
    } else {
      list()
    }
    
    plot_ly(evol_partidos, x = ~corte, color = ~descPartido) %>%
      add_trace(y = as.formula(paste0("~", y_var)), 
                type = 'scatter', mode = 'lines+markers') %>%
      layout(
        xaxis = list(title = "Número de Corte"),
        yaxis = list(title = y_title),
        showlegend = TRUE,
        shapes = my_shapes
      )
  })
  
  output$grafico_velocidad_escrutinio <- renderPlotly({
    req(evolucion_data())
    
    plot_ly(evolucion_data() %>% filter(corte > 1), x = ~corte) %>%
      add_bars(y = ~delta_juntas, name = "Juntas Nuevas") %>%
      layout(
        xaxis = list(title = "Número de Corte"),
        yaxis = list(title = "Juntas Escrutadas (incremento)")
      )
  })
  
  output$tabla_evolucion_cortes <- renderDT({
    req(evolucion_data())
    
    df_tabla <- evolucion_data() %>%
      mutate(
        votos_emitidos = format(votos_emitidos, big.mark = ","),
        participacion = paste0(round(participacion, 1), "%"),
        delta_votos = format(delta_votos, big.mark = ",")
      ) %>%
      select(
        Corte = corte,
        Juntas = juntas_escrutadas,
        `Votos Totales` = votos_emitidos,
        Participación = participacion,
        `Votos Nuevos` = delta_votos
      )
    
    datatable(df_tabla, options = list(pageLength = 15), rownames = FALSE)
  })
  
  # ---------------------------------------------------------------------------
  # TAB: ANÁLISIS GEOGRÁFICO
  # ---------------------------------------------------------------------------
  output$grafico_geo_ganador <- renderPlotly({
    req(datos_geo())
    
    df_plot <- datos_geo()$resumen
    
    if (input$nivel_geo == "provincia") {
      x_var <- "descProvincia"
    } else if (input$nivel_geo == "canton") {
      x_var <- "descCanton"
    } else {
      x_var <- "descDistritoAdmin"
    }
    
    df_plot <- df_plot %>% arrange(desc(pct_ganador))
    
    plot_ly(df_plot,
            x = as.formula(paste0("~reorder(", x_var, ", -pct_ganador)")),
            y = ~pct_ganador,
            color = ~partido_ganador,
            type = 'bar',
            text = ~paste0(partido_ganador, ": ", round(pct_ganador, 1), "%"),
            hovertemplate = "<b>%{x}</b><br>%{text}<extra></extra>") %>%
      layout(
        xaxis = list(title = "", tickangle = 45),
        yaxis = list(title = "% del Ganador", ticksuffix = "%"),
        showlegend = TRUE,
        barmode = 'group'
      )
  })
  
  output$grafico_geo_participacion <- renderPlotly({
    req(datos_geo())
    
    df_plot <- datos_geo()$resumen
    
    if (input$nivel_geo == "provincia") {
      x_var <- "descProvincia"
    } else if (input$nivel_geo == "canton") {
      x_var <- "descCanton"
    } else {
      x_var <- "descDistritoAdmin"
    }
    
    df_plot <- df_plot %>% arrange(desc(participacion))
    
    plot_ly(df_plot,
            x = as.formula(paste0("~reorder(", x_var, ", -participacion)")),
            y = ~participacion,
            type = 'bar',
            marker = list(color = ~participacion, colorscale = 'Viridis'),
            text = ~paste0(round(participacion, 1), "%"),
            hovertemplate = "<b>%{x}</b><br>Participación: %{y:.1f}%<extra></extra>") %>%
      layout(
        xaxis = list(title = "", tickangle = 45),
        yaxis = list(title = "Participación (%)", ticksuffix = "%"),
        showlegend = FALSE
      )
  })
  
  output$tabla_resultados_geo <- renderDT({
    req(datos_geo())
    
    df_tabla <- datos_geo()$resumen %>%
      mutate(
        electores = format(electores, big.mark = ","),
        votos_emitidos = format(votos_emitidos, big.mark = ","),
        participacion = paste0(round(participacion, 1), "%"),
        pct_ganador = paste0(round(pct_ganador, 1), "%"),
        margen = paste0(round(margen, 1), " pp")
      )
    
    datatable(
      df_tabla,
      options = list(pageLength = 20, scrollX = TRUE),
      rownames = FALSE,
      filter = 'top'
    )
  })
  
  # ---------------------------------------------------------------------------
  # TAB: COMPARATIVO PARTIDOS
  # ---------------------------------------------------------------------------
  output$selector_partido_1 <- renderUI({
    req(resumen_actual())
    partidos <- as.character(resumen_actual()$votos_partido$descPartido)
    selectInput("partido_comp_1", "Partido 1:", choices = partidos, selected = partidos[1])
  })
  
  output$selector_partido_2 <- renderUI({
    req(resumen_actual())
    partidos <- as.character(resumen_actual()$votos_partido$descPartido)
    selected <- if (length(partidos) >= 2) partidos[2] else partidos[1]
    selectInput("partido_comp_2", "Partido 2:", choices = partidos, selected = selected)
  })
  
  output$grafico_comparativo_votos <- renderPlotly({
    req(datos(), input$partido_comp_1, input$partido_comp_2)
    
    evol_1 <- evolucion_partido(datos(), nombre_partido = input$partido_comp_1) %>%
      mutate(partido = input$partido_comp_1)
    evol_2 <- evolucion_partido(datos(), nombre_partido = input$partido_comp_2) %>%
      mutate(partido = input$partido_comp_2)
    
    df_comp <- bind_rows(evol_1, evol_2)
    
    plot_ly(df_comp, x = ~corte, y = ~porcentaje, color = ~partido,
            type = 'scatter', mode = 'lines+markers') %>%
      layout(
        xaxis = list(title = "Corte"),
        yaxis = list(title = "Porcentaje (%)", ticksuffix = "%"),
        showlegend = TRUE,
        shapes = list(
          list(
            type = "line",
            x0 = 0, x1 = 1,
            xref = "paper",
            y0 = 40, y1 = 40,
            line = list(color = "gray", width = 2, dash = "dash")
          )
        )
      )
  })
  
  output$grafico_comparativo_geo <- renderPlotly({
    req(datos_geo(), input$partido_comp_1, input$partido_comp_2)
    
    detalle <- datos_geo()$detalle_partidos
    
    if (input$nivel_geo == "provincia") {
      geo_var <- "descProvincia"
    } else if (input$nivel_geo == "canton") {
      geo_var <- "descCanton"
    } else {
      geo_var <- "descDistritoAdmin"
    }
    
    df_comp <- detalle %>%
      filter(descPartido %in% c(input$partido_comp_1, input$partido_comp_2)) %>%
      group_by(across(all_of(geo_var))) %>%
      mutate(total = sum(votos), pct = votos / total * 100) %>%
      ungroup()
    
    plot_ly(df_comp,
            x = as.formula(paste0("~", geo_var)),
            y = ~pct,
            color = ~descPartido,
            type = 'bar',
            barmode = 'group') %>%
      layout(
        xaxis = list(title = "", tickangle = 45),
        yaxis = list(title = "% entre los dos", ticksuffix = "%"),
        showlegend = TRUE
      )
  })
  
  output$heatmap_partidos_provincia <- renderPlotly({
    req(datos_geo())
    
    detalle <- datos_geo()$detalle_partidos
    
    if (input$nivel_geo != "provincia") {
      return(plotly_empty() %>% layout(title = "Seleccione nivel Provincia"))
    }
    
    # Calcular porcentajes
    df_heat <- detalle %>%
      group_by(descProvincia) %>%
      mutate(total = sum(votos), pct = votos / total * 100) %>%
      ungroup() %>%
      filter(pct >= 3)  # Solo partidos con al menos 3%
    
    plot_ly(df_heat,
            x = ~descProvincia,
            y = ~descPartido,
            z = ~pct,
            type = 'heatmap',
            colorscale = 'Viridis',
            hovertemplate = "<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>") %>%
      layout(
        xaxis = list(title = ""),
        yaxis = list(title = ""),
        margin = list(l = 200)
      )
  })
  
  # ---------------------------------------------------------------------------
  # TAB: ANÁLISIS POR CORTE
  # ---------------------------------------------------------------------------
  output$selector_corte_comparar_1 <- renderUI({
    req(datos())
    cortes <- sort(unique(datos()$NUMEROCORTE[!is.na(datos()$NUMEROCORTE)]))
    selectInput("corte_comp_1", "Corte A:", choices = cortes, selected = min(cortes))
  })
  
  output$selector_corte_comparar_2 <- renderUI({
    req(datos())
    cortes <- sort(unique(datos()$NUMEROCORTE[!is.na(datos()$NUMEROCORTE)]))
    selectInput("corte_comp_2", "Corte B:", choices = cortes, selected = max(cortes))
  })
  
  output$grafico_delta_cortes <- renderPlotly({
    req(datos())
    
    cortes <- sort(unique(datos()$NUMEROCORTE[!is.na(datos()$NUMEROCORTE)]))
    
    deltas <- map_dfr(cortes, function(c) {
      delta <- calcular_delta_corte(datos(), c)
      delta %>%
        group_by(descPartido) %>%
        summarise(votos = sum(votos_delta, na.rm = TRUE), .groups = "drop") %>%
        mutate(corte = c)
    })
    
    # Top 5 partidos
    top_partidos <- deltas %>%
      group_by(descPartido) %>%
      summarise(total = sum(votos)) %>%
      arrange(desc(total)) %>%
      head(5) %>%
      pull(descPartido)
    
    df_plot <- deltas %>% filter(descPartido %in% top_partidos)
    
    plot_ly(df_plot, x = ~corte, y = ~votos, color = ~descPartido, type = 'bar') %>%
      layout(
        xaxis = list(title = "Corte"),
        yaxis = list(title = "Votos Nuevos"),
        barmode = 'stack'
      )
  })
  
  output$grafico_acumulado_cortes <- renderPlotly({
    req(datos())
    
    cortes <- sort(unique(datos()$NUMEROCORTE[!is.na(datos()$NUMEROCORTE)]))
    
    acum_data <- map_dfr(cortes, function(c) {
      res <- calcular_resumen_nacional(datos(), c, "acumulado")
      res$votos_partido %>%
        head(5) %>%
        select(descPartido, votos, porcentaje) %>%
        mutate(corte = c)
    })
    
    plot_ly(acum_data, x = ~corte, y = ~porcentaje, color = ~descPartido,
            type = 'scatter', mode = 'lines+markers') %>%
      layout(
        xaxis = list(title = "Corte"),
        yaxis = list(title = "Porcentaje Acumulado (%)", ticksuffix = "%"),
        shapes = list(
          list(
            type = "line",
            x0 = 0, x1 = 1,
            xref = "paper",
            y0 = 40, y1 = 40,
            line = list(color = "red", width = 2, dash = "dash")
          )
        )
      )
  })
  
  output$tabla_detalle_cortes <- renderDT({
    req(evolucion_data())
    
    datatable(
      evolucion_data() %>%
        mutate(across(where(is.numeric), ~round(., 2))),
      options = list(pageLength = 15, scrollX = TRUE),
      rownames = FALSE
    )
  })
  
  # ---------------------------------------------------------------------------
  # TAB: ANÁLISIS POR JUNTA
  # ---------------------------------------------------------------------------
  output$filtro_provincia_junta <- renderUI({
    req(datos())
    provincias <- unique(as.character(datos()$descProvincia))
    selectInput("filtro_prov", "Provincia:", 
                choices = c("Todas" = "", sort(provincias[!is.na(provincias)])))
  })
  
  output$filtro_canton_junta <- renderUI({
    req(datos())
    if (is.null(input$filtro_prov) || input$filtro_prov == "") {
      cantones <- unique(as.character(datos()$descCanton))
    } else {
      cantones <- datos() %>%
        filter(descProvincia == input$filtro_prov) %>%
        pull(descCanton) %>%
        unique() %>%
        as.character()
    }
    selectInput("filtro_cant", "Cantón:",
                choices = c("Todos" = "", sort(cantones[!is.na(cantones)])))
  })
  
  output$filtro_distrito_junta <- renderUI({
    req(datos())
    if (is.null(input$filtro_cant) || input$filtro_cant == "") {
      distritos <- unique(as.character(datos()$descDistritoAdmin))
    } else {
      distritos <- datos() %>%
        filter(descCanton == input$filtro_cant) %>%
        pull(descDistritoAdmin) %>%
        unique() %>%
        as.character()
    }
    selectInput("filtro_dist", "Distrito:",
                choices = c("Todos" = "", sort(distritos[!is.na(distritos)])))
  })
  
  output$filtro_partido_junta <- renderUI({
    req(datos())
    partidos <- unique(as.character(datos()$descPartido))
    selectInput("filtro_part", "Partido:",
                choices = c("Todos" = "", sort(partidos[!is.na(partidos)])))
  })
  
  datos_juntas_filtrados <- reactive({
    req(datos())
    
    df <- if (input$modo_corte == "total") {
      calcular_total_todos_cortes(datos())
    } else {
      req(input$corte_global)
      calcular_acumulado_hasta_corte(datos(), as.integer(input$corte_global))
    }
    
    if (!is.null(input$filtro_prov) && input$filtro_prov != "") {
      df <- df %>% filter(descProvincia == input$filtro_prov)
    }
    if (!is.null(input$filtro_cant) && input$filtro_cant != "") {
      df <- df %>% filter(descCanton == input$filtro_cant)
    }
    if (!is.null(input$filtro_dist) && input$filtro_dist != "") {
      df <- df %>% filter(descDistritoAdmin == input$filtro_dist)
    }
    if (!is.null(input$filtro_part) && input$filtro_part != "") {
      df <- df %>% filter(descPartido == input$filtro_part)
    }
    
    df
  })
  
  output$tabla_juntas <- renderDT({
    req(datos_juntas_filtrados())
    
    df_tabla <- datos_juntas_filtrados() %>%
      select(
        Provincia = descProvincia,
        Cantón = descCanton,
        Distrito = descDistritoAdmin,
        Junta = junta,
        Partido = descPartido,
        Votos = votos,
        Electores = electores
      ) %>%
      arrange(Provincia, Cantón, Distrito, Junta, desc(Votos))
    
    datatable(
      df_tabla,
      options = list(pageLength = 25, scrollX = TRUE),
      rownames = FALSE,
      filter = 'top'
    )
  })
  
  output$histograma_votos_junta <- renderPlotly({
    req(datos_juntas_filtrados())
    
    df_hist <- datos_juntas_filtrados() %>%
      group_by(junta) %>%
      summarise(total_votos = sum(votos, na.rm = TRUE), .groups = "drop")
    
    plot_ly(df_hist, x = ~total_votos, type = 'histogram', nbinsx = 30) %>%
      layout(
        xaxis = list(title = "Votos por Junta"),
        yaxis = list(title = "Frecuencia")
      )
  })
  
  output$stats_juntas <- renderDT({
    req(datos_juntas_filtrados())
    
    df_stats <- datos_juntas_filtrados() %>%
      group_by(junta) %>%
      summarise(
        total_votos = sum(votos, na.rm = TRUE),
        electores = first(na.omit(electores)),
        .groups = "drop"
      ) %>%
      mutate(
        total_votos = replace_na(total_votos, 0),
        electores = replace_na(electores, 0)
      ) %>%
      summarise(
        Métrica = c("Total Juntas", "Media Votos/Junta", "Mediana", "Desv. Est.", 
                    "Mín", "Máx", "Q1", "Q3"),
        Valor = c(
          n(),
          round(mean(total_votos, na.rm = TRUE), 1),
          round(median(total_votos, na.rm = TRUE), 1),
          round(sd(total_votos, na.rm = TRUE), 1),
          min(total_votos, na.rm = TRUE),
          max(total_votos, na.rm = TRUE),
          round(quantile(total_votos, 0.25, na.rm = TRUE), 1),
          round(quantile(total_votos, 0.75, na.rm = TRUE), 1)
        )
      )
    
    datatable(df_stats, options = list(dom = 't'), rownames = FALSE)
  })
  
  # ---------------------------------------------------------------------------
  # TAB: EXPORTAR DATOS
  # ---------------------------------------------------------------------------
  datos_exportacion <- reactive({
    req(datos())
    
    tipo <- input$tipo_exportacion
    
    switch(tipo,
           "resumen_total" = {
             res <- calcular_resumen_total(datos())
             res$votos_partido
           },
           "resumen_corte" = {
             req(input$corte_global)
             res <- calcular_resumen_nacional(datos(), as.integer(input$corte_global), "acumulado")
             res$votos_partido
           },
           "provincia" = {
             cortes <- sort(unique(datos()$NUMEROCORTE))
             geo <- calcular_resultados_geograficos(datos(), max(cortes), "provincia")
             geo$resumen
           },
           "canton" = {
             cortes <- sort(unique(datos()$NUMEROCORTE))
             geo <- calcular_resultados_geograficos(datos(), max(cortes), "canton")
             geo$resumen
           },
           "distrito" = {
             cortes <- sort(unique(datos()$NUMEROCORTE))
             geo <- calcular_resultados_geograficos(datos(), max(cortes), "distrito")
             geo$resumen
           },
           "evolucion" = {
             evolucion_data()
           },
           "metricas_cp" = {
             res <- calcular_resumen_total(datos())
             mc <- res$metricas_cp
             tibble(
               Métrica = names(mc),
               Valor = as.character(unlist(mc))
             )
           },
           "completo" = {
             calcular_total_todos_cortes(datos())
           }
    )
  })
  
  output$preview_exportacion <- renderDT({
    req(datos_exportacion())
    datatable(
      head(datos_exportacion(), 100),
      options = list(scrollX = TRUE, pageLength = 10),
      rownames = FALSE
    )
  })
  
  output$btn_descargar <- downloadHandler(
    filename = function() {
      ext <- input$formato_exportacion
      tipo <- input$tipo_exportacion
      paste0("electoral_cr2026_", tipo, "_", Sys.Date(), ".", ext)
    },
    content = function(file) {
      df <- datos_exportacion()
      if (input$formato_exportacion == "xlsx") {
        writexl::write_xlsx(df, file)
      } else {
        write.csv(df, file, row.names = FALSE)
      }
    }
  )
  
}

# =============================================================================
# EJECUTAR APLICACIÓN
# =============================================================================
shinyApp(ui = ui, server = server)