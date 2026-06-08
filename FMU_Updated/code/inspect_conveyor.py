"""
inspect_conveyor.py
===================
Print all variables in the conveyor FMU.
"""
from fmpy import read_model_description

FMU_PATH = r"C:\Users\satres\Documents\ALIX\FMU_Updated\FMUS\Conveyor_updated_v3.fmu"

md = read_model_description(FMU_PATH)

print("=" * 70)
print("CONVEYOR FMU - ALL VARIABLES BY CATEGORY")
print("=" * 70)

for causality in ["input", "output", "parameter", "calculatedParameter", "local"]:
    vars_in_group = [v for v in md.modelVariables if v.causality == causality]
    if vars_in_group:
        print(f"\n--- {causality.upper()} ({len(vars_in_group)}) ---")
        for v in vars_in_group:
            var = v.variability if hasattr(v, "variability") else "?"
            start = ""
            if hasattr(v, "start") and v.start is not None:
                start = f"start={v.start}"
            print(f"   {v.name:<55} type={v.type:<10} variability={var:<10} {start}")

# Search for likely calibration parameters
print("\n" + "=" * 70)
print("LIKELY TUNABLE MOTOR PARAMETERS")
print("=" * 70)
keywords = ["rs", "rr", "r_s", "r_r", "lm", "l_m", "ls", "lsig", "lsigma",
            "stator", "rotor", "resistance", "inductance"]
found = False
for v in md.modelVariables:
    name_lower = v.name.lower()
    for kw in keywords:
        if kw in name_lower:
            var = v.variability if hasattr(v, "variability") else "?"
            start = v.start if hasattr(v, "start") and v.start is not None else ""
            tunable_mark = "<-- TUNABLE" if var == "tunable" else ""
            print(f"   {v.name:<55} variability={var:<12} start={start}  {tunable_mark}")
            found = True
            break

if not found:
    print("   (no obvious motor parameters found — see full parameter list above)")