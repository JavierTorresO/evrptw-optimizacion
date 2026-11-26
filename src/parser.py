import re
import math
from pathlib import Path


def load_evrptw_instance(filepath: str, station_copies: int = 2, max_customers: int | None = None) -> dict:
    """
    Lee una instancia estándar de Schneider et al. (2014) para E-VRPTW.
    
    Args:
        filepath: Ruta al archivo .txt de la instancia.
        station_copies: Número de copias por estación para permitir múltiples visitas.
        max_customers: Si se especifica (ej. 5, 10, 25), recorta los primeros n clientes.
        
    Returns:
        Diccionario estandarizado con conjuntos, parámetros y matrices.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {filepath}")

    depot_raw = None
    stations_raw = []
    customers_raw = []
    params = {}

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        # Saltar encabezado
        if line.startswith("StringID"):
            continue

        # Detectar líneas de parámetros al final: Ej. "Q Vehicle fuel tank capacity /77.75/"
        param_match = re.search(r"^([QCr gv])\s+.*?/([0-9.]+)/", line)
        if param_match:
            key = param_match.group(1)
            val = float(param_match.group(2))
            params[key] = val
            continue

        # Parsear filas de nodos
        parts = line.split()
        if len(parts) >= 8:
            node = {
                "string_id": parts[0],
                "type": parts[1].lower(),
                "x": float(parts[2]),
                "y": float(parts[3]),
                "demand": float(parts[4]),
                "ready_time": float(parts[5]),
                "due_date": float(parts[6]),
                "service_time": float(parts[7]),
            }
            if node["type"] == "d":
                depot_raw = node
            elif node["type"] in ("f", "s"):
                stations_raw.append(node)
            elif node["type"] == "c":
                customers_raw.append(node)

    if depot_raw is None:
        raise ValueError("La instancia no contiene un nodo depósito ('d').")

    # Recortar clientes si se solicitó un subconjunto (ej. n=5, 10, 25)
    if max_customers is not None:
        customers_raw = customers_raw[:max_customers]

    # Construir lista indexada de nodos:
    # 0: Depósito salida
    # 1 .. |V_C|: Clientes
    # |V_C|+1 .. |V_C|+|V_R|: Copias de estaciones de recarga
    nodes = {}
    idx = 0

    # Nodo 0: Depósito
    nodes[idx] = {**depot_raw, "id": idx}
    V_0 = [0]
    idx += 1

    # Clientes V_C
    V_C = []
    for c in customers_raw:
        nodes[idx] = {**c, "id": idx}
        V_C.append(idx)
        idx += 1

    # Estaciones replicadas V_R
    V_R = []
    for s in stations_raw:
        for copy_num in range(station_copies):
            nodes[idx] = {
                **s,
                "id": idx,
                "string_id": f"{s['string_id']}_copy{copy_num + 1}",
            }
            V_R.append(idx)
            idx += 1

    V = V_0 + V_C + V_R  # Todos los nodos

    # Extraer parámetros globales con valores por defecto estándar si faltan
    Q_bat = params.get("Q", 77.75)     # Capacidad máxima batería
    C_cap = params.get("C", 200.0)     # Capacidad de carga física
    h_rate = params.get("r", 1.0)      # Tasa consumo batería por distancia
    g_rate = params.get("g", 3.47)     # Tasa inversa recarga (tiempo por unidad batería)
    velocity = params.get("v", 1.0)    # Velocidad promedio

    # Calcular matrices euclidianas de distancia (d_ij), tiempo (t_ij) y consumo (e_ij)
    dist = {}
    time = {}
    energy = {}

    for i in V:
        for j in V:
            if i == j:
                d_ij = 0.0
            else:
                dx = nodes[i]["x"] - nodes[j]["x"]
                dy = nodes[i]["y"] - nodes[j]["y"]
                d_ij = math.hypot(dx, dy)
            dist[(i, j)] = d_ij
            time[(i, j)] = d_ij / velocity
            energy[(i, j)] = h_rate * d_ij

    return {
        "instance_name": path.stem,
        "V": V,
        "V_0": V_0,
        "V_C": V_C,
        "V_R": V_R,
        "nodes": nodes,
        "dist": dist,
        "time": time,
        "energy": energy,
        "Q_bat": Q_bat,
        "C_cap": C_cap,
        "h_rate": h_rate,
        "g_rate": g_rate,
        "velocity": velocity,
    }

def build_arcs(V_R, nodes, dist, time, Q_bat, h_rate, depot_start, depot_end, V_out, V_in) -> set:
    arcs = []
    for i in V_out:
        e_i = nodes[i]["ready_time"]
        s_i = nodes[i]["service_time"]
        for j in V_in:
            if (i == j) or (i == depot_start and j == depot_end):
                continue
            
            # Evitar saltos entre la misma estacion
            if i in V_R and j in V_R:
                base_i = nodes[i]["string_id"].split("_copy")[0]
                base_j = nodes[j]["string_id"].split("_copy")[0]
                if base_i == base_j:
                    continue

            # Evitar salir del deposito a una estacion en la misma cordenada (bateria al 100)
            if i == depot_start and j in V_R and dist[(i, j)] == 0.0:
                continue

            # Poda por bateria, imposible recorrer (i, j) con carga completa
            if h_rate * dist[(i, j)] > Q_bat:
                continue

            # Poda por time window: si no llega de i a j
            if e_i + s_i + time[(i, j)] > nodes[j]["due_date"]:
                continue
            arcs.append((i, j))

    # set para evitar lookups O(n)
    arcs = set(arcs)
    return arcs

if __name__ == "__main__":
    # Prueba rápida del parser
    data = load_evrptw_instance("data/c101_C5.txt", station_copies=2)
    print(f"Instancia cargada: {data['instance_name']}")
    print(f"Total nodos (con copias estaciones): {len(data['V'])}")
    print(f"Clientes (V_C): {data['V_C']}")
    print(f"Estaciones replicadas (V_R): {data['V_R']}")
    print(f"Batería Q_bat={data['Q_bat']} | Carga C_cap={data['C_cap']} | Tasa recarga g={data['g_rate']}")
    print(f"Distancia Depósito(0) -> Cliente(1): {data['dist'][(0, 1)]:.2f}")