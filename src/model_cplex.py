import json
from pathlib import Path
from docplex.mp.model import Model

from parser import load_evrptw_instance


def solve_evrptw_cplex(
    data: dict,
    num_vehicles: int | None = None,
    time_limit: float = 3600.0,
    mip_gap: float = 0.0,
    output_dir: str = "results",
    verbose: bool = True,
) -> dict:
    """
    Construye y resuelve el modelo PLEM del E-VRPTW usando IBM DOcplex (CPLEX).
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

    # Inicializar modelo CPLEX
    mdl = Model(name=f"EVRPTW_CPLEX_{data['instance_name']}_n{len(V_C)}")
    mdl.set_time_limit(time_limit)
    mdl.parameters.mip.tolerances.mipgap = mip_gap

    # Variables de decisión
    x_keys = [(i, j, k) for (i, j) in arcs for k in K]
    x = mdl.binary_var_dict(x_keys, name="x")

    T = {}
    Y = {}
    for i in V_all:
        for k in K:
            if i == depot_start:
                T[i, k] = mdl.continuous_var(lb=0.0, ub=0.0, name=f"T_{i}_{k}")
                Y[i, k] = mdl.continuous_var(lb=Q_bat, ub=Q_bat, name=f"Y_{i}_{k}")
            else:
                T[i, k] = mdl.continuous_var(
                    lb=nodes[i]["ready_time"],
                    ub=nodes[i]["due_date"],
                    name=f"T_{i}_{k}",
                )
                Y[i, k] = mdl.continuous_var(lb=0.0, ub=Q_bat, name=f"Y_{i}_{k}")

    # Función objetivo
    mdl.minimize(mdl.sum(dist[(i, j)] * x[i, j, k] for (i, j) in arcs for k in K))

    # 1. Visita única a cada cliente
    for i in V_C:
        mdl.add_constraint(
            mdl.sum(x[i, j, k] for k in K for j in V_in if (i, j) in arcs) == 1,
            ctname=f"visit_cust_{i}",
        )

    # 2. Uso máximo de una vez por copia de estación de recarga
    for r in V_R:
        mdl.add_constraint(
            mdl.sum(x[r, j, k] for k in K for j in V_in if (r, j) in arcs) <= 1,
            ctname=f"visit_station_{r}",
        )

    # 3. Salida y retorno al depósito
    for k in K:
        out_depot = mdl.sum(x[depot_start, j, k] for j in V_mid if (depot_start, j) in arcs)
        in_depot = mdl.sum(x[i, depot_end, k] for i in V_mid if (i, depot_end) in arcs)
        mdl.add_constraint(out_depot <= 1, ctname=f"depot_out_{k}")
        mdl.add_constraint(out_depot == in_depot, ctname=f"depot_balance_{k}")

    # 4. Conservación de flujo
    for j in V_mid:
        for k in K:
            in_flow = mdl.sum(x[i, j, k] for i in V_out if (i, j) in arcs)
            out_flow = mdl.sum(x[j, l, k] for l in V_in if (j, l) in arcs)
            mdl.add_constraint(in_flow - out_flow == 0, ctname=f"flow_{j}_{k}")

    # 5. Capacidad de carga física
    for k in K:
        mdl.add_constraint(
            mdl.sum(
                nodes[i]["demand"] * x[i, j, k]
                for i in V_C
                for j in V_in
                if (i, j) in arcs
            )
            <= C_cap,
            ctname=f"capacity_{k}",
        )

    # 6 & 7. Causalidad temporal
    for (i, j) in arcs:
        for k in K:
            if i in [depot_start] + V_C:
                s_i = nodes[i]["service_time"]
                mdl.add_constraint(
                    T[j, k] >= T[i, k] + s_i + time[(i, j)] - M1[(i, j)] * (1 - x[i, j, k]),
                    ctname=f"time_cust_{i}_{j}_{k}",
                )
            elif i in V_R:
                mdl.add_constraint(
                    T[j, k] >= T[i, k] + g_rate * (Q_bat - Y[i, k]) + time[(i, j)] - M2[(i, j)] * (1 - x[i, j, k]),
                    ctname=f"time_stat_{i}_{j}_{k}",
                )

    # 9 & 10. Consumo de batería por arco
    for (i, j) in arcs:
        for k in K:
            if i in [depot_start] + V_R:
                mdl.add_constraint(
                    Y[j, k] <= Q_bat - h_rate * dist[(i, j)] * x[i, j, k],
                    ctname=f"bat_full_{i}_{j}_{k}",
                )
            elif i in V_C:
                mdl.add_constraint(
                    Y[j, k] <= Y[i, k] - h_rate * dist[(i, j)] * x[i, j, k] + Q_bat * (1 - x[i, j, k]),
                    ctname=f"bat_cust_{i}_{j}_{k}",
                )

    # 12. Ruptura de simetría de flota
    for k in range(m - 1):
        use_next = mdl.sum(x[depot_start, j, k + 1] for j in V_mid if (depot_start, j) in arcs)
        use_curr = mdl.sum(x[depot_start, j, k] for j in V_mid if (depot_start, j) in arcs)
        mdl.add_constraint(use_next <= use_curr, ctname=f"symmetry_{k}")

    # Optimizar
    sol = mdl.solve(log_output=verbose)
    details = mdl.solve_details

    raw_status = str(details.status).upper()
    if "OPTIMAL" in raw_status:
        status_str = "OPTIMAL"
    elif "TIME" in raw_status:
        status_str = "TIME_LIMIT"
    elif "INFEASIBLE" in raw_status:
        status_str = "INFEASIBLE"
    else:
        status_str = raw_status

    routes = []
    if sol is not None:
        for k in K:
            first_next = None
            for j in V_mid:
                if (depot_start, j) in arcs and sol.get_value(x[depot_start, j, k]) > 0.5:
                    first_next = j
                    break
            if first_next is None:
                continue

            seq = [
                {
                    "node_id": depot_start,
                    "string_id": nodes[depot_start]["string_id"],
                    "type": "d",
                    "arrival_time": round(float(sol.get_value(T[depot_start, k])), 4),
                    "battery_soc": round(float(sol.get_value(Y[depot_start, k])), 4),
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
                    if (curr, j) in arcs and sol.get_value(x[curr, j, k]) > 0.5:
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
                        "arrival_time": round(float(sol.get_value(T[nxt, k])), 4),
                        "battery_soc": round(float(sol.get_value(Y[nxt, k])), 4),
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
        "solver": "CPLEX",
        "instance": data["instance_name"],
        "n_customers": len(V_C),
        "num_vehicles_available": m,
        "vehicles_used": len(routes),
        "status": status_str,
        "best_objective": round(float(sol.get_objective_value()), 4) if sol is not None else None,
        "best_bound": round(float(details.best_bound), 4) if sol is not None else None,
        "mip_gap_pct": round(float(details.mip_relative_gap) * 100.0, 4) if sol is not None else None,
        "cpu_time_sec": round(float(details.time), 4),
        "nodes_explored": int(details.nb_nodes_processed),
        "routes": routes,
    }

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"cplex_{data['instance_name']}_n{len(V_C)}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


if __name__ == "__main__":
    inst = load_evrptw_instance("data/c101_C5.txt", station_copies=2)
    res = solve_evrptw_cplex(inst, num_vehicles=3, time_limit=60.0, verbose=True)
    print("\n--- RESUMEN CPLEX ---")
    print(f"Estado: {res['status']} | Objetivo: {res['best_objective']} | Gap: {res['mip_gap_pct']}% | Tiempo: {res['cpu_time_sec']}s")
    for r in res["routes"]:
        path_str = " -> ".join(f"{n['string_id']}(SoC:{n['battery_soc']})" for n in r["sequence"])
        print(f"  Vehículo {r['vehicle']} [dist={r['route_distance']}]: {path_str}")