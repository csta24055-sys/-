"""Synthetic (fictional) building scenarios for the approximation study.

Research tooling only. Every number is produced by a seeded random generator;
nothing comes from J-CAT or from any real factor, service-life or rate table.
Results obtained on this data say nothing about accuracy on real buildings.
"""
from .generate import make_scenario, DEFAULT_OPTIONS, OPTION_HELP
from .io import from_dict, load_json, save_json, to_dict
from .model import INPUT_FIELD_MAP, Scenario, check_input_coverage
from .population import edge_cases, standard_benchmark, verification_population

__all__ = [
    "make_scenario", "DEFAULT_OPTIONS", "OPTION_HELP",
    "to_dict", "from_dict", "save_json", "load_json",
    "INPUT_FIELD_MAP", "Scenario", "check_input_coverage",
    "standard_benchmark", "verification_population", "edge_cases",
]
