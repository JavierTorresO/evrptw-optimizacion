from __future__ import annotations

import json
from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
from matplotlib.lines import Line2D

import csv
from matplotlib.ticker import LogLocator, NullFormatter

from parser import load_evrptw_instance
from validator import validate_solution

ROOT = Path(__file__).resolve().parents[1]

# Caso ilustrativo: familia mixta, 15 clientes, 2 rutas y 6 recargas;
# ambos solvers certificaron el óptimo en el benchmark.
INSTANCE_FILE = ROOT / "data" / "rc202C15.txt"

RESULT_FILE = (
    ROOT / "results" / "benchmark_json" / "gurobi_rc202C15_n15.json"
)
OUTPUT_FILE = (
    ROOT / "results" / "figuras" / "mapa_rutas_rc202C15_gurobi.png"
)
SOC_OUTPUT_FILE = (
    ROOT / "results" / "figuras" / "perfil_soc_rc202C15_gurobi.png"
)

CSV_FILE = ROOT / "results" / "comparacion_solvers.csv"

TIEMPOS_OUTPUT_FILE = (
    ROOT / "results" / "figuras" / "comparacion_tiempos_solvers.png"
)

MIPGAP_OUTPUT_FILE = (
    ROOT / "results" / "figuras" / "comparacion_mipgap_solvers.png"
)

OBJETIVOS_OUTPUT_FILE = (
    ROOT / "results" / "figuras" / "comparacion_incumbent_cota.png"
)

OPTIMOS_OUTPUT_FILE = (
    ROOT / "results" / "figuras" / "resumen_optimos_por_tamano.png"
)

def obtener_coordenadas(data: dict, node_id: int) -> tuple[float, float]:
    """Obtiene las coordenadas de un nodo; el depósito final está duplicado."""
    depot_end = len(data["V"])

    if node_id == depot_end:
        node_id = 0

    node = data["nodes"][node_id]
    return float(node["x"]), float(node["y"])


def separar_etiquetas_nodos(etiquetas: list, puntos: list, ax) -> None:
    """Reubica etiquetas cercanas sin modificar las coordenadas de los nodos."""
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    limites = ax.get_window_extent(renderer)
    puntos_px = [ax.transData.transform(punto) for punto in puntos]
    direcciones = [
        (1, 0), (0, 1), (-1, 0), (0, -1),
        (1, 1), (-1, 1), (-1, -1), (1, -1),
    ]
    cajas_ocupadas = []
    margen = renderer.points_to_pixels(4)

    orden = sorted(
        range(len(etiquetas)),
        key=lambda i: min(
            (
                (puntos_px[i][0] - x) ** 2 + (puntos_px[i][1] - y) ** 2
                for j, (x, y) in enumerate(puntos_px)
                if i != j
            ),
            default=float("inf"),
        ),
    )

    for i in orden:
        etiqueta = etiquetas[i]
        posicion_inicial = etiqueta.get_position()
        candidatos = [posicion_inicial]
        for radio in range(10, 61, 5):
            candidatos.extend(
                (
                    posicion_inicial[0] + dx * radio,
                    posicion_inicial[1] + dy * radio,
                )
                for dx, dy in direcciones
            )

        cajas_otros_nodos = [
            Bbox.from_extents(
                x - margen, y - margen, x + margen, y + margen
            )
            for j, (x, y) in enumerate(puntos_px)
            if j != i
        ]

        for posicion in candidatos:
            etiqueta.set_position(posicion)
            caja = etiqueta.get_window_extent(renderer).expanded(1.05, 1.1)
            dentro_del_grafico = (
                limites.x0 <= caja.x0
                and caja.x1 <= limites.x1
                and limites.y0 <= caja.y0
                and caja.y1 <= limites.y1
            )
            tapa_nodo = any(
                caja.overlaps(caja_nodo_otro)
                for caja_nodo_otro in cajas_otros_nodos
            )
            tapa_etiqueta = any(
                caja.overlaps(caja_anterior)
                for caja_anterior in cajas_ocupadas
            )

            if dentro_del_grafico and not tapa_nodo and not tapa_etiqueta:
                cajas_ocupadas.append(caja)
                break
        else:
            etiqueta.set_position(posicion_inicial)
            cajas_ocupadas.append(
                etiqueta.get_window_extent(renderer).expanded(1.05, 1.1)
            )


