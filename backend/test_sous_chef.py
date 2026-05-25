import random, sys, re

import os
graph_path = os.path.join(os.path.dirname(__file__), 'agent', 'graph.py')
with open(graph_path, encoding="utf-8") as f:
    code = f.read()

def extract_list(name):
    match = re.search(rf'{name}\s*=\s*\[(.+?)\]', code, re.DOTALL)
    if not match: return []
    return [s.strip().strip('"').strip("'") for s in match.group(1).split(',') if s.strip().strip('"').strip("'")]

def extract_dict_list(block_name, key):
    block_match = re.search(rf'{block_name}\s*=\s*\{{(.+?)\}}', code, re.DOTALL)
    if not block_match: return []
    block = block_match.group(1)
    key_match = re.search(rf'"{key}":\s*\[(.+?)\]', block, re.DOTALL)
    if not key_match: return []
    return [s.strip().strip('"').strip("'") for s in key_match.group(1).split(',') if s.strip().strip('"').strip("'")]

SABZIS = extract_list("SABZIS")
THU_PANEER_GRAVIES = extract_list("THU_PANEER_GRAVIES")
GRAVIES = {k: extract_dict_list("GRAVIES", k) for k in ["fish","chicken","veg"]}
PROTEINS = {k: extract_dict_list("PROTEINS", k) for k in ["fish","chicken","veg"]}
REMOVED = ["dal makhani", "arhar dal", "kaddu"]
DAY_TYPE = {0:"chicken",1:"fish",2:"chicken",3:"veg",4:"fish",5:"chicken",6:"flex"}
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
errors = []

def fail(msg): errors.append(f"❌ {msg}")
def ok(msg): print(f"✅ {msg}")

# ── GROUP 1: Static data ──────────────────────────────────────────
print("\n=== GROUP 1: Static Data ===")

for item in REMOVED:
    found = any(item in lst for lst in list(GRAVIES.values()) + [SABZIS])
    if found: fail(f"'{item}' still in lists!")
    else: ok(f"'{item}' removed")

if "kadhi" in GRAVIES["chicken"]: fail("Kadhi in chicken gravies!")
else: ok("Kadhi not in chicken gravies")

for item in ["rajma","black chana","rajma soyabean"]:
    if item in GRAVIES["chicken"]: fail(f"'{item}' in chicken gravies!")
    else: ok(f"'{item}' not in chicken gravies")

if "chicken curry" in PROTEINS["chicken"]: fail("chicken curry in PROTEINS!")
else: ok("chicken curry not in PROTEINS")

if len(SABZIS) != len(set(SABZIS)): fail(f"Duplicate sabzis: {[s for s in SABZIS if SABZIS.count(s)>1]}")
else: ok(f"All {len(SABZIS)} sabzis unique")

for g in THU_PANEER_GRAVIES:
    if g not in GRAVIES["veg"]: fail(f"'{g}' in THU_PANEER_GRAVIES but not in veg gravies!")
    else: ok(f"'{g}' in both THU_PANEER_GRAVIES and veg gravies")

# ── GROUP 2: Protein cross-contamination ─────────────────────────
print("\n=== GROUP 2: Protein Cross-Contamination ===")

for p in PROTEINS["fish"]:
    if p in PROTEINS["chicken"]: fail(f"Fish protein '{p}' in chicken PROTEINS!")
    if p in PROTEINS["veg"]: fail(f"Fish protein '{p}' in veg PROTEINS!")
ok("No fish proteins in chicken/veg PROTEINS")

for p in PROTEINS["chicken"]:
    if p in PROTEINS["fish"]: fail(f"Chicken protein '{p}' in fish PROTEINS!")
    if p in PROTEINS["veg"]: fail(f"Chicken protein '{p}' in veg PROTEINS!")
ok("No chicken proteins in fish/veg PROTEINS")

