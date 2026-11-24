# Formulación Matemática (PLEM): E-VRPTW con Estaciones de Recarga

**Referencia Base:** Schneider, Stenger & Goeke (2014)

---

## 1. Conjuntos e Índices

Para evitar conflictos entre las variables de tiempo y batería al salir frente al regresar al depósito, se desdobla el nodo depósito en un origen ($0$) y un destino ($N+1$):

* $V_0 = \{0\}$: Depósito de salida (los vehículos parten con batería al $100\%$).
* $V_{N+1} = \{N+1\}$: Depósito de retorno (copia espacial del nodo $0$).
* $V_C = \{1, \dots, n\}$: Conjunto de clientes a abastecer.
* $V_R$: Conjunto de nodos de estaciones de recarga (incluye las copias ficticias generadas por `parser.py` para permitir múltiples visitas).
* $V = V_0 \cup V_C \cup V_R \cup V_{N+1}$: Conjunto total de nodos del grafo.
* $V'_0 = V_0 \cup V_C \cup V_R$: Nodos desde los cuales puede salir un arco.
* $V'_{N+1} = V_C \cup V_R \cup V_{N+1}$: Nodos a los cuales puede llegar un arco.
* $K = \{1, \dots, m\}$: Flota homogénea de vehículos eléctricos disponibles.

---

## 2. Parámetros

* $d_{ij}$: Distancia euclidiana entre el nodo $i$ y el nodo $j$.
* $t_{ij}$: Tiempo de viaje entre $i$ y $j$, calculado como $t_{ij} = d_{ij} / v$.
* $q_i$: Demanda de carga del cliente $i \in V_C$ ($q_i = 0$ para depósitos y estaciones).
* $[e_i, l_i]$: Ventana de tiempo permitida para iniciar el servicio en el nodo $i \in V$ ($[0, l_0]$ en depósitos y estaciones).
* $s_i$: Tiempo de descarga o servicio en el cliente $i \in V_C$ ($s_i = 0$ para depósitos y estaciones).
* $C$: Capacidad máxima de carga física de cada vehículo.
* $Q_{\text{bat}}$: Capacidad máxima de la batería del vehículo.
* $h$: Tasa de consumo energético por unidad de distancia recorrida.
* $g$: Tasa inversa de recarga (tiempo requerido para recargar $1$ unidad de batería).

---

## 3. Variables de Decisión

* $x_{ijk} \in \{0, 1\}$: Variable binaria igual a $1$ si el vehículo $k \in K$ viaja directamente del nodo $i \in V'_0$ al nodo $j \in V'_{N+1}$ ($i \neq j$), y $0$ en caso contrario.
* $T_{ik} \ge 0$: Variable continua que indica el instante de inicio de atención (o llegada) del vehículo $k \in K$ en el nodo $i \in V$.
* $Y_{ik} \in [0, Q_{\text{bat}}]$: Variable continua que representa el estado de carga de la batería (*State of Charge*) del vehículo $k \in K$ al arribar al nodo $i \in V$.

---

## 4. Función Objetivo

Minimizar la distancia total recorrida por toda la flota:

$$\min Z = \sum_{k \in K} \sum_{i \in V'_0} \sum_{\substack{j \in V'_{N+1} \\ j \neq i}} d_{ij} \, x_{ijk}$$

*(Nota: Si se desea minimizar también el número de vehículos despachados, se agrega el término $+ W \sum_{k \in K} \sum_{j \in V_C \cup V_R} x_{0jk}$ con un costo fijo $W$).*

---

## 5. Restricciones del Modelo

### 5.1. Asignación y Conservación de Flujo

