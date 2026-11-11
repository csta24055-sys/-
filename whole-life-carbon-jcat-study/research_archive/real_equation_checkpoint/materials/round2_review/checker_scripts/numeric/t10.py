from h import *
nan, inf = float("nan"), float("inf")
def case(name, fn, seed=1, period=60.0, **opts):
    s = mk(seed, period, **opts); fn(s)
    r = check(s, name)
    if not r: print(f"[{name}] no difference")
    return s
print("gases:", mk(1).gases, mk(1).gwp)
case("gases_without_CO2_composites", lambda s: setattr(s, "gases", [g for g in s.gases if g != "CO2"]), composite_share=0.5, epd_share=0.0)
case("gases_without_CO2_no_composites", lambda s: setattr(s, "gases", [g for g in s.gases if g != "CO2"]), composite_share=0.0, epd_share=0.0)
case("gases_duplicate_composites", lambda s: setattr(s, "gases", list(s.gases) + [s.gases[0]]), composite_share=0.5, epd_share=0.0)
case("gases_duplicate_no_composites", lambda s: setattr(s, "gases", list(s.gases) + [s.gases[0]]), composite_share=0.0, epd_share=0.0)
case("gases_empty_composites", lambda s: setattr(s, "gases", []), composite_share=0.5, epd_share=0.0)
case("gases_reversed", lambda s: setattr(s, "gases", list(reversed(s.gases))), composite_share=0.5, epd_share=0.0)
case("gases_tuple", lambda s: setattr(s, "gases", tuple(s.gases)), composite_share=0.5)
def extra_gas(s):
    s.gases = list(s.gases) + ["SF6"]; s.gwp["SF6"] = 20000.0
case("gas_unknown_to_factors", extra_gas, composite_share=0.5)
def missing_amount(s):
    row = next(r for r in s.materials if r.composition)
    s.factors[row.composition[0].factor_id].gas_amounts.pop("CH4", None)
case("component_gas_amount_missing", missing_amount, composite_share=0.5, epd_share=0.0)
# long periods
for T, lives in ((1000.0, [0.3, 7.5, 33.3]), (999.9, [1.0, 11.1]), (500.5, [0.5, 250.25, 500.5])):
    s = mk(2, T, table_length=1001, service_life_choices=lives, replacement_cycle=lives[-1], reconstruction_scenario="REBUILD_IDENTICAL")
    r = check(s, f"T={T}")
    if not r: print(f"[T={T}] no difference")
# very small periods with events
for T, lives in ((1e-3, [1e-4, 3e-4]), (0.3, [0.1, 0.05]), (1.0, [0.999999999, 1.0, 0.5])):
    s = mk(2, T, service_life_choices=lives, replacement_cycle=lives[0], reconstruction_scenario="REBUILD_IDENTICAL")
    r = check(s, f"T={T}", floor_rel=1e-15)
    if not r: print(f"[T={T}] no difference")
