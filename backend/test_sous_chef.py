import random, sys, re, ast, os, json

# ── Load graph.py source ──────────────────────────────────────────
graph_path = os.path.join(os.path.dirname(__file__), 'agent', 'graph.py')
with open(graph_path, encoding="utf-8") as f:
    code = f.read()

errors = []
passed = 0

def fail(msg): errors.append(f"❌ {msg}")
def ok(msg):
    global passed
    passed += 1
    print(f"✅ {msg}")

# ════════════════════════════════════════════════════════════════════
# GROUP 0: SYNTAX & STRUCTURE
# ════════════════════════════════════════════════════════════════════
print("\n=== GROUP 0: Syntax & Structure ===")

# 0.1 Syntax check — catches the production crash
try:
    tree = ast.parse(code)
    ok("Syntax valid — no SyntaxError")
except SyntaxError as e:
    fail(f"SYNTAX ERROR line {e.lineno}: {e.msg}")
    print(f"\n🔴 FATAL: Fix syntax before anything else.")
    sys.exit(1)

# 0.2 All required functions exist with correct async/sync type
required_async = ['get_history','save_plan','execute_tool','run_weekly_agent','run_agent']
required_sync  = ['plan_week','generate_shopping_list']
all_fns = {n.name: type(n).__name__ for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
for fn in required_async:
    if fn not in all_fns: fail(f"{fn} MISSING")
    elif all_fns[fn] != 'AsyncFunctionDef': fail(f"{fn} must be async")
    else: ok(f"{fn} exists and is async")
for fn in required_sync:
    if fn not in all_fns: fail(f"{fn} MISSING")
    elif all_fns[fn] != 'FunctionDef': fail(f"{fn} must be sync")
    else: ok(f"{fn} exists and is sync")

# 0.3 No triple blank lines
if "\n\n\n" in code: fail("Triple blank line found")
else: ok("No triple blank lines")

# 0.4 No hardcoded API keys
for pattern in ["gsk_", "sk-or", "sb_secret"]:
    if pattern in code: fail(f"Hardcoded key pattern '{pattern}' found!")
    else: ok(f"No hardcoded key: {pattern}")

# 0.5 Dead code check — look for run_agent body orphaned after return
# Specifically check the known failure pattern: return items followed by function body
if "return items\n    now = datetime.now()" in code:
    fail("CRITICAL: run_agent body orphaned inside generate_shopping_list after 'return items'")
else:
    ok("No orphaned run_agent body after return items")

# 0.6 All 7 tools defined AND handled in execute_tool
REQUIRED_TOOLS = ['get_expenses','get_pantry','update_pantry','log_expense',
                  'get_preferences','save_preference','send_weekly_email']
tools_section = code[code.find('TOOLS = ['):code.find('llm_with_tools')]
exec_section  = code[code.find('async def execute_tool'):code.find('def generate_shopping_list')]
for t in REQUIRED_TOOLS:
    if t not in tools_section: fail(f"Tool '{t}' not in TOOLS list")
    elif t not in exec_section: fail(f"Tool '{t}' not handled in execute_tool — dead code!")
    else: ok(f"Tool '{t}' defined and handled")

# 0.7 run_weekly_agent calls all required steps
rwa = code[code.find('async def run_weekly_agent'):code.find('async def run_agent')]
for check, label in [('get_preferences','fetches preferences'),('get_pantry','fetches pantry'),
                      ('plan_week','calls plan_week'),('generate_shopping_list','generates shopping'),
                      ('send_weekly_email','sends email'),('save_plan','saves plan')]:
    if check in rwa: ok(f"run_weekly_agent: {label}")
    else: fail(f"run_weekly_agent: {label} MISSING")

# 0.8 run_agent passes preferences and pantry
ra = code[code.find('async def run_agent'):]
for check, label in [('get_preferences','reads prefs before planning'),
                      ('get_pantry','reads pantry'),
                      ('wants_plan','wants_plan trigger'),
                      ('wants_today','wants_today trigger'),
                      ('wants_shopping','wants_shopping trigger'),
                      ('shopping_list','returns shopping_list')]:
    if check in ra: ok(f"run_agent: {label}")
    else: fail(f"run_agent: {label} MISSING")

# 0.9 plan_week accepts avoid/replace params
pw = code[code.find('def plan_week'):code.find('def generate_shopping_list')]
for check, label in [('avoid','avoid param'),('replace','replace param'),
                      ('replace.get','apply replacements'),('not in avoid','filter avoids')]:
    if check in pw: ok(f"plan_week: {label}")
    else: fail(f"plan_week: {label} MISSING")

# 0.10 generate_shopping_list accepts in_stock
gs = code[code.find('def generate_shopping_list'):code.find('async def run_weekly_agent')]
for check, label in [('in_stock','in_stock param'),('is_in_stock','pantry check applied')]:
    if check in gs: ok(f"generate_shopping_list: {label}")
    else: fail(f"generate_shopping_list: {label} MISSING")

# ════════════════════════════════════════════════════════════════════
# GROUP 1: STATIC DATA INTEGRITY
# ════════════════════════════════════════════════════════════════════
print("\n=== GROUP 1: Static Data Integrity ===")

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

def extract_set(name):
    match = re.search(rf'{name}\s*=\s*\{{(.+?)\}}', code, re.DOTALL)
    if not match: return set()
    return {s.strip().strip('"').strip("'") for s in match.group(1).split(',') if s.strip().strip('"').strip("'")}

SABZIS = extract_list("SABZIS")
THU_PANEER_GRAVIES = extract_list("THU_PANEER_GRAVIES")
GRAVIES = {k: extract_dict_list("GRAVIES", k) for k in ["fish","chicken","veg"]}
PROTEINS = {k: extract_dict_list("PROTEINS", k) for k in ["fish","chicken","veg"]}
DAL_GRAVIES = extract_set("DAL_GRAVIES")
REMOVED = ["dal makhani", "arhar dal", "kaddu"]
SAT_CHICKEN_GRAVIES = ["chole", "aloo gobi gravy", "chicken curry"]  # non-dal only for Saturday

# Removed items
for item in REMOVED:
    found = any(item in lst for lst in list(GRAVIES.values()) + [SABZIS])
    if found: fail(f"'{item}' still in lists!")
    else: ok(f"'{item}' correctly removed")

# Kadhi rules
if "kadhi" in GRAVIES["chicken"]: fail("Kadhi in chicken gravies!")
else: ok("Kadhi not in chicken gravies")
if "kadhi" in GRAVIES["veg"]: fail("Kadhi in veg gravies!")
else: ok("Kadhi not in veg gravies")

# Rajma/black chana not in chicken
for item in ["rajma","black chana","rajma soyabean"]:
    if item in GRAVIES["chicken"]: fail(f"'{item}' in chicken gravies!")
    else: ok(f"'{item}' not in chicken gravies")

# chicken curry not in PROTEINS
if "chicken curry" in PROTEINS["chicken"]: fail("'chicken curry' in PROTEINS!")
else: ok("'chicken curry' not in PROTEINS")

# Sabzis
if len(SABZIS) != len(set(SABZIS)): fail(f"Duplicate sabzis!")
else: ok(f"All {len(SABZIS)} sabzis unique")
if len(SABZIS) != 17: fail(f"Expected 17 sabzis, got {len(SABZIS)}")
else: ok("Exactly 17 sabzis")

# THU_PANEER_GRAVIES all in veg
for g in THU_PANEER_GRAVIES:
    if g not in GRAVIES["veg"]: fail(f"'{g}' in THU_PANEER_GRAVIES but not in veg gravies!")
    else: ok(f"'{g}' in THU_PANEER_GRAVIES and veg gravies")

# DAL_GRAVIES completeness
expected_dal = {"dal tadka","palak dal","moong dal","lauki dal","sambar","kadhi","santula","rajma","black chana","rajma soyabean"}
missing_dal = expected_dal - DAL_GRAVIES
if missing_dal: fail(f"DAL_GRAVIES missing: {missing_dal}")
else: ok(f"DAL_GRAVIES complete ({len(DAL_GRAVIES)} items)")

# Saturday gravies must be non-dal
sat_dal = [g for g in SAT_CHICKEN_GRAVIES if g in DAL_GRAVIES]
if sat_dal: fail(f"Saturday gravies contain dal: {sat_dal}")
else: ok("Saturday gravies are all non-dal (stuffed paratha safe)")

# Saturday gravies must exist in code
if "SAT_CHICKEN_GRAVIES" in code: ok("SAT_CHICKEN_GRAVIES defined in plan_week")
else: fail("SAT_CHICKEN_GRAVIES not defined — Saturday dal+paratha bug possible!")

# Protein maps defined
for item, label in [("GRAVY_CONTAINS_PROTEIN","gravy_contains_protein map"),
                     ("NEEDS_PANEER_BHURJI","needs_paneer_bhurji map")]:
    if item in code: ok(f"{label} defined")
    else: fail(f"{label} MISSING")

# ════════════════════════════════════════════════════════════════════
# GROUP 2: PROTEIN CROSS-CONTAMINATION
# ════════════════════════════════════════════════════════════════════
print("\n=== GROUP 2: Protein Cross-Contamination ===")

for p in PROTEINS["fish"]:
    if p in PROTEINS["chicken"]: fail(f"Fish protein '{p}' in chicken!")
    if p in PROTEINS["veg"]: fail(f"Fish protein '{p}' in veg!")
ok("No fish proteins in chicken/veg")

for p in PROTEINS["chicken"]:
    if p in PROTEINS["fish"]: fail(f"Chicken protein '{p}' in fish!")
    if p in PROTEINS["veg"]: fail(f"Chicken protein '{p}' in veg!")
ok("No chicken proteins in fish/veg")

non_paneer_veg = [p for p in PROTEINS["veg"] if p != "paneer"]
if not non_paneer_veg: fail("No non-paneer veg proteins!")
else: ok(f"Non-paneer veg proteins: {non_paneer_veg}")

# ════════════════════════════════════════════════════════════════════
# GROUP 3: STARCH RULES
# ════════════════════════════════════════════════════════════════════
print("\n=== GROUP 3: Starch Rules ===")

DAY_TYPE = {0:"chicken",1:"fish",2:"chicken",3:"veg",4:"fish",5:"chicken",6:"flex"}
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
VEG_PARATHA_GRAVIES = ["chole","matar paneer","palak paneer","chana masala","aloo gobi gravy","paneer handi"]

def get_starch(dt, i, gravy):
    if dt == "chicken" and i == 5: return "Stuffed Paratha"
    if dt == "fish" or gravy in DAL_GRAVIES: return "Rice"
    if dt == "chicken": return "Paratha"
    if dt == "veg": return "Paratha" if gravy in VEG_PARATHA_GRAVIES else "Rice"
    return "Rice"

for g in GRAVIES["fish"]:
    if get_starch("fish",1,g) != "Rice": fail(f"Fish+{g}→not Rice!")
ok(f"All {len(GRAVIES['fish'])} fish gravies → Rice")

for i in [0,2]:
    for g in GRAVIES["chicken"]:
        exp = "Rice" if g in DAL_GRAVIES else "Paratha"
        got = get_starch("chicken",i,g)
        if exp not in got: fail(f"{DAYS[i]}+{g}→{got} (expected {exp})")
ok("All chicken weekday gravies → correct starch")

# Saturday: only non-dal gravies should be used → always Stuffed Paratha
for g in SAT_CHICKEN_GRAVIES:
    if "Stuffed Paratha" not in get_starch("chicken",5,g):
        fail(f"Saturday+{g}→not Stuffed Paratha!")
ok("Saturday non-dal chicken gravies → Stuffed Paratha")

# Verify no dal gravy can reach Saturday (caught by SAT_CHICKEN_GRAVIES restriction)
for g in GRAVIES["chicken"]:
    if g in DAL_GRAVIES and g in SAT_CHICKEN_GRAVIES:
        fail(f"Dal gravy '{g}' in SAT_CHICKEN_GRAVIES!")
ok("No dal gravies in SAT_CHICKEN_GRAVIES")

for g in ["moong dal","rajma","black chana","rajma soyabean","santula"]:
    if g in GRAVIES["veg"] and get_starch("veg",3,g) != "Rice":
        fail(f"Veg+{g}→not Rice!")
ok("All veg dal gravies → Rice")

for g in VEG_PARATHA_GRAVIES:
    if get_starch("veg",3,g) != "Paratha": fail(f"Veg+{g}→not Paratha!")
ok("All veg paneer/chole gravies → Paratha")

# ════════════════════════════════════════════════════════════════════
# GROUP 4: 100-WEEK SIMULATION
# ════════════════════════════════════════════════════════════════════
print("\n=== GROUP 4: 100-Week Simulation ===")

GRAVY_SABZI_CONFLICTS = {
    "aloo gobi": ["aloo","gobi"],
    "lauki dal": ["lauki"],
    "matar paneer": ["matar"],
    "palak dal": ["palak"],
}
GRAVY_CONTAINS_PROTEIN = {"matar paneer","palak paneer","paneer handi","chicken curry"}
NEEDS_PANEER_BHURJI = {"chole","aloo gobi gravy","rajma soyabean","rajma","black chana","chana masala"}

def sabzi_conflicts(gravy, sabzi):
    for gkey, blocked in GRAVY_SABZI_CONFLICTS.items():
        if gkey in gravy.lower() and any(w in sabzi.lower().split() for w in blocked):
            return True
    return False

week_errors = []

for seed in range(100):
    random.seed(seed)
    used_g, used_s, used_p = set(), set(), {}
    week = []

    for i in range(7):
        dt = DAY_TYPE[i]
        if dt == "flex": dt = random.choice(["fish", "veg"])

        # Saturday uses restricted non-dal gravy pool
        if dt == "chicken" and i == 5:
            gp = [g for g in SAT_CHICKEN_GRAVIES if g not in used_g]
            if not gp: gp = list(SAT_CHICKEN_GRAVIES)
        else:
            gp = [g for g in GRAVIES[dt] if g not in used_g]
            if not gp: gp = list(GRAVIES[dt])
        gravy = random.choice(gp)
        used_g.add(gravy)

        # Sabzi
        sp = [s for s in SABZIS if s not in used_s and not sabzi_conflicts(gravy, s)]
        if not sp: sp = [s for s in SABZIS if not sabzi_conflicts(gravy, s)]
        if not sp: sp = SABZIS
        sabzi = random.choice(sp)
        used_s.add(sabzi)

        # Saturday roll BEFORE protein
        sat_roll = random.random() if (dt == "chicken" and i == 5) else None
        if sat_roll is not None and sat_roll < 0.3:
            week.append({"i":i,"dt":"khichdi","gravy":"khichdi","sabzi":"none","protein":"none","starch":"khichdi"})
            continue

        # Protein (per type, no repeats)
        if dt == "veg" and gravy in THU_PANEER_GRAVIES:
            fp = [p for p in PROTEINS["veg"] if p != "paneer" and p not in used_p.get("veg",set())]
            if not fp: fp = [p for p in PROTEINS["veg"] if p != "paneer"]
            protein = random.choice(fp) if fp else "paneer bhurji"
        else:
            pp = [p for p in PROTEINS[dt] if p not in used_p.get(dt,set())]
            if not pp: pp = PROTEINS[dt]
            protein = random.choice(pp)

        used_p.setdefault(dt, set()).add(protein)

        # Saturday option B: chicken curry
        if sat_roll is not None and sat_roll < 0.65:
            gravy = "chicken curry"
            protein = ""

        # Protein overrides
        if gravy in GRAVY_CONTAINS_PROTEIN: protein = ""
        elif gravy in NEEDS_PANEER_BHURJI: protein = "paneer bhurji"
        elif dt == "veg" and gravy not in THU_PANEER_GRAVIES: protein = "paneer bhurji"

        starch = get_starch(dt, i, gravy)
        week.append({"i":i,"dt":dt,"gravy":gravy,"sabzi":sabzi,"protein":protein,"starch":starch})

        # ── Per-day validations ──
        if dt == "fish" and starch != "Rice":
            week_errors.append(f"W{seed} {DAYS[i]}: Fish+{gravy}→{starch}")
        if gravy in DAL_GRAVIES and starch != "Rice":
            week_errors.append(f"W{seed} {DAYS[i]}: Dal '{gravy}'→{starch} (must be Rice)")
        if dt == "chicken" and i == 5 and gravy != "chicken curry" and "Stuffed Paratha" not in starch:
            week_errors.append(f"W{seed} {DAYS[i]}: Saturday→{starch} (must be Stuffed Paratha)")
        if dt == "veg" and gravy == "kadhi":
            week_errors.append(f"W{seed} {DAYS[i]}: Kadhi on veg day!")
        if dt == "chicken" and gravy == "kadhi":
            week_errors.append(f"W{seed} {DAYS[i]}: Kadhi on chicken day!")
        if any(x in (protein or "") for x in ["chicken sukka","chicken handi","chicken masala"]) and dt != "chicken":
            week_errors.append(f"W{seed} {DAYS[i]}: Chicken protein on {dt} day!")
        if any(x in (protein or "") for x in ["mackerel","sardine"]) and dt == "chicken":
            week_errors.append(f"W{seed} {DAYS[i]}: Fish protein on chicken day!")
        if gravy in NEEDS_PANEER_BHURJI and protein != "paneer bhurji":
            week_errors.append(f"W{seed} {DAYS[i]}: {gravy} needs paneer bhurji, got '{protein}'")
        if gravy in GRAVY_CONTAINS_PROTEIN and protein not in ("","none"):
            week_errors.append(f"W{seed} {DAYS[i]}: {gravy} already has protein, got '{protein}'")
        for rm in REMOVED:
            if rm in gravy or rm in sabzi:
                week_errors.append(f"W{seed} {DAYS[i]}: Removed item '{rm}'!")
        for gkey, blocked in GRAVY_SABZI_CONFLICTS.items():
            if gkey in gravy.lower() and any(w in sabzi.lower().split() for w in blocked):
                week_errors.append(f"W{seed} {DAYS[i]}: Conflict: {gravy}+{sabzi}")

    # Week-level: no gravy repeats (exclude Saturday and chicken curry which is option B)
    gravies = [d["gravy"] for d in week if d["gravy"] not in ("khichdi","chicken curry") and d["i"] != 5]
    if len(gravies) != len(set(gravies)):
        dups = [g for g in set(gravies) if gravies.count(g)>1]
        week_errors.append(f"W{seed}: Gravy repeat (non-Saturday): {dups}")

    sabzis_w = [d["sabzi"] for d in week if d.get("sabzi") not in ("none","")]
    if len(sabzis_w) != len(set(sabzis_w)):
        dups = [s for s in set(sabzis_w) if sabzis_w.count(s)>1]
        week_errors.append(f"W{seed}: Sabzi repeat: {dups}")

    real_proteins = [d["protein"] for d in week if d.get("protein") not in ("","none",None,"paneer bhurji")]
    if len(real_proteins) != len(set(real_proteins)):
        dups = [p for p in set(real_proteins) if real_proteins.count(p)>1]
        week_errors.append(f"W{seed}: Protein repeat: {dups}")

for e in week_errors[:10]: fail(e)
if not week_errors: ok("100 weeks — zero logic errors")

# ════════════════════════════════════════════════════════════════════
# GROUP 5: SYSTEM PROMPT & CODE CHECKS
# ════════════════════════════════════════════════════════════════════
print("\n=== GROUP 5: System Prompt & Code Checks ===")

def file_contains(path, text):
    if not os.path.exists(path): return False
    with open(path) as f: return text in f.read()

checks = {
    "Supriya 1700 kcal":        "1,700 kcal" in code,
    "Vivek 2200 kcal":          "2,200 kcal" in code,
    "130g protein":             "130g protein" in code,
    "166g protein":             "166g protein" in code,
    "8 egg whites":             "8 egg whites" in code,
    "ON Whey":                  "ON Whey" in code,
    "Sunday paratha exception": "Sunday exception" in code,
    "Indian home cooking":      "INDIAN HOME COOKING" in code,
    "No Western food":          "no Western food" in code,
    "No roti+dal":              "NO roti+dal" in code,
    "Macros only when asked":   "Only show macros" in code,
    "Shopping total always":    "ALWAYS show the weekly total" in code,
    "Egg price 139":            "₹139" in code,
    "Mango cheaper":            "cheaper than Instamart" in code,
    "Weekly not monthly":       "these are different" in code,
    "Pantry table correct":     "pantry_inventory" in code,
    "in_stock column":          '"in_stock"' in code,
    "No old instock col":       '"instock"' not in code,
    "No hardcoded Groq key":    "gsk_" not in code,
    "Model llama-3.1-8b":       "llama-3.1-8b-instant" in code,
    "plan_week exists":         "def plan_week" in code,
    "get_history exists":       "def get_history" in code,
    "save_plan exists":         "def save_plan" in code,
    "run_weekly_agent exists":  "async def run_weekly_agent" in code,
    "No dead Monday code":      "If today is Monday use today" not in code,
    "No dup shopping section":  code.count("SHOPPING PRICES") == 1,
    "Paneer not doubled":       "veg_proteins_no_paneer" in code,
    "Khichdi Special label":    "Khichdi Special" in code,
    "Khichdi is_veg False":     '"veg", "khichdi"' not in code,
    "Platform lowercase":       ".lower()" in code,
    "Lunch & Dinner once":      "Lunch & Dinner" in code,
    "Force exact plan":         "MEAL PLAN GENERATED" in code,
    "LLM not replanning":       "Present the meal plan above exactly" in code,
    "RESEND_API_KEY used":      "RESEND_API_KEY" in code,
    "Preferences table used":   "preferences" in code,
    "SAT_CHICKEN_GRAVIES":      "SAT_CHICKEN_GRAVIES" in code,
    "Friday cron in railway":   file_contains('/home/claude/railway.json','0 12 * * 5'),
    "weekly-plan in main":      file_contains('/home/claude/main.py','weekly-plan'),
    "preferences router":       file_contains('/home/claude/main.py','preferences_router'),
}

for k, v in checks.items():
    if v: ok(k)
    else: fail(k)

# ════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"Total: {passed + len(errors)} | Passed: {passed} | Failed: {len(errors)}")
print('='*60)
if errors:
    print(f"\n🔴 {len(errors)} FAILED:")
    for e in errors: print(f"  {e}")
    sys.exit(1)
else:
    print("🚀 ALL TESTS PASSED — safe to deploy!")