def graficar_mapa_rutas(data: dict, result: dict, output_file: Path) -> None:
    # Nombres de las estaciones que aparecen en alguna ruta
    estaciones_usadas = set()

    for route in result["routes"]:
        for stop in route["sequence"]:
            if stop["type"] in {"f", "s"}:
                nombre_base = stop["string_id"].split("_copy")[0]
                estaciones_usadas.add(nombre_base)

    fig, ax = plt.subplots(figsize=(14, 10))
    colores = plt.get_cmap("tab10")
    n_rutas = len(result["routes"])

    # Dibuja las rutas con flechas curvas (una curvatura distinta por ruta)
    for index, route in enumerate(result["routes"]):
        color = colores(index % 10)
        sequence = route["sequence"]

        puntos = [
            obtener_coordenadas(data, stop["node_id"])
            for stop in sequence
        ]

        rad = 0.08 * (index - (n_rutas - 1) / 2)

        for inicio, fin in zip(puntos, puntos[1:]):
            if inicio != fin:
                ax.annotate(
                    "",
                    xy=fin,
                    xytext=inicio,
                    arrowprops={
                        "arrowstyle": "-|>",
                        "mutation_scale": 9,
                        "color": color,
                        "linewidth": 1.6,
                        "alpha": 0.85,
                        "shrinkA": 5,
                        "shrinkB": 5,
                        "connectionstyle": f"arc3,rad={rad}",
                    },
                    zorder=3,
                )

    nodes = data["nodes"]

    # Dibuja los clientes
    etiquetas_nodos = []
    puntos_nodos = []

    for node_id in data["V_C"]:
        node = nodes[node_id]
        punto = (node["x"], node["y"])
        puntos_nodos.append(punto)
        ax.scatter(
            node["x"],
            node["y"],
            marker="o",
            s=65,
            color="#954CE8",
            edgecolors="black",
            linewidths=0.7,
            zorder=5,
        )
        desplazamiento = (6, 6)

        if node["string_id"] == "C96":
            desplazamiento = (12, 14)
        elif node["string_id"] == "C95":
            desplazamiento = (12, -14)

        etiqueta = ax.annotate(
            node["string_id"],
            punto,
            xytext=desplazamiento,
            textcoords="offset points",
            fontsize=7,
            zorder=6,
            ha="left",
            va="center",
            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
                "pad": 1,
            },
        )
        etiquetas_nodos.append(etiqueta)

    # Agrupa las copias de una misma estación para dibujarla una sola vez
    estaciones = {}

    for node_id in data["V_R"]:
        node = nodes[node_id]
        nombre_base = node["string_id"].split("_copy")[0]
        estaciones[nombre_base] = node

    deposito = nodes[0]

    # Dibuja las estaciones. Las usadas en las rutas quedan resaltadas.
    for nombre, node in estaciones.items():
        usada = nombre in estaciones_usadas
        color_est = "#F28E2B" if usada else "#C7CBD1"
        tamano = 115 if usada else 75

        ax.scatter(
            node["x"],
            node["y"],
            marker="^",
            s=tamano,
            color=color_est,
            edgecolors="black",
            linewidths=0.7,
            zorder=4,
        )

        # No etiqueta la estación si comparte ubicación con el depósito
        comparte_deposito = (
            abs(node["x"] - deposito["x"]) < 1e-8
            and abs(node["y"] - deposito["y"]) < 1e-8
        )

        if not comparte_deposito:
            etiqueta = ax.annotate(
                nombre,
                (node["x"], node["y"]),
                xytext=(5, -12),
                textcoords="offset points",
                fontsize=8,
                zorder=6,
            )
            etiquetas_nodos.append(etiqueta)
            puntos_nodos.append((node["x"], node["y"]))

    # Dibuja el depósito al final para que destaque si comparte coordenadas
    ax.scatter(
        deposito["x"],
        deposito["y"],
        marker="*",
        s=260,
        color="#222222",
        edgecolors="white",
        linewidths=1,
        zorder=7,
    )
    etiqueta = ax.annotate(
        "Depósito",
        (deposito["x"], deposito["y"]),
        xytext=(8, -15),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        zorder=8,
    )
    etiquetas_nodos.append(etiqueta)
    puntos_nodos.append((deposito["x"], deposito["y"]))

    # Leyenda: tipos de nodo y vehículos
    leyenda = [
        Line2D(
            [0], [0],
            marker="*",
            color="white",
            markerfacecolor="#222222",
            markeredgecolor="white",
            markersize=14,
            label="Depósito",
        ),
        Line2D(
            [0], [0],
            marker="o",
            color="white",
            markerfacecolor="#954CE8",
            markeredgecolor="black",
            markersize=8,
            label="Cliente",
        ),
        Line2D(
            [0], [0],
            marker="^",
            color="white",
            markerfacecolor="#F28E2B",
            markeredgecolor="black",
            markersize=9,
            label="Estación usada",
        ),
    ]

    for index, route in enumerate(result["routes"]):
        color = colores(index % 10)
        numero_vehiculo = route["vehicle"] + 1
        distancia = route["route_distance"]

        leyenda.append(
            Line2D(
                [0], [0],
                color=color,
                linewidth=2,
                label=f"Vehículo {numero_vehiculo} - dist. {distancia:.1f}",
            )
        )

    ax.legend(
        handles=leyenda,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.09),
        ncol=3,
        frameon=False,
    )

    total_recargas = sum(
        route["recharges_count"] for route in result["routes"]
    )

    fig.suptitle(
        f"Rutas para {result['instance']} - {result['solver']}\n"
        f"Estado: {result['status']} | "
        f"Distancia total: {result['best_objective']:.2f} | "
        f"Recargas: {total_recargas}",
        fontsize=13,
        fontweight="bold",
    )

    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.25)

    fig.tight_layout(rect=[0, 0.08, 1, 0.91])

    separar_etiquetas_nodos(etiquetas_nodos, puntos_nodos, ax)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico guardado en: {output_file}")


