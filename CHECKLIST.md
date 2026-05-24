# Sous Chef — Master Checklist (Run Before Every Deploy)

## HOW TO RUN
```bash
python3 checklist.py
```
Must show 50/50 before any push.

---

## THE 50 RULES

### GROUP 1: Nutrition Targets (4)
1. Supriya: 1,700 kcal/day
2. Supriya: 130g protein/day
3. Vivek: 2,200 kcal/day
4. Vivek: 166g protein/day

### GROUP 2: Breakfast (3)
5. Fixed every day: 8 egg whites bhurji + ON Whey smoothie (yogurt + banana + blueberries + dragon fruit)
6. No bread — smoothie replaces it
7. Sunday exception: paratha + egg bhurji instead

### GROUP 3: Weekly Rotation (4)
8. Mon = Chicken
9. Tue = Fish dry fry
10. Wed = Chicken (different combo from Mon)
11. Thu = Veg only (zero meat/fish/eggs)
12. Fri = Fish dry fry (different sabzi from Tue)
13. Sat = Chicken or Khichdi special
14. Sun = Flexible (fish/chicken/paneer)

### GROUP 4: Meal Structure (3)
15. Every meal = gravy + dry sabzi + protein
16. Lunch and dinner = same dish cooked once
17. Show as "Lunch & Dinner" not separately

### GROUP 5: Starch Rules (6)
18. Chicken days → 3 plain parathas (Supriya) / 4 rotis (Vivek)
19. Fish days → Rice always (both meals)
20. Dal/Kadhi/Rajma/Santula/Sambar → Rice
21. Chole/Matar paneer/Palak paneer/Aloo gobi gravy → Paratha
22. NO roti+dal combo ever
23. Saturday stuffed paratha (aloo/paneer cauliflower/methi/palak)

### GROUP 6: Saturday Options (3)
24. Option A (30%): Khichdi + Chokha + Fish fry — no sabzi
25. Option B (35%): Chicken curry + stuffed paratha + sabzi
26. Option C (35%): Regular chicken + stuffed paratha + sabzi

### GROUP 7: Strict Rules (5)
27. Kadhi ONLY with fish — never chicken
28. Rajma/black chana = no meat same day
29. Torai = always dry sabzi, never a gravy
30. NEVER repeat same gravy in same week
31. NEVER repeat same sabzi in same week

### GROUP 8: Approved Gravies (by day type)
32. Fish gravies: kadhi | palak dal | sambar | moong dal | lauki dal | santula
33. Chicken gravies: dal tadka | palak dal | aloo gobi gravy | moong dal | lauki dal | chole
34. Veg gravies: matar paneer | rajma soyabean | chole | palak paneer | chana masala | kadhi | santula | moong dal | rajma | black chana

### GROUP 9: Removed Items (3)
35. Dal makhani — REMOVED
36. Arhar dal — REMOVED
37. Kaddu — REMOVED

### GROUP 10: Portions (4)
38. Supriya: chicken 150g | fish 150g | paneer 80g | rice 60g dry | 3 parathas | dal 30g | veg 100g
39. Vivek: chicken 200g | fish 200g | paneer 120g | rice 100g dry | 4 rotis | dal 40g | veg 120g

### GROUP 11: Thursday Special (2)
40. Veg day only — no meat/fish/eggs
41. If no paneer gravy → add paneer bhurji as dry side

### GROUP 12: No Repeat Logic (3)
42. Python plan_week() function generates meals (not LLM)
43. get_history() fetches last 14 days before planning
44. Used gravies and sabzis tracked in sets — no week repeats

### GROUP 13: Shopping List (3)
45. Always show weekly total (~₹6,400) at end
46. Weekly ≠ monthly (₹38,000 is monthly)
47. Grouped by platform: Licious | Instamart | Mango

### GROUP 14: Response Behaviour (3)
48. Macros shown ONLY when asked
49. Quantities shown ONLY when asked
50. Log expense ONLY when user explicitly says they spent money

### GROUP 15: Technical (6) — bonus checks
51. No hardcoded API keys in code
52. Platform names lowercased (.lower())
53. Model: llama-3.1-8b-instant
54. max_tokens set to control token usage
55. Only last 4 messages sent (save tokens)
56. Syntax check passes (ast.parse)

---

## APPROVED SABZIS (17)
Torai | Bhindi fry | Beans carrot | Cauliflower matar aloo | Cabbage |
Baingan bharta | Beetroot | Lauki | Parwal | Mix veg (cauliflower+broccoli+matar+carrot+beans) |
Aloo shimla mirch | Methi | Aloo jeera | Sem sabzi | Tinda | Gawar | Aloo gobi dry

## APPROVED PROTEINS
- Chicken: sukka | curry | handi | masala
- Fish: mackerel dry fry | sardine dry fry | mackerel rava fry
- Veg: paneer bhurji | matar paneer (in gravy) | soyabean curry | chana

## SHOPPING PRICES
| Item | Qty | Price/week |
|------|-----|------------|
| Eggs | 6 dozen | ₹792 |
| Chicken breast | 3×450g | ₹885 |
| Chicken curry cut | 3×500g | ₹780 |
| Mackerel | 3×500g | ₹1,050 |
| Paneer | 2×200g | ₹272 |
| A2 Milk | 14×500ml | ₹742 |
| Epigamia Yogurt | 2 | ₹498 |
| Vegetables | — | ~₹350 |
| Fruits | — | ~₹500 |
| Dal | — | ₹130 |
| Rice 5kg | 1 | ₹320 |
| Atta 1kg | 1 | ₹60 |
| **TOTAL** | | **~₹6,400** |
