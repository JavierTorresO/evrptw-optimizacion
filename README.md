# Proyecto E-VRPTW — Optimización Grupo 04

**Universidad de Concepción**  
**Equipo:** Martín González, Mariel Muñoz, Javier Cadagán, Jhostian San Martín, Javier Torres  
**Docente:** Dra. Rosa Medina Durán  

Implementación y comparación computacional (Gurobi vs. CPLEX) de un modelo PLEM para el Problema de Ruteo de Vehículos Eléctricos con Ventanas de Tiempo y Estaciones de Recarga Intermedias **(E-VRPTW)** basado en Schneider et al. (2014).



## Estructura del proyecto
```text
evrptw-optimizacion/
├── data/                    # Instancias oficiales de Schneider et al. (2014)
├── src/
│   ├── parser.py            # Lectura de instancias, copias de estaciones y poda de arcos
│   ├── model_gurobi.py      # Modelo PLEM en GurobiPy
│   ├── model_cplex.py       # Modelo PLEM en DOcplex (CPLEX)
│   ├── validator.py         # Simulador y validador operativo (tiempos y SoC reales)
│   ├── benchmark.py         # (T6) Ejecución automatizada Gurobi vs. CPLEX
│   └── visualize.py         # (T8) Mapas 2D de rutas, perfiles SoC y comparativas
├── results/                 # Soluciones .json y tabla comparacion_solvers.csv
├── modelo_matematico.md     # Definición formal del PLEM y cotas Big-M
└── README.md
```
## Instancias
En `data/` se incluyen las instancias oficiales de Schneider et al. (2014) (DOI: `10.17632/h3mrm5dhxw.1`), cubriendo las tres distribuciones espaciales:
* **Agrupadas (`C`):** clientes en clústeres (`c101..c109`, `c201..c208` y pequeñas `C5/C10/C15`).
* **Aleatorias (`R`):** distribución uniforme (`r101..r112`, `r201..r211` y pequeñas `C5/C10/C15`).
* **Mixtas (`RC`):** combinación de clústeres y puntos dispersos (`rc101..rc108`, `rc201..rc208` y pequeñas `C5/C10/C15`).
Para las pruebas se usan al menos 3 instancias por familia:
* **Validación y escala chica/mediana:** `C5`, `C10` y `C15` oficiales (3–8 estaciones, con recargas activas).
* **Estrés / punto de quiebre:** recortes de `c101..c103_21`, `r101..r103_21` y `rc101..rc103_21` (`n=15, 25`).

## Uso rápido
### Local
```bash
git clone https://github.com/JavierTorresO/evrptw-optimizacion.git
cd evrptw-optimizacion
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Pruebas individuales:
```bash
python src/parser.py
python src/model_gurobi.py
python src/model_cplex.py
python src/validator.py
```
### Servidor DIICC (`chome.inf.udec.cl`)
El servidor ya tiene configurado `.venv` (Python 3.12) con **Gurobi 14** (licencia WLS en `~/gurobi.lic`) y **CPLEX 22.2.0 Académico** (`~/cplex_academic`). No es necesario reinstalar paquetes.
1. Conectarse (desde red UdeC o VPN institucional; la clave de `grupo04` está en `credenciales_servidor.txt`):
```bash
ssh grupo04@chome.inf.udec.cl
```
2. Entrar al proyecto, actualizar código y activar el entorno:
```bash
cd ~/evrptw-optimizacion
git pull
source .venv/bin/activate
```
3. Para experimentos largos, usar `tmux` (evita que se corten si se cierra el SSH):
```bash
tmux new -s evrptw          # crear sesión (Ctrl+B luego D para desconectarse sin detenerla)
tmux attach -t evrptw       # volver a la sesión
```

##  Estado de avance

| Ticket | Descripción | Estado |
| :--- | :--- | :--- |
| **T1** | Entorno local, repositorio Git y solvers | ✅ |
| **T2** | Parser de instancias Schneider (`src/parser.py`) y poda de arcos | ✅ |
| **T3** | Formulación matemática PLEM y cotas Big-M (`modelo_matematico.md`) | ✅ |
| **T4** | Modelos en Gurobi y CPLEX (`model_gurobi.py`, `model_cplex.py`) | ✅ |
| **T5** | Validación operativa (`src/validator.py`) y batería de instancias (≥3 por familia) | ✅ |
| **T6** | Benchmarking Gurobi vs. CPLEX en `chome` (`src/benchmark.py`) | Pendiente |
| **T7** | Análisis de supuestos, limitaciones y escalabilidad (`analisis_resultados.md`) | Pendiente |
| **T8** | Visualización de rutas, SoC y gráficos comparativos (`src/visualize.py`) | Pendiente |
| **T9** | Presentación final (~15 min) y guion del equipo | Pendiente |



## Especificación Técnica de los Próximos Tickets

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
