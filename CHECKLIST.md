# Sous Chef — Master Checklist (Run Before Every Deploy)
# Must show 67/67 before any push.

---

## GROUP 1: Nutrition Targets (4)
1. Supriya: 1,700 kcal/day
2. Supriya: 130g protein/day
3. Vivek: 2,200 kcal/day
4. Vivek: 166g protein/day

## GROUP 2: Breakfast (3)
5. Fixed every day: 8 egg whites bhurji + ON Whey smoothie (yogurt + banana + blueberries + dragon fruit)
6. No bread — smoothie replaces it
7. Sunday exception: paratha + egg bhurji instead

## GROUP 3: Weekly Rotation (7)
8. Mon = Chicken
9. Tue = Fish dry fry
10. Wed = Chicken (different combo from Mon)
11. Thu = Veg only (zero meat/fish/eggs)
12. Fri = Fish dry fry (different sabzi from Tue)
13. Sat = Chicken or Khichdi special
14. Sun = Flexible (fish/chicken/paneer)

## GROUP 4: Meal Structure (3)
15. Every meal = gravy + dry sabzi + protein
16. Lunch and dinner = same dish cooked once
17. Show as "Lunch & Dinner" not separately
18. LLM presents EXACTLY what Python generates — no changes

## GROUP 5: Starch Rules (6)
19. Chicken days → 3 plain parathas (Supriya) / 4 rotis (Vivek)
20. Fish days → Rice always (both meals)
21. Veg + dal/kadhi/rajma/santula/sambar → Rice
22. Veg + chole/matar paneer/palak paneer/aloo gobi → Paratha
23. NO roti+dal combo ever
24. Saturday stuffed paratha (aloo/paneer cauliflower/methi/palak)

## GROUP 6: Saturday Options (5)
25. Option A (30%): Khichdi + Chokha + Fish fry — no sabzi, uses continue
26. Option B (35%): gravy="chicken curry" + stuffed paratha + sabzi
27. Option C (35%): Regular chicken + stuffed paratha + sabzi
28. Saturday khichdi uses `continue` to skip rest of loop
29. Saturday no protein duplication (gravy and protein are different)

## GROUP 7: Strict Rules (5)
30. Kadhi ONLY with fish — never chicken
31. Rajma/black chana = no meat same day (NOT in chicken gravies)
32. Torai = always dry sabzi, never a gravy
33. NEVER repeat same gravy in same week (tracked in set)
34. NEVER repeat same sabzi in same week (tracked in set)

## GROUP 8: Approved Gravies (3)
35. Fish gravies: kadhi | palak dal | sambar | moong dal | lauki dal | santula
36. Chicken gravies: dal tadka | palak dal | aloo gobi gravy | moong dal | lauki dal | chole
37. Veg gravies: matar paneer | rajma soyabean | chole | palak paneer | chana masala | kadhi | santula | moong dal | rajma | black chana

## GROUP 9: Removed Items (3)
38. Dal makhani — REMOVED
39. Arhar dal — REMOVED
40. Kaddu — REMOVED

## GROUP 10: Portions (4)
41. Supriya: chicken 150g | fish 150g | paneer 80g | rice 60g dry | 3 parathas | dal 30g | veg 100g
42. Vivek: chicken 200g | fish 200g | paneer 120g | rice 100g dry | 4 rotis | dal 40g | veg 120g

## GROUP 11: Thursday Special (2)
43. Veg day only — no meat/fish/eggs
44. If no paneer gravy → add paneer bhurji as dry side

## GROUP 12: No Repeat Logic (4)
45. Python plan_week() generates meals — not LLM
46. get_history() fetches last 14 days before planning
47. History used inside plan_week to avoid repeats
48. save_plan() saves to Supabase after generating

## GROUP 13: Pantry Inventory (7) — NEW
49. get_pantry tool defined
50. update_pantry tool defined
51. Correct table name: pantry_inventory
52. Correct column name: in_stock (with underscore)
53. Old wrong column name instock (no underscore) NOT present
54. Shopping list always calls get_pantry first
55. update_pantry called immediately when user mentions inventory

## GROUP 14: Shopping List (6)
56. Always show weekly total at end
57. Weekly total ~₹6,500
58. Weekly ≠ monthly (₹38,000 is monthly — clearly different)
59. Buy vegetables from Mango — cheaper than Instamart
60. Licious egg price ₹139/dozen (updated from receipt)
61. Real Mango prices: beetroot/carrot ₹99/kg, lauki ₹59/kg etc

## GROUP 15: Response Behaviour (3)
62. Macros shown ONLY when asked
63. Quantities shown ONLY when asked
64. Log expense ONLY when user explicitly says they spent money

## GROUP 16: Technical (4)
65. No hardcoded API keys (no gsk_, no sk-or-)
66. Platform names lowercased (.lower())
67. Model: llama-3.1-8b-instant (1M tokens/day)
68. max_tokens set to control token usage
69. Only last 4 messages sent (save tokens)
70. Syntax check passes (ast.parse)

---

## APPROVED SABZIS (17)
Torai | Bhindi fry | Beans carrot | Cauliflower matar aloo | Cabbage |
Baingan bharta | Beetroot | Lauki | Parwal | Mix veg (cauliflower+broccoli+matar+carrot+beans) |
Aloo shimla mirch | Methi | Aloo jeera | Sem sabzi | Tinda | Gawar | Aloo gobi dry

## APPROVED PROTEINS
- Chicken: sukka | curry | handi | masala
- Fish: mackerel dry fry | sardine dry fry | mackerel rava fry
- Veg: paneer bhurji | matar paneer (in gravy) | soyabean curry | chana

## SHOPPING PRICES (Real — from Mango receipt)
| Item | Qty | Price/week |
|------|-----|------------|
| Eggs | 6 dozen | ₹834 |
| Chicken breast | 3×450g | ₹885 |
| Chicken curry cut | 3×500g | ₹780 |
| Mackerel | 3×500g | ₹1,050 |
| Paneer | 2×200g | ₹272 |
| A2 Milk | 14×500ml | ₹742 |
| Epigamia Yogurt | 2 | ₹498 |
| Beetroot | per kg | ₹99 |
| Carrot | per kg | ₹99 |
| Lauki | per kg | ₹59 |
| Torai | per kg | ₹129 |
| French beans | per kg | ₹159 |
| Potato | per kg | ₹29 |
| Rajma | per kg | ₹184 |
| Moong | per kg | ₹163 |
| Rice | 5kg | ₹320 |
| Atta | 1kg | ₹60 |
| Fruits | — | ~₹300 |
| **WEEKLY TOTAL** | | **~₹6,500** |
| **MONTHLY BUDGET** | | **₹38,000** |