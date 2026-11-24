# Proyecto E-VRPTW — Optimización (580451)

**Universidad de Concepción**  
**Equipo:** Grupo 4 (Martín González, Mariel Muñoz, Javier Cadagán, Jhostian San Martín, Javier Torres)  
**Docente:** Dra. Rosa Medina Durán  

Implementación y comparación computacional (Gurobi vs. CPLEX) de un modelo de Programación Lineal Entera Mixta (PLEM) para el **Problema de Ruteo de Vehículos Eléctricos con Ventanas de Tiempo y Estaciones de Recarga Intermedias (E-VRPTW)** basado en Schneider et al. (2014).

---

## 1. Tablero de Avance y Plan de Trabajo (Alineado a Rúbrica Final)

El desarrollo está organizado en tickets secuenciales. Cualquier integrante disponible puede tomar el siguiente ticket abierto respetando las dependencias:

| Ticket | Tarea | Estado | Depende de | Entregable / Criterio de Cierre (Rúbrica) |
| :--- | :--- | :---: | :---: | :--- |
| **T1** | Entorno, repo Git y verificación de solvers | ✅ Completado | — | Repo listo, `venv` operativo en local; validar licencia CPLEX al conectar a `chome`. |
| **T2** | Parser de instancias Schneider (2014) | ✅ Completado | — | `src/parser.py` operativo con replicación de estaciones y recorte dinámico. |
| **T3** | Cierre algebraico y cotas Big-M | ✅ Completado | — | Formulación PLEM completa documentada en `modelo_matematico.md`. |
| **T4** | Implementación PLEM en **Gurobi y CPLEX** | ⬜ Pendiente | T1, T2, T3 | Scripts `src/model_gurobi.py` y `src/model_cplex.py` con `TimeLimit=3600s`. |
| **T5** | Validación Toy y **Diseño de Instancias (≥3/cat)** | ⬜ Pendiente | T4 | Óptimo idéntico en ambos solvers ($n=5, 10$) y batería de ≥3 instancias por característica. |
| **T6** | Benchmarking **Gurobi vs. CPLEX** en `chome` | ⬜ Pendiente | T5 | Tabla CSV con Tiempo, *MIPGap (%)* y *Best Objective* para ambos solvers (≤1 hr). |
| **T7** | Análisis Crítico: **Supuestos, Limitaciones y Solvers** | ⬜ Pendiente | T6 | Evaluación crítica de supuestos del modelo y comparación de escalabilidad Gurobi/CPLEX. |
| **T8** | Visualización de Rutas y Métricas (`visualize.py`) | ⬜ Pendiente | T6 | Mapas 2D de rutas, perfiles de batería (SoC) y gráficos comparativos de desempeño. |
| **T9** | **Presentación Final (~15 min) + Guion Equilibrado** | ⬜ Pendiente | T7, T8 | Diapositivas completas, guion cronometrado (3 min/integrante) y preparación de Q&A. |

---

## 2. Especificación Técnica de los Próximos Tickets

### Ticket 4: Codificación Dual del Modelo (`model_gurobi.py` y `model_cplex.py`)
* **Entrada:** Usar `load_evrptw_instance()` desde `src/parser.py`.
* **Implementación:** Programar exactamente las 12 restricciones y cotas M<sup>(1)</sup><sub>ij</sub> y M<sup>(2)</sup><sub>rj</sub> de `modelo_matematico.md` en ambos solvers (`gurobipy` y `docplex`), fijando un límite máximo de ejecución de **3600 segundos (1 hora)** por instancia.
* **Salida estandarizada:** Ambos scripts deben exportar un `.json` en `/results` con la misma estructura: `solver`, `instance`, `n_customers`, `status`, `best_objective`, `best_bound`, `mip_gap`, `cpu_time`, `nodes_explored` y rutas activas.

### Ticket 5: Validación Toy y Diseño de Batería de Instancias (Mínimo 3 por característica)
* **Validación cruzada ($n=5, 10$):** Correr Gurobi y CPLEX sobre los mismos subconjuntos pequeños y confirmar que ambos alcanzan exactamente el mismo valor objetivo sin subtours ni violaciones de batería/tiempo.
* **Diseño de instancias (Criterio Rúbrica):** Seleccionar y documentar **al menos 3 instancias por cada característica** evaluada (ej. 3 instancias Agrupadas `c101, c102, c103`, 3 Aleatorias `r101, r102, r103` y 3 Mixtas `rc101, rc102, rc103`, evaluadas en escalas de $n=15$ y $n=25$), justificando cómo cada característica desafía el ruteo y la autonomía.