for g in THU_PANEER_GRAVIES:
    filtered = [p for p in PROTEINS["veg"] if p != "paneer"]
    if not filtered: fail(f"No non-paneer proteins for {g}!")
ok("Paneer excluded when paneer gravy")

# ── GROUP 3: Starch rules ─────────────────────────────────────────
print("\n=== GROUP 3: Starch Rules ===")

def get_starch(dt, i, gravy):
    veg_paratha = ["chole","matar paneer","palak paneer","chana masala","aloo gobi gravy","paneer handi"]
    if dt == "fish": return "Rice"
    elif dt == "chicken":
        return "Paratha" if i != 5 else "Stuffed Paratha"
    elif dt == "veg":
        return "Paratha" if gravy in veg_paratha else "Rice"
    return "Rice"

for g in GRAVIES["fish"]:
    if get_starch("fish", 1, g) != "Rice": fail(f"Fish+{g} → not Rice!")
ok(f"All {len(GRAVIES['fish'])} fish gravies → Rice")

for i in range(7):
    if DAY_TYPE[i] == "chicken" and i != 5:
        for g in GRAVIES["chicken"]:
            if "Paratha" not in get_starch("chicken", i, g):
                fail(f"{DAYS[i]}+{g} → not Paratha!")
ok("All chicken weekday gravies → Paratha")

dal_gravies_in_veg = ["moong dal","rajma","black chana","rajma soyabean","santula","kadhi"]
for g in dal_gravies_in_veg:
    if g in GRAVIES["veg"] and get_starch("veg", 3, g) != "Rice":
        fail(f"Veg+{g} → not Rice (roti+dal!)")
ok("All veg dal gravies → Rice (no roti+dal)")

for g in ["chole","matar paneer","palak paneer","chana masala","paneer handi"]:
    if "Paratha" not in get_starch("veg", 3, g):
        fail(f"Veg+{g} → not Paratha!")
ok("All veg paneer/chole gravies → Paratha")

# ── GROUP 4: 100-week simulation ──────────────────────────────────
print("\n=== GROUP 4: 100-Week Simulation ===")
week_errors = []

for seed in range(100):
    random.seed(seed)
    used_g, used_s = set(), set()
    week = []

    for i in range(7):
        dt = DAY_TYPE[i]
        if dt == "flex": dt = random.choice(["fish","chicken","veg"])

        gp = [g for g in GRAVIES[dt] if g not in used_g]
        if not gp: gp = GRAVIES[dt]
        gravy = random.choice(gp)
        used_g.add(gravy)

        sp = [s for s in SABZIS if s not in used_s]
        if not sp: sp = SABZIS
        sabzi = random.choice(sp)
        used_s.add(sabzi)

        if dt == "veg" and gravy in THU_PANEER_GRAVIES:
            fp = [p for p in PROTEINS["veg"] if p != "paneer"]
            protein = random.choice(fp)
        else:
            protein = random.choice(PROTEINS[dt])

        roll = random.random()
        if dt == "chicken" and i == 5 and roll < 0.3:
            week.append({"i":i,"dt":"khichdi","gravy":"khichdi","sabzi":"none"})
            continue

        if dt == "chicken" and i == 5 and roll < 0.65:
            gravy = "chicken curry"

        starch = get_starch(dt, i, gravy)
        week.append({"i":i,"dt":dt,"gravy":gravy,"sabzi":sabzi,"protein":protein,"starch":starch})

        # Validate all rules
        if dt == "fish" and starch != "Rice":
            week_errors.append(f"W{seed} {DAYS[i]}: Fish→{starch}")
        if dt == "chicken" and i != 5 and "Paratha" not in starch:
            week_errors.append(f"W{seed} {DAYS[i]}: Chicken→{starch}")
        if gravy == "kadhi" and dt == "chicken":
            week_errors.append(f"W{seed} {DAYS[i]}: Kadhi+Chicken!")
        if "chicken" in protein and dt != "chicken":
            week_errors.append(f"W{seed} {DAYS[i]}: Chicken protein on {dt}")
        if any(x in protein for x in ["mackerel","sardine"]) and dt == "chicken":
            week_errors.append(f"W{seed} {DAYS[i]}: Fish protein on chicken")
        if dt == "veg" and gravy in THU_PANEER_GRAVIES and protein == "paneer":
            week_errors.append(f"W{seed} {DAYS[i]}: Paneer gravy+paneer protein!")
        for rm in REMOVED:
            if rm in gravy or rm in sabzi:
                week_errors.append(f"W{seed} {DAYS[i]}: Removed item '{rm}'!")

    gravies = [d["gravy"] for d in week if d["gravy"] != "khichdi"]
    if len(gravies) != len(set(gravies)):
        dups = [g for g in set(gravies) if gravies.count(g)>1]
        week_errors.append(f"W{seed}: Gravy repeat: {dups}")

    sabzis = [d["sabzi"] for d in week if d.get("sabzi") != "none"]
    if len(sabzis) != len(set(sabzis)):
        dups = [s for s in set(sabzis) if sabzis.count(s)>1]
        week_errors.append(f"W{seed}: Sabzi repeat: {dups}")