1. **Visita única a cada cliente:**
   $$\sum_{k \in K} \sum_{\substack{j \in V'_{N+1} \\ j \neq i}} x_{ijk} = 1 \quad \forall i \in V_C$$

2. **Uso máximo de una vez por copia de estación de recarga:**
   $$\sum_{k \in K} \sum_{\substack{j \in V'_{N+1} \\ j \neq r}} x_{rjk} \le 1 \quad \forall r \in V_R$$

3. **Salida y retorno al depósito (permite dejar vehículos sin usar):**
   $$\sum_{j \in V_C \cup V_R} x_{0jk} \le 1 \quad \forall k \in K$$
   $$\sum_{j \in V_C \cup V_R} x_{0jk} = \sum_{i \in V_C \cup V_R} x_{i, N+1, k} \quad \forall k \in K$$

4. **Conservación de flujo en clientes y estaciones:**
   $$\sum_{\substack{i \in V'_0 \\ i \neq j}} x_{ijk} - \sum_{\substack{l \in V'_{N+1} \\ l \neq j}} x_{jlk} = 0 \quad \forall j \in V_C \cup V_R, \ \forall k \in K$$

### 5.2. Capacidad Física

5. **Capacidad máxima de carga del vehículo:**
   $$\sum_{i \in V_C} q_i \sum_{\substack{j \in V'_{N+1} \\ j \neq i}} x_{ijk} \le C \quad \forall k \in K$$

### 5.3. Causalidad Temporal y Ventanas de Tiempo

6. **Avance temporal desde el depósito y clientes** (sin recarga):
   $$T_{jk} \ge T_{ik} + s_i + t_{ij} - M^{(1)}_{ij}(1 - x_{ijk}) \quad \forall i \in V_0 \cup V_C, \ \forall j \in V'_{N+1} \ (i \neq j), \ \forall k \in K$$

7. **Avance temporal desde estaciones de recarga** (acopla el tiempo de recarga completa $\Delta t_r = g(Q_{\text{bat}} - Y_{rk})$):
   $$T_{jk} \ge T_{rk} + g(Q_{\text{bat}} - Y_{rk}) + t_{rj} - M^{(2)}_{rj}(1 - x_{rjk}) \quad \forall r \in V_R, \ \forall j \in V'_{N+1} \ (r \neq j), \ \forall k \in K$$

8. **Cumplimiento estricto de ventanas de tiempo:**
   $$e_i \le T_{ik} \le l_i \quad \forall i \in V, \ \forall k \in K$$

### 5.4. Dinámica Energética (Estado de Carga de Batería)

9. **Consumo de batería al salir del depósito o de una estación** (salen recargados al $100\%$):
   $$Y_{jk} \le Q_{\text{bat}} - h \cdot d_{ij} \, x_{ijk} \quad \forall i \in V_0 \cup V_R, \ \forall j \in V'_{N+1} \ (i \neq j), \ \forall k \in K$$

10. **Consumo de batería al salir de un cliente:**
    $$Y_{jk} \le Y_{ik} - h \cdot d_{ij} \, x_{ijk} + Q_{\text{bat}}(1 - x_{ijk}) \quad \forall i \in V_C, \ \forall j \in V'_{N+1} \ (i \neq j), \ \forall k \in K$$

11. **Condiciones iniciales en el depósito de salida:**
    $$T_{0k} = 0, \quad Y_{0k} = Q_{\text{bat}} \quad \forall k \in K$$

### 5.5. Ruptura de Simetría de Flota

12. **Ordenamiento lexicográfico de vehículos** (evita explorar permutaciones idénticas):
    $$\sum_{j \in V_C \cup V_R} x_{0, j, k+1} \le \sum_{j \in V_C \cup V_R} x_{0, j, k} \quad \forall k \in \{1, \dots, m-1\}$$

---

## 6. Cotas Big-M Ajustadas

Para mantener una relajación lineal estrecha en el solver, en `model.py` se calcula el valor mínimo válido por cada par de nodos $(i, j)$:

* **Para arcos desde depósito o clientes:**
  $$M^{(1)}_{ij} = \max\{0, \ l_i + s_i + t_{ij} - e_j\}$$

* **Para arcos desde estaciones de recarga** (peor caso: arribo con batería $0$ y recarga completa $Q_{\text{bat}}$):
  $$M^{(2)}_{rj} = \max\{0, \ l_r + g \cdot Q_{\text{bat}} + t_{rj} - e_j\}$$

* **Para energía:** La cota exacta es $Q_{\text{bat}}$, ya incorporada directamente en las restricciones 9 y 10.

---

## 7. Nota de Implementación (`src/model.py`)

En `src/parser.py` el depósito está indexado como `0`. Al construir el modelo en Gurobi, se debe crear el índice virtual `depot_end = len(data["V"])` copiando las coordenadas y ventanas de `nodes[0]`. De ese modo $T_{0k} = 0$ y $Y_{0k} = Q_{\text{bat}}$ fijan las condiciones de partida, mientras que $T_{\text{end}, k}$ y $Y_{\text{end}, k}$ registran la hora de arribo y la energía residual al retornar al depósito.