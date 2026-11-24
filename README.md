# Proyecto E-VRPTW — Optimización (580451)

**Universidad de Concepción**  
**Equipo:** Grupo 4 (Martín González, Mariel Muñoz, Javier Cadagán, Jhostian San Martín, Javier Torres)  
**Docente:** Dra. Rosa Medina Durán  

Implementación y análisis computacional de un modelo de Programación Lineal Entera Mixta (PLEM) para el **Problema de Ruteo de Vehículos Eléctricos con Ventanas de Tiempo y Estaciones de Recarga Intermedias (E-VRPTW)** basado en Schneider et al. (2014).

---

## 1. Tablero de Avance y Plan de Trabajo Secuencial

El desarrollo está organizado en tickets secuenciales. Cualquier integrante disponible puede tomar el siguiente ticket abierto respetando las dependencias:

| Ticket | Tarea | Estado | Depende de | Entregable / Criterio de Cierre |
| :--- | :--- | :---: | :---: | :--- |
| **T1** | Entorno, repositorio Git y verificación de solver | ✅ Completado | — | Repo configurado, `.gitignore` activo, `venv` con `gurobipy` validado en local. |
| **T2** | Descarga y parser de instancias Schneider (2014) | ✅ Completado | — | Datasets en `/data` (`c101_21`, `r101_21`, `rc101_21`) y `src/parser.py` operativo. |
| **T3** | Cierre algebraico y cotas Big-M | ✅ Completado | — | Formulación PLEM completa documentada en `modelo_matematico.md`. |
| **T4** | Codificación del modelo PLEM (`src/model.py`) | ⬜ Pendiente | T1, T2, T3 | Modelo implementado en `gurobipy` leyendo el diccionario de `parser.py`. |
| **T5** | Validación y auditoría en instancias Toy ($n=5, 10$) | ⬜ Pendiente | T4 | Solución óptima verificada sin subtours, con recargas y cumplimiento de ventanas. |
| **T6** | Benchmarking en `chome.inf.udec.cl` ($n=25, 50$) | ⬜ Pendiente | T5 | Corridas ejecutadas en servidor; métricas y *MIP Gap* guardados en `/results`. |
| **T7** | Visualización de rutas e informe/presentación final | ⬜ Pendiente | T5, T6 | Gráficos 2D de rutas, perfiles de batería (SoC) y entrega final cerrada. |

---

## 2. Especificación de los Próximos Tickets

### Ticket 4: Implementación del Modelo (`src/model.py`)
* **Entrada:** Usar `load_evrptw_instance()` desde `src/parser.py`, que entrega las llaves `V`, `V_0`, `V_C`, `V_R`, `nodes`, `dist`, `time`, `energy`, `Q_bat`, `C_cap`, `h_rate`, `g_rate`.
* **Implementación:** Traducir exactamente las 12 restricciones y las cotas M<sup>(1)</sup><sub>ij</sub> y M<sup>(2)</sup><sub>rj</sub> definidas en `modelo_matematico.md` (recordar crear el nodo virtual de retorno `depot_end = len(V)`).
* **Salida:** Exportar un `.json` en `/results` con arcos activos ($x_{ijk}=1$), tiempos $T_{ik}$, niveles de batería $Y_{ik}$, valor objetivo, cota dual, *MIP Gap* y tiempo de CPU.

### Ticket 5: Validación en Instancias Reducidas ($n=5$ y $n=10$)
* Recortar instancias usando `max_customers=5` y `max_customers=10` en `load_evrptw_instance()`.
* Verificar que ningún vehículo viole $[e_i, l_i]$, que no existan subtours y que, al reducir $Q_{\text{bat}}$, los vehículos se desvíen efectivamente a nodos de `V_R` sumando el tiempo de recarga $\Delta t_r = g(Q_{\text{bat}} - Y_{rk})$.

### Ticket 6: Experimentación en Servidor DIICC ($n=25$ y $n=50$)
* Clonar o actualizar el repositorio en `chome.inf.udec.cl` y ejecutar dentro de `tmux`.
* Evaluar instancias agrupadas (`c101_21`), aleatorias (`r101_21`) y mixtas (`rc101_21`) con límite de tiempo definido, consolidando los resultados en `results/benchmark_summary.csv`.

### Ticket 7: Visualización y Entrega Final
* Crear `src/visualize.py` para graficar los mapas de rutas (depósito, clientes y estaciones visitadas) y las curvas de estado de carga de batería ($Y_{ik}$) por vehículo.

---

## 3. Estructura del Proyecto

```text
evrptw-optimizacion/
├── data/                    # Instancias estándar de Schneider et al. (.txt)
├── src/
│   ├── parser.py            # Lectura de instancias, replicación de estaciones y matrices
│   ├── model.py             # (Ticket 4) Formulación PLEM en GurobiPy
│   └── visualize.py         # (Ticket 7) Gráficos de rutas y perfiles de batería
├── results/                 # Logs del solver, soluciones .json y tablas .csv
├── modelo_matematico.md     # Definición algebraica formal y cotas Big-M
└── README.md                # Plan de trabajo y guía de ejecución
```

---

## 4. Instalación Local y Acceso al Servidor (`chome.inf.udec.cl`)

### Ejecución en equipo local (Windows / Linux / Mac)
```bash
git clone https://github.com/JavierTorresO/evrptw-optimizacion.git
cd evrptw-optimizacion
python -m venv venv
# Activar entorno (Windows PowerShell): .\venv\Scripts\Activate.ps1
# Activar entorno (Linux/Mac): source venv/bin/activate
pip install gurobipy numpy pandas matplotlib
python src/parser.py
```

### Conexión al Servidor DIICC (desde red UdeC o VPN institucional)
```bash
ssh grupo04@chome.inf.udec.cl
```
*(La contraseña de la cuenta `grupo04` se resguarda localmente en `credenciales_servidor.txt` —ignorado por Git— y en el chat de coordinación del equipo. Para corridas largas en el servidor, utilizar `tmux new -s evrptw`).*
