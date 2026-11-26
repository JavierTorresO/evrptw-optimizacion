from __future__ import annotations

import argparse
import csv
from pathlib import Path

from parser import load_evrptw_instance
from model_gurobi import solve_evrptw_gurobi
from model_cplex import solve_evrptw_cplex
from validator import validate_solution
from instances_battery import BENCHMARK_INSTANCES

CSV_COLUMNS = [
    "instance",
    "family",
    "scale",
    "n_customers",
    "n_station_copies",
    "num_vehicles_available",
    "solver",
    "status",
    "best_objective",
    "best_bound",
    "mip_gap_pct",
    "cpu_time_sec",
    "nodes_explored",
    "vehicles_used",
    "total_recharges",
    "is_valid",
]


def load_completed_runs(csv_path: Path) -> set[tuple[str, str, str]]:
    """Lee el CSV existente para no repetir corridas ya terminadas si se usa --resume."""
    done = set()
    if not csv_path.exists():
        return done
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            done.add((row["instance"], row["scale"], row["solver"]))
    return done


def append_row(csv_path: Path, row: dict) -> None:
    """Agrega una fila al CSV inmediatamente (creando el encabezado si no existe)."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def run_benchmark(
    scales: list[str] | None,
    solvers: list[str],
    time_limit: float,
    threads: int,
    resume: bool,
    output_dir: str = "results",
) -> None:
    out_root = Path(output_dir)
    json_dir = out_root / "benchmark_json"
    csv_path = out_root / "comparacion_solvers.csv"

    done = load_completed_runs(csv_path) if resume else set()
    if not resume and csv_path.exists():
        csv_path.unlink()

    solver_map = {
        "Gurobi": solve_evrptw_gurobi,
        "CPLEX": solve_evrptw_cplex,
    }

    selected = [
        cfg for cfg in BENCHMARK_INSTANCES
        if scales is None or cfg["scale"] in scales
    ]

    print(f"Instancias a evaluar: {len(selected)} | Solvers: {solvers} | TimeLimit: {time_limit}s | Threads: {threads}")
    print("-" * 95)

    for cfg in selected:
        data = load_evrptw_instance(
            cfg["file"],
            station_copies=cfg["station_copies"],
            max_customers=cfg["max_customers"],
        )
        inst_name = data["instance_name"]

        for solver_name in solvers:
            key = (inst_name, cfg["scale"], solver_name)
            if key in done:
                print(f"[SKIP] {inst_name:10s} ({cfg['scale']}) | {solver_name} ya existe en CSV")
                continue

            print(f"[RUN ] {inst_name:10s} ({cfg['scale']}, fam={cfg['family']}) | {solver_name} ...", flush=True)
            solve_fn = solver_map[solver_name]

            try:
                res = solve_fn(
                    data,
                    num_vehicles=cfg["num_vehicles"],
                    time_limit=time_limit,
                    mip_gap=0.0,
                    threads=threads,
                    output_dir=str(json_dir),
                    verbose=False,
                )
                if res["routes"]:
                    val = validate_solution(data, res)
                    is_valid = val["is_valid"]
                    total_recharges = sum(r["recharges_count"] for r in val["simulated_routes"])
                else:
                    is_valid = False
                    total_recharges = 0

                row = {
                    "instance": inst_name,
                    "family": cfg["family"],
                    "scale": cfg["scale"],
                    "n_customers": res["n_customers"],
                    "n_station_copies": len(data["V_R"]),
                    "num_vehicles_available": res["num_vehicles_available"],
                    "solver": solver_name,
                    "status": res["status"],
                    "best_objective": res["best_objective"],
                    "best_bound": res["best_bound"],
                    "mip_gap_pct": res["mip_gap_pct"],
                    "cpu_time_sec": res["cpu_time_sec"],
                    "nodes_explored": res["nodes_explored"],
                    "vehicles_used": res["vehicles_used"],
                    "total_recharges": total_recharges,
                    "is_valid": is_valid,
                }
            except Exception as e:
                row = {
                    "instance": inst_name,
                    "family": cfg["family"],
                    "scale": cfg["scale"],
                    "n_customers": len(data["V_C"]),
                    "n_station_copies": len(data["V_R"]),
                    "num_vehicles_available": cfg["num_vehicles"],
                    "solver": solver_name,
                    "status": f"ERROR: {type(e).__name__}",
                    "best_objective": None,
                    "best_bound": None,
                    "mip_gap_pct": None,
                    "cpu_time_sec": None,
                    "nodes_explored": None,
                    "vehicles_used": None,
                    "total_recharges": None,
                    "is_valid": False,
                }
                print(f"  -> ERROR en {inst_name} ({solver_name}): {e}", flush=True)

            append_row(csv_path, row)
            print(
                f"[DONE] {inst_name:10s} | {solver_name:6s} | {str(row['status']):10s} | "
                f"obj={str(row['best_objective']):8s} | gap={str(row['mip_gap_pct']):6s}% | "
                f"t={str(row['cpu_time_sec']):7s}s | valid={row['is_valid']}",
                flush=True,
            )

    print(f"\nBenchmark finalizado. Resultados consolidados en: {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark comparativo Gurobi vs CPLEX (E-VRPTW)")
    parser.add_argument("--scales", nargs="+", default=None, help="Escalas a correr (ej: n=10 n=15 n=25)")
    parser.add_argument("--solvers", nargs="+", default=["Gurobi", "CPLEX"], choices=["Gurobi", "CPLEX"])
    parser.add_argument("--time-limit", type=float, default=3600.0, help="Límite en segundos por corrida")
    parser.add_argument("--threads", type=int, default=8, help="Hilos por solver")
    parser.add_argument("--resume", action="store_true", help="Saltar corridas ya guardadas en el CSV")
    args = parser.parse_args()

    run_benchmark(
        scales=args.scales,
        solvers=args.solvers,
        time_limit=args.time_limit,
        threads=args.threads,
        resume=args.resume,
    )