"""
Aca tomamos la secuencia de nodos que entrega el modelo
y simulamos el v iaje real hacia delante paso a paso para:

1. Verificamos que no haya ninguna infraccion
2. Revisamosl los tiempos reales y el SoC real de cada parada, sirve para los graficos
"""

import json
from pathlib import Path

from parser import load_evrptw_instance


def validate_solution(data: dict, result: dict, tol: float = 1e-4) -> dict:
    """
    Simula y valida operativamente una solución de Gurobi o CPLEX.
    Recalcula tiempos reales (llegada, espera, servicio, recarga) y SoC real.
    """
    errors = []
    routes = result.get("routes", [])
    if not routes:
        return {
            "is_valid": False,
            "errors": ["La solución no contiene rutas para validar."],
            "recalculated_distance": 0.0,
            "simulated_routes": [],
        }

    V_C_set = set(data["V_C"])
    nodes = data["nodes"]
    dist = data["dist"]
    time = data["time"]
    Q_bat = data["Q_bat"]
    C_cap = data["C_cap"]
    h_rate = data["h_rate"]
    g_rate = data["g_rate"]
    depot_end = len(data["V"])

    visited_customers = []
    total_dist = 0.0
    simulated_routes = []

    # Recorremos cada arco prev->curr de cada ruta con las restricciones reales
    # Bateria verifica que no caiga bajo cero, si llega a estacion recarga al 100
    # Tiempo suma e lviaje y verifica que llega en ventana (o ante y espera)
    # Capacidad acumula la demanda de los clientes y verifica que no supere el limite

    for route in routes:
        veh = route["vehicle"]
        seq = route["sequence"]

        if seq[0]["node_id"] != 0 or seq[-1]["node_id"] != depot_end:
            errors.append(f"Vehículo {veh}: la ruta no inicia en D0 o no termina en D0_end.")

        t_curr = 0.0
        soc_curr = Q_bat
        load = 0.0
        route_dist = 0.0
        recharges = 0

        sim_seq = [
            {
                "node_id": 0,
                "string_id": nodes[0]["string_id"],
                "type": "d",
                "arrival_time": 0.0,
                "wait_time": 0.0,
                "start_time": 0.0,
                "recharge_time": 0.0,
                "depart_time": 0.0,
                "soc_arrival": round(Q_bat, 4),
                "soc_depart": round(Q_bat, 4),
            }
        ]

        for step in range(1, len(seq)):
            prev_id = seq[step - 1]["node_id"]
            curr_id = seq[step]["node_id"]

            # Mapear depot_end al nodo 0 para consultar matrices de parser.py
            prev_key = 0 if prev_id == depot_end else prev_id
            curr_key = 0 if curr_id == depot_end else curr_id
            node = nodes[curr_key]

            # 1. Viaje y consumo de energía
            d_ij = dist[(prev_key, curr_key)]
            t_ij = time[(prev_key, curr_key)]
            route_dist += d_ij

            soc_arr = soc_curr - h_rate * d_ij
            if soc_arr < -tol:
                errors.append(
                    f"Vehículo {veh} en {seq[step]['string_id']}: batería negativa ({soc_arr:.4f})."
                )

            # 2. Llegada, espera y ventana horaria
            t_arr = t_curr + t_ij
            wait = max(0.0, node["ready_time"] - t_arr)
            t_start = t_arr + wait
            if t_start > node["due_date"] + tol:
                errors.append(
                    f"Vehículo {veh} en {seq[step]['string_id']}: viola ventana "
                    f"(inicio={t_start:.2f} > due={node['due_date']:.2f})."
                )

            # 3. Atención según tipo de nodo
            recharge_time = 0.0
            if curr_id == depot_end:
                t_dep = t_arr
                soc_dep = soc_arr
            elif node["type"] == "c":
                visited_customers.append(curr_id)
                load += node["demand"]
                t_dep = t_start + node["service_time"]
                soc_dep = soc_arr
            elif node["type"] in ("f", "s"):
                recharges += 1
                recharge_time = g_rate * (Q_bat - max(0.0, soc_arr))
                t_dep = t_start + recharge_time
                soc_dep = Q_bat
            else:
                t_dep = t_start
                soc_dep = soc_arr

            sim_seq.append(
                {
                    "node_id": curr_id,
                    "string_id": seq[step]["string_id"],
                    "type": node["type"],
                    "arrival_time": round(t_arr, 4),
                    "wait_time": round(wait, 4),
                    "start_time": round(t_start, 4),
                    "recharge_time": round(recharge_time, 4),
                    "depart_time": round(t_dep, 4),
                    "soc_arrival": round(soc_arr, 4),
                    "soc_depart": round(soc_dep, 4),
                }
            )
            t_curr = t_dep
            soc_curr = soc_dep

        if load > C_cap + tol:
            errors.append(f"Vehículo {veh}: excede capacidad ({load:.2f} > {C_cap:.2f}).")

        total_dist += route_dist
        simulated_routes.append(
            {
                "vehicle": veh,
                "route_distance": round(route_dist, 4),
                "load_used": round(load, 4),
                "recharges_count": recharges,
                "sequence": sim_seq,
            }
        )

    # Chequeo global de clientes (exactamente 1 visita por cliente)
    visited_set = set(visited_customers)
    if len(visited_customers) != len(visited_set):
        errors.append("Hay clientes visitados más de una vez.")
    missing = V_C_set - visited_set
    if missing:
        errors.append(f"Faltan clientes por visitar: {sorted(missing)}.")

    # Chequeo de distancia total vs objetivo del solver
    reported_obj = result.get("best_objective")
    if reported_obj is not None and abs(total_dist - reported_obj) > 1e-2:
        errors.append(
            f"Distancia recalculada ({total_dist:.4f}) difiere del objetivo ({reported_obj:.4f})."
        )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "recalculated_distance": round(total_dist, 4),
        "simulated_routes": simulated_routes,
    }


if __name__ == "__main__":
    # Pruebas rapidas
    from model_gurobi import solve_evrptw_gurobi

    for fname in ["data/c101C5.txt", "data/r104C5.txt"]:
        inst = load_evrptw_instance(fname, station_copies=2)
        res = solve_evrptw_gurobi(inst, num_vehicles=3, time_limit=60.0, output_dir="/tmp/val_toy", verbose=False)
        val = validate_solution(inst, res)
        print(f"\n=== VALIDACION {inst['instance_name']} ===")
        print(f"Válida: {val['is_valid']} | Dist real: {val['recalculated_distance']} | Errores: {val['errors']}")
        for r in val["simulated_routes"]:
            print(f"  Vehiculo {r['vehicle']} (carga={r['load_used']}/{inst['C_cap']}, dist={r['route_distance']}, recargas={r['recharges_count']}):")
            for s in r["sequence"]:
                extra = f" | recarga={s['recharge_time']}m" if s["recharge_time"] > 0 else ""
                print(
                    f"    {s['string_id']:10s} | lleg={s['arrival_time']:6.2f} | esp={s['wait_time']:5.2f} "
                    f"| sal={s['depart_time']:6.2f} | SoC: {s['soc_arrival']:5.2f} -> {s['soc_depart']:5.2f}{extra}"
                )
    