def graficar_bateria_soc(data: dict, result: dict, output_file: Path) -> None:
    validacion = validate_solution(data, result)

    if not validacion["is_valid"]:
        print("La solución no pasó la validación:", validacion["errors"])
        return

    rutas = validacion["simulated_routes"]

    if not rutas:
        print("La solución no contiene rutas para graficar.")
        return

    columnas = 2
    filas = (len(rutas) + columnas - 1) // columnas

    fig, axes = plt.subplots(
        filas,
        columnas,
        figsize=(12, 5 * filas),
        squeeze=False,
    )

    colores = plt.get_cmap("tab10")
    capacidad = data["Q_bat"]

    for indice, (ax, ruta) in enumerate(zip(axes.flat, rutas)):
        secuencia = ruta["sequence"]
        xs = [0]
        ys = [100 * secuencia[0]["soc_depart"] / capacidad]

        # Agrega el SoC de llegada y, en estaciones, también el de salida
        for parada_indice, parada in enumerate(secuencia[1:], start=1):
            xs.append(parada_indice)
            ys.append(100 * parada["soc_arrival"] / capacidad)

            if parada["type"] in {"f", "s"}:
                xs.append(parada_indice)
                ys.append(100 * parada["soc_depart"] / capacidad)

        color = colores(indice % 10)

        ax.plot(
            xs,
            ys,
            color=color,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

        # Destaca la llegada y salida de cada estación de recarga
        for parada_indice, parada in enumerate(secuencia):
            if parada["type"] in {"f", "s"}:
                soc_llegada = 100 * parada["soc_arrival"] / capacidad
                soc_salida = 100 * parada["soc_depart"] / capacidad

                ax.scatter(
                    parada_indice,
                    soc_llegada,
                    marker="v",
                    s=65,
                    color="#F22BA9",
                    edgecolors="black",
                    zorder=4,
                )
                ax.scatter(
                    parada_indice,
                    soc_salida,
                    marker="^",
                    s=65,
                    color="#872CA0",
                    edgecolors="black",
                    zorder=4,
                )

        etiquetas = []
        for parada in secuencia:
            if parada["type"] == "d":
                etiquetas.append("D0")
            elif parada["type"] in {"f", "s"}:
                etiquetas.append(parada["string_id"].split("_copy")[0])
            else:
                etiquetas.append(parada["string_id"])

        ax.set_xticks(
            range(len(secuencia)),
            etiquetas,
            rotation=35,
            ha="right",
            fontsize=8,
        )
        ax.set_ylim(0, 110)
        ax.axhline(100, color="#555555", linestyle="--", linewidth=1)
        ax.set_title(
            f"Vehículo {ruta['vehicle'] + 1} "
            f"| recargas: {ruta['recharges_count']}"
        )
        ax.set_xlabel("Paradas en orden")
        ax.set_ylabel("Batería (%)")
        ax.grid(True, alpha=0.25)

    # Oculta paneles vacíos si sobran
    for ax in list(axes.flat)[len(rutas):]:
        ax.set_visible(False)

    leyenda = [
        Line2D(
            [0], [0],
            marker="v",
            color="white",
            markerfacecolor="#F22BA9",
            markeredgecolor="black",
            label="Llegada a estación",
        ),
        Line2D(
            [0], [0],
            marker="^",
            color="white",
            markerfacecolor="#872CA0",
            markeredgecolor="black",
            label="Salida después de recarga",
        ),
    ]

    fig.suptitle(
        f"Evolución del estado de carga de la batería\n"
        f"{result['instance']} - {result['solver']} | "
        f"{result['n_customers']} clientes",
        fontsize=14,
    )
    fig.legend(handles=leyenda, loc="lower center", ncol=2, frameon=False)
    fig.tight_layout(rect=[0, 0.08, 1, 0.94])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico SoC guardado en: {output_file}")

LIMITE_TIEMPO = 3600

def graficar_tiempos(csv_path: Path, output_file: Path) -> None:
    with open(csv_path, "r", encoding="utf-8", newline="") as file:
        filas = list(csv.DictReader(file))

    escalas = ["n=10", "n=15", "n=25"]
    colores_solver = {
        "Gurobi": "#2A6FDB",
        "CPLEX": "#E07026",
    }
    marcadores_estado = {
        "OPTIMAL": "o",
        "TIME_LIMIT": "^",
        "MEM_LIMIT": "s",
    }
    orden_familias = {"C": 0, "R": 1, "RC": 2}
    colores_familia = {"C": "#F2F6FC", "R": "#FDF4EC", "RC": "#F1F8F1"}

    fig, axes = plt.subplots(1, 3, figsize=(24, 9), sharey=True)

    for ax, escala in zip(axes, escalas):
        grupo = [fila for fila in filas if fila["scale"] == escala]

        familia_por_instancia = {
            fila["instance"]: fila["family"] for fila in grupo
        }
        instancias = sorted(
            familia_por_instancia,
            key=lambda nombre: (
                orden_familias.get(familia_por_instancia[nombre], 99),
                nombre,
            ),
        )
        posicion = {instancia: i for i, instancia in enumerate(instancias)}

        # Bandas de fondo y etiqueta por familia (C / R / RC)
        inicio = 0
        for fam in ["C", "R", "RC"]:
            n_fam = sum(
                1 for i in instancias if familia_por_instancia[i] == fam
            )
            if n_fam == 0:
                continue
            ax.axvspan(
                inicio - 0.5,
                inicio + n_fam - 0.5,
                color=colores_familia[fam],
                zorder=0,
            )
            ax.text(
                inicio + (n_fam - 1) / 2,
                1.01,
                fam,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )
            inicio += n_fam

        pares = []

        for instancia in instancias:
            tiempos_par = {}

            for solver, desplazamiento in [
                ("Gurobi", -0.12),
                ("CPLEX", 0.12),
            ]:
                fila = next(
                    (
                        f for f in grupo
                        if f["instance"] == instancia
                        and f["solver"] == solver
                    ),
                    None,
                )

                if fila is None or not fila["cpu_time_sec"]:
                    continue

                tiempo = float(fila["cpu_time_sec"])
                if tiempo <= 0:
                    continue

                estado = fila["status"]
                marcador = marcadores_estado.get(estado, "x")
                x = posicion[instancia] + desplazamiento

                ax.scatter(
                    x,
                    tiempo,
                    color=colores_solver[solver],
                    marker=marcador,
                    s=110,
                    edgecolors="black",
                    linewidths=2.0,
                    zorder=3,
                )
                tiempos_par[solver] = (x, tiempo)

            if "Gurobi" in tiempos_par and "CPLEX" in tiempos_par:
                pares.append(
                    (tiempos_par["Gurobi"], tiempos_par["CPLEX"])
                )

        # Conector con el color del solver más rápido
        for gurobi, cplex in pares:
            gana_gurobi = gurobi[1] <= cplex[1]
            ax.plot(
                [gurobi[0], cplex[0]],
                [gurobi[1], cplex[1]],
                color=colores_solver["Gurobi" if gana_gurobi else "CPLEX"],
                linewidth=1.8,
                alpha=0.6,
                zorder=2,
            )

        # Línea del límite de tiempo
        ax.axhline(
            LIMITE_TIEMPO,
            color="#C62828",
            linestyle="--",
            linewidth=1,
            zorder=1,
        )
        if ax is axes[0]:
            ax.text(
                0.01,
                LIMITE_TIEMPO,
                " límite",
                color="#C62828",
                fontsize=8,
                transform=ax.get_yaxis_transform(),
                va="bottom",
            )

        # Resumen en el título: cuántas veces ganó Gurobi
        gana_g = sum(1 for g, c in pares if g[1] <= c[1])
        ax.set_title(
            f"{escala} ({len(instancias)} inst.) | "
            f"Gurobi más rápido: {gana_g}/{len(pares)}",
            pad=22,
        )

        ax.set_xticks(
            range(len(instancias)),
            instancias,
            rotation=55,
            ha="right",
            fontsize=11,
        )
        ax.set_xlim(-0.5, len(instancias) - 0.5)

        # Escala log más legible
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(LogLocator(base=10))
        ax.yaxis.set_minor_locator(
            LogLocator(base=10, subs=range(2, 10))
        )
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.grid(True, which="major", axis="y", alpha=0.25)
        ax.grid(True, which="minor", axis="y", alpha=0.1)

        if ax is axes[0]:
            ax.set_ylabel("Tiempo de cómputo (segundos, escala log)")

    leyenda_solver = [
        Line2D(
            [0], [0],
            marker="o",
            color=color,
            linestyle="none",
            label=solver,
        )
        for solver, color in colores_solver.items()
    ]
    leyenda_estado = [
        Line2D(
            [0], [0],
            marker=marcador,
            color="#555555",
            linestyle="none",
            label=estado,
        )
        for estado, marcador in marcadores_estado.items()
    ]

    fig.suptitle("Comparación de tiempos: Gurobi y CPLEX", fontsize=14)
    fig.legend(
        handles=leyenda_solver + leyenda_estado,
        loc="lower center",
        ncol=5,
        frameon=False,
    )
    fig.tight_layout(rect=[0, 0.13, 1, 0.93])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico de tiempos guardado en: {output_file}")


def graficar_mipgap(csv_path: Path, output_file: Path) -> None:
    with open(csv_path, "r", encoding="utf-8", newline="") as file:
        filas = list(csv.DictReader(file))

    escalas = ["n=10", "n=15", "n=25"]
    colores_solver = {
        "Gurobi": "#2A6FDB",
        "CPLEX": "#E07026",
    }
    marcadores_estado = {
        "OPTIMAL": "o",
        "TIME_LIMIT": "^",
        "MEM_LIMIT": "s",
    }
    colores_estado = {
        "OPTIMAL": "#2E7D32",
        "TIME_LIMIT": "#C62828",
        "MEM_LIMIT": "#6A1B9A",
    }
    orden_familias = {"C": 0, "R": 1, "RC": 2}
    colores_familia = {"C": "#F2F6FC", "R": "#FDF4EC", "RC": "#F1F8F1"}

    # Máximo global para que los 3 paneles (sharey) usen el mismo eje
    todos_gaps = [
        float(f["mip_gap_pct"])
        for f in filas
        if f.get("mip_gap_pct", "").strip() != ""
    ]
    tope = max(todos_gaps, default=0) * 1.15 + 2

    fig, axes = plt.subplots(1, 3, figsize=(24, 9), sharey=True)
    gaps_sin_incumbent = []

    for ax, escala in zip(axes, escalas):
        grupo = [fila for fila in filas if fila["scale"] == escala]

        familia_por_instancia = {
            fila["instance"]: fila["family"] for fila in grupo
        }
        instancias = sorted(
            familia_por_instancia,
            key=lambda nombre: (
                orden_familias.get(familia_por_instancia[nombre], 99),
                nombre,
            ),
        )
        posicion = {instancia: i for i, instancia in enumerate(instancias)}

        # Bandas de fondo y etiqueta por familia (C / R / RC)
        inicio = 0
        for fam in ["C", "R", "RC"]:
            n_fam = sum(
                1 for i in instancias if familia_por_instancia[i] == fam
            )
            if n_fam == 0:
                continue
            ax.axvspan(
                inicio - 0.5,
                inicio + n_fam - 0.5,
                color=colores_familia[fam],
                zorder=0,
            )
            ax.text(
                inicio + (n_fam - 1) / 2,
                1.01,
                fam,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=12,
                fontweight="bold",
            )
            inicio += n_fam

        pares = []

        for instancia in instancias:
            valores_par = {}

            for solver, desplazamiento in [
                ("Gurobi", -0.12),
                ("CPLEX", 0.12),
            ]:
                fila = next(
                    (
                        f for f in grupo
                        if f["instance"] == instancia
                        and f["solver"] == solver
                    ),
                    None,
                )

                if fila is None:
                    continue

                valor_gap = fila.get("mip_gap_pct", "").strip()

                if valor_gap == "":
                    gaps_sin_incumbent.append(
                        f"{instancia} ({solver})"
                    )
                    continue

                gap = float(valor_gap)
                estado = fila["status"]
                marcador = marcadores_estado.get(estado, "x")
                x = posicion[instancia] + desplazamiento

                ax.scatter(
                    x,
                    gap,
                    color=colores_solver[solver],
                    marker=marcador,
                    s=110,
                    edgecolors=colores_estado.get(estado, "black"),
                    linewidths=2.0,
                    zorder=3,
                )
                valores_par[solver] = (x, gap)

            if "Gurobi" in valores_par and "CPLEX" in valores_par:
                pares.append(
                    (valores_par["Gurobi"], valores_par["CPLEX"])
                )

        # Conector con el color del solver que tiene menor gap
        for gurobi, cplex in pares:
            gana_gurobi = gurobi[1] <= cplex[1]
            ax.plot(
                [gurobi[0], cplex[0]],
                [gurobi[1], cplex[1]],
                color=colores_solver["Gurobi" if gana_gurobi else "CPLEX"],
                linewidth=1.8,
                alpha=0.6,
                zorder=2,
            )

        # Resumen en el título
        gana_g = sum(1 for g, c in pares if g[1] <= c[1])
        ax.set_title(
            f"{escala} ({len(instancias)} inst.) | "
            f"Gurobi menor gap: {gana_g}/{len(pares)}",
            fontsize=13,
            pad=26,
        )

        ax.set_xticks(
            range(len(instancias)),
            instancias,
            rotation=55,
            ha="right",
            fontsize=11,
        )
        ax.set_xlim(-0.5, len(instancias) - 0.5)
        ax.set_ylim(-0.05 * tope, tope)  # margen abajo para gap = 0
        ax.tick_params(axis="y", labelsize=11)
        ax.grid(True, axis="y", alpha=0.25)

        if ax is axes[0]:
            ax.set_ylabel("MIPGap (%)", fontsize=12)

    leyenda_solver = [
        Line2D(
            [0], [0],
            marker="o",
            color=color,
            linestyle="none",
            label=solver,
        )
        for solver, color in colores_solver.items()
    ]
    leyenda_estado = [
        Line2D(
            [0], [0],
            marker=marcador,
            color="white",
            markerfacecolor="white",
            markeredgecolor=colores_estado[estado],
            markeredgewidth=1.8,
            linestyle="none",
            label=estado,
        )
        for estado, marcador in marcadores_estado.items()
    ]

    fig.suptitle("Comparación de MIPGap: Gurobi y CPLEX", fontsize=18)
    # Reserva filas distintas para leyenda y nota, fuera de los ejes.
    nota = fill(
        "Sin MIPGap por falta de incumbent: " + ", ".join(gaps_sin_incumbent),
        width=140,
    ) if gaps_sin_incumbent else ""
    alto_nota = (len(nota.splitlines()) * 14 / 72 / fig.get_figheight())
    base_leyenda = 0.025 + alto_nota + (0.025 if nota else 0)
    fig.legend(
        handles=leyenda_solver + leyenda_estado,
        loc="lower center",
        bbox_to_anchor=(0.5, base_leyenda),
        ncol=5,
        frameon=False,
        fontsize=13,
        markerscale=1.6,
    )

    if nota:
        fig.text(0.5, 0.025, nota, ha="center", va="bottom", fontsize=11)
    fig.tight_layout(rect=[0, base_leyenda + 0.07, 1, 0.93])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico MIPGap guardado en: {output_file}")

def graficar_incumbent_cota(
    csv_path: Path,
    output_file: Path,
) -> None:
    with open(csv_path, "r", encoding="utf-8", newline="") as file:
        filas = list(csv.DictReader(file))

    escalas = ["n=10", "n=15", "n=25"]
    colores_solver = {
        "Gurobi": "#2A6FDB",
        "CPLEX": "#E07026",
    }
    orden_familias = {"C": 0, "R": 1, "RC": 2}
    colores_familia = {"C": "#F2F6FC", "R": "#FDF4EC", "RC": "#F1F8F1"}

    fig, axes = plt.subplots(1, 3, figsize=(24, 9), sharey=True)
    valores_grafico = []
    sin_incumbent = []

    for ax, escala in zip(axes, escalas):
        grupo = [fila for fila in filas if fila["scale"] == escala]

        familia_por_instancia = {
            fila["instance"]: fila["family"] for fila in grupo
        }
        instancias = sorted(
            familia_por_instancia,
            key=lambda nombre: (
                orden_familias.get(familia_por_instancia[nombre], 99),
                nombre,
            ),
        )
        posicion = {instancia: i for i, instancia in enumerate(instancias)}

        # Bandas de fondo y etiqueta por familia (C / R / RC)
        inicio = 0
        for fam in ["C", "R", "RC"]:
            n_fam = sum(
                1 for i in instancias if familia_por_instancia[i] == fam
            )
            if n_fam == 0:
                continue
            ax.axvspan(
                inicio - 0.5,
                inicio + n_fam - 0.5,
                color=colores_familia[fam],
                zorder=0,
            )
            ax.text(
                inicio + (n_fam - 1) / 2,
                1.01,
                fam,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=12,
                fontweight="bold",
            )
            inicio += n_fam

        for instancia in instancias:
            for solver, desplazamiento in [
                ("Gurobi", -0.12),
                ("CPLEX", 0.12),
            ]:
                fila = next(
                    (
                        f for f in grupo
                        if f["instance"] == instancia
                        and f["solver"] == solver
                    ),
                    None,
                )

                if fila is None:
                    continue

                x = posicion[instancia] + desplazamiento
                color = colores_solver[solver]

                texto_cota = fila.get("best_bound", "").strip()
                texto_incumbent = fila.get("best_objective", "").strip()

                cota = float(texto_cota) if texto_cota else None
                incumbent = (
                    float(texto_incumbent) if texto_incumbent else None
                )

                if cota is not None:
                    valores_grafico.append(cota)
                    ax.scatter(
                        x,
                        cota,
                        marker="s",
                        s=110,
                        facecolors="white",
                        edgecolors=color,
                        linewidths=2.2,
                        zorder=3,
                    )

                if incumbent is not None:
                    valores_grafico.append(incumbent)
                    ax.scatter(
                        x,
                        incumbent,
                        marker="o",
                        s=110,
                        color=color,
                        edgecolors="black",
                        linewidths=0.8,
                        zorder=4,
                    )
                else:
                    sin_incumbent.append(f"{instancia} ({solver})")

                if cota is not None and incumbent is not None:
                    ax.vlines(
                        x,
                        min(cota, incumbent),
                        max(cota, incumbent),
                        color=color,
                        alpha=0.65,
                        linewidth=2.2,
                        zorder=2,
                    )

        ax.set_title(
            f"{escala} ({len(instancias)} instancias)",
            fontsize=13,
            pad=26,
        )
        ax.set_xticks(
            range(len(instancias)),
            instancias,
            rotation=55,
            ha="right",
            fontsize=11,
        )
        ax.set_xlim(-0.5, len(instancias) - 0.5)
        ax.tick_params(axis="y", labelsize=11)
        ax.grid(True, axis="y", alpha=0.25)

        if ax is axes[0]:
            ax.set_ylabel("Distancia objetivo", fontsize=12)

    if valores_grafico:
        minimo = min(valores_grafico)
        maximo = max(valores_grafico)
        margen = (maximo - minimo) * 0.08
        for ax in axes:
            ax.set_ylim(minimo - margen, maximo + margen)

    leyenda = [
        Line2D(
            [0], [0],
            color=color,
            linewidth=2.5,
            label=solver,
        )
        for solver, color in colores_solver.items()
    ]
    leyenda.extend([
        Line2D(
            [0], [0],
            marker="o",
            color="white",
            markerfacecolor="#555555",
            markeredgecolor="black",
            linestyle="none",
            label="Incumbent",
        ),
        Line2D(
            [0], [0],
            marker="s",
            color="white",
            markerfacecolor="white",
            markeredgecolor="#555555",
            markeredgewidth=1.8,
            linestyle="none",
            label="Mejor cota",
        ),
    ])

    fig.suptitle(
        "Mejor solución encontrada frente a mejor cota",
        fontsize=18,
    )

    # Nota al fondo de la figura (una sola línea)
    y_nota = 0.01
    if sin_incumbent:
        nota = "Sin incumbent: " + ", ".join(sin_incumbent)
        fig.text(
            0.5,
            y_nota,
            nota,
            ha="center",
            va="bottom",
            fontsize=9,
            color="#444444",
        )
        y_leyenda = y_nota + 0.035
    else:
        y_leyenda = 0.015

    # Leyenda justo encima de la nota
    fig.legend(
        handles=leyenda,
        loc="lower center",
        bbox_to_anchor=(0.5, y_leyenda),
        ncol=4,
        frameon=False,
        fontsize=13,
        markerscale=1.6,
    )

    # Los gráficos empiezan sobre la leyenda
    fig.tight_layout(rect=[0, y_leyenda + 0.06, 1, 0.93])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico incumbent-cota guardado en: {output_file}")

def graficar_optimos_por_tamano(
    csv_path: Path,
    output_file: Path,
) -> None:
    with open(csv_path, "r", encoding="utf-8", newline="") as file:
        filas = list(csv.DictReader(file))

    escalas = ["n=10", "n=15", "n=25"]
    solvers = ["Gurobi", "CPLEX"]
    colores = {
        "Gurobi": "#2A6FDB",
        "CPLEX": "#E07026",
    }
    color_fondo = "#E6E8EB"

    fig, ax = plt.subplots(figsize=(13, 8))
    ancho = 0.36

    for indice_solver, solver in enumerate(solvers):
        desplazamiento = (
            -ancho / 2 if indice_solver == 0 else ancho / 2
        )

        for indice_escala, escala in enumerate(escalas):
            casos = [
                fila for fila in filas
                if fila["scale"] == escala
                and fila["solver"] == solver
            ]
            total = len(casos)

            if total == 0:
                continue

            optimas = sum(
                fila["status"] == "OPTIMAL" for fila in casos
            )
            porcentaje = 100 * optimas / total
            x = indice_escala + desplazamiento

            # Fondo gris: casos que no llegaron al óptimo
            ax.bar(
                x,
                100,
                width=ancho,
                color=color_fondo,
                edgecolor="white",
                zorder=1,
            )

            # Parte coloreada: casos resueltos óptimamente
            ax.bar(
                x,
                porcentaje,
                width=ancho,
                color=colores[solver],
                edgecolor="white",
                zorder=2,
            )

            # Porcentaje sobre la barra
            ax.text(
                x,
                102,
                f"{porcentaje:.0f}%",
                ha="center",
                va="bottom",
                fontsize=13,
                fontweight="bold",
                color=colores[solver],
            )

            # Cantidad óptima / total dentro de la barra
            if porcentaje >= 12:
                ax.text(
                    x,
                    porcentaje / 2,
                    f"{optimas}/{total}",
                    ha="center",
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                    color="white",
                    zorder=3,
                )
            else:
                ax.text(
                    x,
                    porcentaje + 12,
                    f"{optimas}/{total}",
                    ha="center",
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                    color="#444444",
                    zorder=3,
                )

            # Nombre del solver bajo cada barra
            ax.text(
                x,
                -3,
                solver,
                ha="center",
                va="top",
                fontsize=10,
                color="#444444",
            )

    ax.set_xticks(range(len(escalas)))
    ax.set_xticklabels(escalas, fontsize=14, fontweight="bold")
    ax.tick_params(axis="x", pad=22)  # deja espacio al nombre del solver
    ax.tick_params(axis="y", labelsize=12)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Instancias resueltas óptimamente (%)", fontsize=13)
    ax.set_title("Resolución óptima por tamaño", fontsize=18, pad=16)
    ax.grid(True, axis="y", alpha=0.25)
    ax.set_axisbelow(True)

    leyenda = [
        Line2D(
            [0], [0],
            marker="s",
            color="white",
            markerfacecolor=colores["Gurobi"],
            markersize=12,
            label="Gurobi: óptimas",
        ),
        Line2D(
            [0], [0],
            marker="s",
            color="white",
            markerfacecolor=colores["CPLEX"],
            markersize=12,
            label="CPLEX: óptimas",
        ),
        Line2D(
            [0], [0],
            marker="s",
            color="white",
            markerfacecolor=color_fondo,
            markeredgecolor="#AAAAAA",
            markersize=12,
            label="No óptimas",
        ),
    ]

    ax.legend(
        handles=leyenda,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=3,
        frameon=False,
        fontsize=13,
    )

    # Nota al fondo (una sola línea)
    fig.text(
        0.5,
        0.01,
        "Dentro de cada barra: cantidad óptima / total de instancias.",
        ha="center",
        va="bottom",
        fontsize=10,
        color="#444444",
    )
    fig.tight_layout(rect=[0, 0.05, 1, 1])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico de óptimos guardado en: {output_file}")



def main() -> None:
    data = load_evrptw_instance(
        str(INSTANCE_FILE),
        station_copies=2,
    )

    with open(RESULT_FILE, "r", encoding="utf-8") as file:
        result = json.load(file)

    graficar_mapa_rutas(data, result, OUTPUT_FILE)
    graficar_bateria_soc(data, result, SOC_OUTPUT_FILE)
    graficar_tiempos(CSV_FILE, TIEMPOS_OUTPUT_FILE)
    graficar_mipgap(CSV_FILE, MIPGAP_OUTPUT_FILE)
    graficar_incumbent_cota(CSV_FILE, OBJETIVOS_OUTPUT_FILE)
    graficar_optimos_por_tamano(CSV_FILE, OPTIMOS_OUTPUT_FILE)



if __name__ == "__main__":
    main()