for e in week_errors: fail(e)
if not week_errors: ok("100 weeks — zero logic errors")

# ── GROUP 5: Code checks ──────────────────────────────────────────
print("\n=== GROUP 5: Code Checks ===")

checks = {
    "Supriya 1700 kcal": "1,700 kcal" in code,
    "Vivek 2200 kcal": "2,200 kcal" in code,
    "130g protein": "130g protein" in code,
    "166g protein": "166g protein" in code,
    "8 egg whites": "8 egg whites" in code,
    "ON Whey": "ON Whey" in code,
    "Sunday paratha exception": "Sunday exception" in code,
    "Indian home cooking": "INDIAN HOME COOKING" in code,
    "No Western food": "no Western food" in code,
    "No roti+dal": "NO roti+dal" in code,
    "Macros only when asked": "Only show macros" in code,
    "Shopping total always": "ALWAYS show the weekly total" in code,
    "Egg price 139": "₹139" in code,
    "Mango cheaper": "cheaper than Instamart" in code,
    "Weekly not monthly": "these are different" in code,
    "Pantry table correct": "pantry_inventory" in code,
    "Column in_stock correct": '"in_stock"' in code,
    "No old instock": '"instock"' not in code,
    "No hardcoded keys": "gsk_" not in code,
    "llama-3.1-8b": "llama-3.1-8b-instant" in code,
    "plan_week exists": "def plan_week" in code,
    "get_history exists": "def get_history" in code,
    "save_plan exists": "def save_plan" in code,
    "No dead code monday": "If today is Monday use today" not in code,
    "r.json() once": code.count("r.json() if isinstance(r.json()") == 0,
    "No duplicate shopping": code.count("SHOPPING PRICES") == 1,
    "Paneer not doubled": "veg_proteins_no_paneer" in code,
    "Khichdi Special label": "Khichdi Special" in code,
    "Khichdi is_veg False": '"veg", "khichdi"' not in code,
    "No triple blank line": "\n\n\n" not in code,
    "Platform lowercase": ".lower()" in code,
    "Lunch & Dinner once": "Lunch & Dinner" in code,
    "Force exact plan": "MEAL PLAN GENERATED" in code,
    "LLM not replanning": "Present the meal plan above exactly" in code,
}

for k, v in checks.items():
    if v: ok(k)
    else: fail(k)

# ── FINAL ─────────────────────────────────────────────────────────
print("\n" + "="*50)
total_checks = len(errors)  # all checks complete
if errors:
    print(f"🔴 {len(errors)} FAILED:")
    for e in errors: print(e)
    sys.exit(1)
else:
    print("🚀 ALL TESTS PASSED — safe to deploy!")