### Ticket 6: Benchmarking Comparativo en Servidor DIICC (`chome.inf.udec.cl`)
* Verificar `cplex` y `gurobi_cl` en `chome.inf.udec.cl` y lanzar el script maestro `src/benchmark.py` dentro de `tmux`.
* Consolidar todas las corridas en `results/comparacion_solvers.csv` reportando obligatoriamente para Gurobi y CPLEX: **Tiempo de cómputo (s), MIPGap (%) y Best objective / incumbent**.

### Ticket 7: Evaluación Crítica de Supuestos, Limitaciones y Escalabilidad
* Redactar en `analisis_resultados.md` dos bloques clave exigidos por la pauta:
  1. **Supuestos y Limitaciones:** Evaluar críticamente el impacto operativo de asumir recarga completa obligatoria ($Q_{\text{bat}}$), tasa de consumo lineal independiente de la carga transportada, velocidad constante y ausencia de colas en estaciones.
  2. **Comparación Gurobi vs. CPLEX:** Analizar diferencias en cierre de brecha (*MIPGap*), calidad de cotas duales, velocidad de exploración de nodos y punto de quiebre al escalar el tamaño de instancia.

### Ticket 8: Visualización de Rutas y Comparativas (`src/visualize.py`)
* Generar figuras limpias para las diapositivas: mapas 2D de rutas (depósito, clientes y estaciones usadas), curvas de evolución de batería ($Y_{ik}$) y gráficos de barras/líneas comparando tiempos y *MIPGap* entre Gurobi y CPLEX.

### Ticket 9: Presentación Final (~15 min) y Guion del Equipo
* Armar las diapositivas cubriendo todos los bloques de la rúbrica:
  1. **Integración de correcciones previas:** Evolución desde VRPTW hacia E-VRPTW (Schneider et al., 2014) y estructura del equipo.
  2. **Modelo matemático PLEM:** Conjuntos, parámetros, variables, función objetivo y restricciones clave.
  3. **Supuestos y limitaciones:** Justificación e impacto crítico.
  4. **Diseño y diversidad de instancias:** Justificación de las ≥3 instancias por característica.
  5. **Resultados y comparación Gurobi vs. CPLEX:** Tablas con Tiempo, *MIPGap* y *Best Objective* (límite 1 hr) + análisis de escalabilidad.
* Redactar un **guion cronometrado de 15 minutos totales** (~3 minutos por cada uno de los 5 integrantes) y un anexo con posibles preguntas de la profesora.

---

## 3. Estructura del Proyecto

```text
evrptw-optimizacion/
├── data/                    # Instancias estándar de Schneider et al. (.txt)
├── src/
│   ├── parser.py            # Lectura de instancias, replicación de estaciones y matrices
│   ├── model_gurobi.py      # (Ticket 4) Formulación PLEM en GurobiPy
│   ├── model_cplex.py       # (Ticket 4) Formulación PLEM en DOcplex (CPLEX)
│   ├── benchmark.py         # (Ticket 6) Ejecución automatizada Gurobi vs. CPLEX
│   └── visualize.py         # (Ticket 8) Gráficos de rutas, SoC y comparativas
├── results/                 # Logs, soluciones .json y comparacion_solvers.csv
├── modelo_matematico.md     # Definición algebraica formal y cotas Big-M
├── analisis_resultados.md   # (Ticket 7) Supuestos, limitaciones y análisis comparativo
└── README.md                # Plan de trabajo y guía de ejecución
```

---

## 4. Instalación Local y Acceso al Servidor (`chome.inf.udec.cl`)

### Ejecución en equipo local
```bash
git clone [https://github.com/JavierTorresO/evrptw-optimizacion.git](https://github.com/JavierTorresO/evrptw-optimizacion.git)
cd evrptw-optimizacion
python -m venv venv
# Windows PowerShell: .\venv\Scripts\Activate.ps1
# Linux/Mac: source venv/bin/activate
pip install gurobipy docplex cplex numpy pandas matplotlib
python src/parser.py
```

### Conexión al Servidor DIICC (desde red UdeC o VPN institucional)
```bash
ssh grupo04@chome.inf.udec.cl
```
*(La contraseña de `grupo04` se resguarda localmente en `credenciales_servidor.txt` —ignorado por Git— y en el chat de coordinación del equipo. Usar `tmux new -s evrptw` para experimentos largos).*
