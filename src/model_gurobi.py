import json
from pathlib import Path
import gurobipy as gp
from gurobipy import GRB

from parser import load_evrptw_instance


def solve_evrptw_gurobi(
    data: dict,
    num_vehicles: int | None = None,
    time_limit: float = 3600.0,
    mip_gap: float = 0.0,
    output_dir: str = "results",
    verbose: bool = True,
) -> dict:
    """
    Construye y resuelve el modelo PLEM del E-VRPTW usando GurobiPy.
    """
    V = data["V"]
    V_C = data["V_C"]
    V_R = data["V_R"]
    nodes = {k: dict(v) for k, v in data["nodes"].items()}
    dist = dict(data["dist"])
    time = dict(data["time"])

    Q_bat = data["Q_bat"]
    C_cap = data["C_cap"]
    h_rate = data["h_rate"]
    g_rate = data["g_rate"]

    # Desdoblar depósito: 0 (salida) y depot_end = len(V) (retorno)
    depot_start = 0
    depot_end = len(V)
    nodes[depot_end] = {**nodes[depot_start], "id": depot_end, "string_id": "D0_end"}

    for i in V:
        dist[(i, depot_end)] = dist[(i, depot_start)]
        dist[(depot_end, i)] = dist[(depot_start, i)]
        time[(i, depot_end)] = time[(i, depot_start)]
        time[(depot_end, i)] = time[(depot_start, i)]
    dist[(depot_end, depot_end)] = 0.0
    time[(depot_end, depot_end)] = 0.0

    V_all = V + [depot_end]
    V_mid = V_C + V_R
    V_out = [depot_start] + V_mid
    V_in = V_mid + [depot_end]

    m = num_vehicles if num_vehicles is not None else len(V_C)
    K = list(range(m))

    # Construir arcos válidos (evita bucles i==j, viaje vacío 0->end y saltos entre copias de la misma estación)
    arcs = []
    for i in V_out:
        for j in V_in:
            if i == j:
                continue
            if i == depot_start and j == depot_end:
                continue
            if i in V_R and j in V_R:
                base_i = nodes[i]["string_id"].split("_copy")[0]
                base_j = nodes[j]["string_id"].split("_copy")[0]
                if base_i == base_j:
                    continue
            arcs.append((i, j))

    # Precalcular cotas Big-M ajustadas
    M1 = {}
    M2 = {}
    for i, j in arcs:
        e_j = nodes[j]["ready_time"]
        if i in [depot_start] + V_C:
            l_i = nodes[i]["due_date"]
            s_i = nodes[i]["service_time"]
            M1[(i, j)] = max(0.0, l_i + s_i + time[(i, j)] - e_j)
        elif i in V_R:
            l_r = nodes[i]["due_date"]
            M2[(i, j)] = max(0.0, l_r + g_rate * Q_bat + time[(i, j)] - e_j)

    # Inicializar modelo Gurobi
    model = gp.Model(f"EVRPTW_Gurobi_{data['instance_name']}_n{len(V_C)}")
    model.Params.TimeLimit = time_limit
    model.Params.MIPGap = mip_gap
    model.Params.OutputFlag = 1 if verbose else 0

    # Variables de decisión
    x = model.addVars(arcs, K, vtype=GRB.BINARY, name="x")

    T = {}
    Y = {}
    for i in V_all:
        for k in K:
            if i == depot_start:
                T[i, k] = model.addVar(lb=0.0, ub=0.0, vtype=GRB.CONTINUOUS, name=f"T_{i}_{k}")
                Y[i, k] = model.addVar(lb=Q_bat, ub=Q_bat, vtype=GRB.CONTINUOUS, name=f"Y_{i}_{k}")
            else:
                T[i, k] = model.addVar(
                    lb=nodes[i]["ready_time"],
                    ub=nodes[i]["due_date"],
                    vtype=GRB.CONTINUOUS,
                    name=f"T_{i}_{k}",
                )
                Y[i, k] = model.addVar(lb=0.0, ub=Q_bat, vtype=GRB.CONTINUOUS, name=f"Y_{i}_{k}")

    # Función objetivo: Minimizar distancia total recorrida
    model.setObjective(
        gp.quicksum(dist[(i, j)] * x[i, j, k] for (i, j) in arcs for k in K),
        GRB.MINIMIZE,
    )

    # 1. Visita única a cada cliente
    for i in V_C:
        model.addConstr(
            gp.quicksum(x[i, j, k] for k in K for j in V_in if (i, j) in x.keys() or (i, j) in arcs) == 1,
            name=f"visit_cust_{i}",
        )

    # 2. Uso máximo de una vez por copia de estación de recarga
    for r in V_R:
        model.addConstr(
            gp.quicksum(x[r, j, k] for k in K for j in V_in if (r, j) in arcs) <= 1,
            name=f"visit_station_{r}",
        )

    # 3. Salida y retorno al depósito
    for k in K:
        out_depot = gp.quicksum(x[depot_start, j, k] for j in V_mid if (depot_start, j) in arcs)
        in_depot = gp.quicksum(x[i, depot_end, k] for i in V_mid if (i, depot_end) in arcs)
        model.addConstr(out_depot <= 1, name=f"depot_out_{k}")
        model.addConstr(out_depot == in_depot, name=f"depot_balance_{k}")

    # 4. Conservación de flujo en clientes y estaciones
    for j in V_mid:
        for k in K:
            in_flow = gp.quicksum(x[i, j, k] for i in V_out if (i, j) in arcs)
            out_flow = gp.quicksum(x[j, l, k] for l in V_in if (j, l) in arcs)
            model.addConstr(in_flow - out_flow == 0, name=f"flow_{j}_{k}")

    # 5. Capacidad de carga física del vehículo
    for k in K:
        model.addConstr(
            gp.quicksum(
                nodes[i]["demand"] * x[i, j, k]
                for i in V_C
                for j in V_in
                if (i, j) in arcs
            )
            <= C_cap,
            name=f"capacity_{k}",
        )

    # 6 & 7. Causalidad temporal (clientes/depósito vs estaciones de recarga)
    for (i, j) in arcs:
        for k in K:
            if i in [depot_start] + V_C:
                s_i = nodes[i]["service_time"]
                model.addConstr(
                    T[j, k] >= T[i, k] + s_i + time[(i, j)] - M1[(i, j)] * (1 - x[i, j, k]),
                    name=f"time_cust_{i}_{j}_{k}",
                )
            elif i in V_R:
                model.addConstr(
                    T[j, k] >= T[i, k] + g_rate * (Q_bat - Y[i, k]) + time[(i, j)] - M2[(i, j)] * (1 - x[i, j, k]),
                    name=f"time_stat_{i}_{j}_{k}",
                )

    # 9 & 10. Consumo de batería por arco
    for (i, j) in arcs:
        for k in K:
            if i in [depot_start] + V_R:
                model.addConstr(
                    Y[j, k] <= Q_bat - h_rate * dist[(i, j)] * x[i, j, k],
                    name=f"bat_full_{i}_{j}_{k}",
                )
            elif i in V_C:
                model.addConstr(
                    Y[j, k] <= Y[i, k] - h_rate * dist[(i, j)] * x[i, j, k] + Q_bat * (1 - x[i, j, k]),
                    name=f"bat_cust_{i}_{j}_{k}",
                )

    # 12. Ruptura de simetría de flota
    for k in range(m - 1):
        use_next = gp.quicksum(x[depot_start, j, k + 1] for j in V_mid if (depot_start, j) in arcs)
        use_curr = gp.quicksum(x[depot_start, j, k] for j in V_mid if (depot_start, j) in arcs)
        model.addConstr(use_next <= use_curr, name=f"symmetry_{k}")

    # Optimizar
    model.optimize()

    # Mapear estado y extraer rutas
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }
    status_str = status_map.get(model.Status, f"STATUS_{model.Status}")

    routes = []
    if model.SolCount > 0:
        for k in K:
            # Verificar si el vehículo k salió del depósito
            first_next = None
            for j in V_mid:
                if (depot_start, j) in arcs and x[depot_start, j, k].X > 0.5:
                    first_next = j
                    break
            if first_next is None:
                continue

            seq = [
                {
                    "node_id": depot_start,
                    "string_id": nodes[depot_start]["string_id"],
                    "type": "d",
                    "arrival_time": round(T[depot_start, k].X, 4),
                    "battery_soc": round(Y[depot_start, k].X, 4),
                }
            ]
            curr = depot_start
            route_dist = 0.0
            recharges = 0
            visited_guard = set()

            while curr != depot_end and curr not in visited_guard:
                visited_guard.add(curr)
                nxt = None
                for j in V_in:
                    if (curr, j) in arcs and x[curr, j, k].X > 0.5:
                        nxt = j
                        break
                if nxt is None:
                    break
                route_dist += dist[(curr, nxt)]
                if nxt in V_R:
                    recharges += 1
                seq.append(
                    {
                        "node_id": nxt,
                        "string_id": nodes[nxt]["string_id"],
                        "type": nodes[nxt]["type"],
                        "arrival_time": round(T[nxt, k].X, 4),
                        "battery_soc": round(Y[nxt, k].X, 4),
                    }
                )
                curr = nxt

            routes.append(
                {
                    "vehicle": k,
                    "route_distance": round(route_dist, 4),
                    "recharges_count": recharges,
                    "sequence": seq,
                }
            )

    result = {
        "solver": "Gurobi",
        "instance": data["instance_name"],
        "n_customers": len(V_C),
        "num_vehicles_available": m,
        "vehicles_used": len(routes),
        "status": status_str,
        "best_objective": round(float(model.ObjVal), 4) if model.SolCount > 0 else None,
        "best_bound": round(float(model.ObjBound), 4) if model.SolCount > 0 else None,
        "mip_gap_pct": round(float(model.MIPGap) * 100.0, 4) if model.SolCount > 0 else None,
        "cpu_time_sec": round(float(model.Runtime), 4),
        "nodes_explored": int(model.NodeCount),
        "routes": routes,
    }

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"gurobi_{data['instance_name']}_n{len(V_C)}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


if __name__ == "__main__":
    inst = load_evrptw_instance("data/c101_C5.txt", station_copies=2)
    res = solve_evrptw_gurobi(inst, num_vehicles=3, time_limit=60.0, verbose=True)
    print("\n--- RESUMEN GUROBI ---")
    print(f"Estado: {res['status']} | Objetivo: {res['best_objective']} | Gap: {res['mip_gap_pct']}% | Tiempo: {res['cpu_time_sec']}s")
    for r in res["routes"]:
        path_str = " -> ".join(f"{n['string_id']}(SoC:{n['battery_soc']})" for n in r["sequence"])
        print(f"  Vehículo {r['vehicle']} [dist={r['route_distance']}]: {path_str}")