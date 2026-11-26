"""
Para centralizar las instancias de evaluacion y sus parametros
Cada categoría espacial (C: Agrupadas, R: Aleatorias, RC: Mixtas) cuenta con >= 3 instancias.
"""


# 1. Validación cruzada rapida (Ticket 5): n=5 y n=10 (3 por escala, 1 de cada familia)
VALIDATION_INSTANCES = [
    # n = 5 (C5 oficiales)
    {"file": "data/c101C5.txt",   "family": "C",  "scale": "n=5",  "max_customers": None, "num_vehicles": 3, "station_copies": 2},
    {"file": "data/r104C5.txt",   "family": "R",  "scale": "n=5",  "max_customers": None, "num_vehicles": 3, "station_copies": 2},
    {"file": "data/rc105C5.txt",  "family": "RC", "scale": "n=5",  "max_customers": None, "num_vehicles": 3, "station_copies": 2},
    # n = 10 (C10 oficiales)
    {"file": "data/c101C10.txt",  "family": "C",  "scale": "n=10", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/r102C10.txt",  "family": "R",  "scale": "n=10", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/rc102C10.txt", "family": "RC", "scale": "n=10", "max_customers": None, "num_vehicles": 5, "station_copies": 2},
]

# 2. Bateria completa de Benchmarking (Ticket 6): >= 3 instancias por categoría en cada escala
BENCHMARK_INSTANCES = [
    # --- Escala n = 10 (3 C, 3 R, 3 RC) ---
    {"file": "data/c101C10.txt",  "family": "C",  "scale": "n=10", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/c104C10.txt",  "family": "C",  "scale": "n=10", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/c202C10.txt",  "family": "C",  "scale": "n=10", "max_customers": None, "num_vehicles": 3, "station_copies": 2},
    {"file": "data/r102C10.txt",  "family": "R",  "scale": "n=10", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/r103C10.txt",  "family": "R",  "scale": "n=10", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/r201C10.txt",  "family": "R",  "scale": "n=10", "max_customers": None, "num_vehicles": 3, "station_copies": 2},
    {"file": "data/rc102C10.txt", "family": "RC", "scale": "n=10", "max_customers": None, "num_vehicles": 5, "station_copies": 2},
    {"file": "data/rc108C10.txt", "family": "RC", "scale": "n=10", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/rc201C10.txt", "family": "RC", "scale": "n=10", "max_customers": None, "num_vehicles": 3, "station_copies": 2},

    # --- Escala n = 15 (3 C, 3 R, 3 RC) ---
    {"file": "data/c103C15.txt",  "family": "C",  "scale": "n=15", "max_customers": None, "num_vehicles": 5, "station_copies": 2},
    {"file": "data/c106C15.txt",  "family": "C",  "scale": "n=15", "max_customers": None, "num_vehicles": 5, "station_copies": 2},
    {"file": "data/c202C15.txt",  "family": "C",  "scale": "n=15", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/r102C15.txt",  "family": "R",  "scale": "n=15", "max_customers": None, "num_vehicles": 6, "station_copies": 2},
    {"file": "data/r105C15.txt",  "family": "R",  "scale": "n=15", "max_customers": None, "num_vehicles": 6, "station_copies": 2},
    {"file": "data/r202C15.txt",  "family": "R",  "scale": "n=15", "max_customers": None, "num_vehicles": 4, "station_copies": 2},
    {"file": "data/rc103C15.txt", "family": "RC", "scale": "n=15", "max_customers": None, "num_vehicles": 6, "station_copies": 2},
    {"file": "data/rc108C15.txt", "family": "RC", "scale": "n=15", "max_customers": None, "num_vehicles": 5, "station_copies": 2},
    {"file": "data/rc202C15.txt", "family": "RC", "scale": "n=15", "max_customers": None, "num_vehicles": 4, "station_copies": 2},

    # --- Escala n = 25 (estres, sacadas de *_21.txt) ---
    {"file": "data/c101_21.txt",  "family": "C",  "scale": "n=25", "max_customers": 25,   "num_vehicles": 6, "station_copies": 1},
    {"file": "data/r101_21.txt",  "family": "R",  "scale": "n=25", "max_customers": 25,   "num_vehicles": 8, "station_copies": 1},
    {"file": "data/rc101_21.txt", "family": "RC", "scale": "n=25", "max_customers": 25,   "num_vehicles": 7, "station_copies": 1},
]