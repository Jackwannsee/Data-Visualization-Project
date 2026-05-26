# Bug Analysis: Incorrect Round Outcomes in Economy Visualization

## Summary

I found **one critical bug** in [parse_team_outcomes.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py) that causes round outcomes to be **inverted after half-time (round 13+)**. The `parse_economy.py` cash extraction logic appears correct. The visualization in `economy_viz.py` faithfully renders the bad data, so the fix is in the data processing layer.

---

## 🐛 The Critical Bug: Stale `side_to_team` mapping after half-time

**File:** [parse_team_outcomes.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py)  
**Location:** Lines 334–389

### What's happening

The code builds a **single, static** `side_to_team` dictionary at [line 335-337](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py#L335-L337):

```python
side_to_team = {}
for t, side in team_sides.items():
    side_to_team[side] = t
```

This maps `{"CT": "Team A", "T": "Team B"}` based on each team's **starting** side (rounds 1–12).

Then on [line 383](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py#L383), this same mapping is used for **every round**:

```python
winning_team = side_to_team.get(winner_side, "")
row[f"r_{r}_outcome"] = (winning_team == team)
```

**The problem:** In CS2, teams **swap sides at round 13**. If Team A started CT (rounds 1–12), they become T (rounds 13+). But the code never updates `side_to_team`, so after halftime, when the demo says "CT won round 14", it maps that to Team A — **but Team A is now T side**. The correct winner is Team B.

### The effect

> **Every round outcome from round 13 onward is flipped** (wins shown as losses, losses shown as wins).

This matches what you observed watching the games back.

### Proof from the CSV

Look at line 2 of [budapest_major_team_outcomes.csv](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/analysis_results/budapest_major_team_outcomes.csv):

```
Final,Dust2,FaZe Clan,Team Vitality,1-12,13-16
r1-r12:  F,F,F,F,F,F,F,T,F,F,T,T   (CT side: 5 wins out of 12 → lost CT side badly)
r13-r16: T,T,T,T                      (T side: won all 4 rounds?)
```

The final score is 13-3 (Vitality won 13, FaZe won 3). FaZe only won 3 rounds total. But the outcomes CSV shows FaZe winning **5 + 4 = 9 rounds** — that's impossible. The second half outcomes are inverted.

Corrected, FaZe's second half should be `F,F,F,F` (0 wins), giving them 5 total — still not matching 3 from the score. This suggests the CT-side half may also have issues (see secondary issue below).

---

## ⚠️ Secondary Concern: Starting side detection might also be wrong

**File:** [parse_team_outcomes.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py) — [load_match_details()](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py#L84-L125)

The `load_match_details()` function determines starting side from which `side` row has non-null `rounds_played`. Looking at the match_details CSV:

```csv
Final,Dust2,FaZe Clan,Team Vitality,Counter Terrorist,16.0,7.0,...
Final,Dust2,FaZe Clan,Team Vitality,Terrorist,,,                  # rounds_played is NaN
```

The logic at [line 108-114](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py#L108-L114) says: if `rounds_played` is not NaN and > 0 for "Counter Terrorist", set starting_side to "CT". For FaZe on Dust2, CT has `rounds_played=16.0`, so starting_side = "CT".

But the match_details CSV itself seems to only populate `rounds_played` on the **CT** row — and the `rounds_won=7` for FaZe seems off for a team that only scored 3 rounds in a 13-3 loss. This suggests the match_details parsing may have its own issues, which could cascade into wrong side assignments.

The `get_team_sides()` fallback at [line 183-242](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py#L183-L242) looks at the **most common side** across all ticks — but since ticks span both halves, this will be a rough 50/50 split and is unreliable.

---

## ✅ Fix for the critical bug

In [parse_team_outcomes.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py), the outcome assignment loop ([lines 377–389](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py#L377-L389)) needs to **flip the `side_to_team` mapping after round 12**:

```diff
 # Add round outcome columns
 for r in range(1, MAX_ROUNDS + 1):
     if r <= total_rounds:
         round_winner = winners_df[winners_df["round_num"] == r]
         if not round_winner.empty:
             winner_side = round_winner["winner_side"].iloc[0]
-            # Map winner_side to team name and check if it's our team
-            winning_team = side_to_team.get(winner_side, "")
+            # After round 12, teams swap sides
+            if r <= 12:
+                current_side_to_team = side_to_team
+            else:
+                # Flip the mapping: CT↔T
+                current_side_to_team = {v_side: v_team 
+                    for v_team, v_side in side_to_team.items()
+                    for v_side, v_team in [("CT" if s == "T" else "T", t) 
+                    for t, s in team_sides.items()]}
+            winning_team = current_side_to_team.get(winner_side, "")

             row[f"r_{r}_outcome"] = (winning_team == team)
```

A cleaner approach:

```python
# Build per-half side mappings
first_half_side_to_team = {side: t for t, side in team_sides.items()}
# After halftime, sides swap
second_half_side_to_team = {
    ("T" if side == "CT" else "CT"): t 
    for t, side in team_sides.items()
}

# Then in the loop:
mapping = first_half_side_to_team if r <= 12 else second_half_side_to_team
winning_team = mapping.get(winner_side, "")
```

---

## 📋 Files reviewed

| File | Status | Issue? |
|------|--------|--------|
| [parse_economy.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_economy.py) | ✅ OK | Cash extraction uses tick closest to round start — correct |
| [parse_outcomes.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_outcomes.py) | ⚠️ Same bug pattern | Uses `winner_name` from awpy, may or may not have the same issue depending on what awpy returns |
| [parse_team_outcomes.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/data_processing/parse_team_outcomes.py) | 🐛 **BUG** | `side_to_team` not flipped after halftime — outcomes inverted for rounds 13+ |
| [economy_viz.py](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/src/visualization/economy_viz.py) | ✅ OK | Correctly renders data from CSV; bug is upstream |
| [match_details.csv](file:///wsl.localhost/Ubuntu/home/jack/02.SS26/Data-Visualization-Project/analysis_results/budapest_major_match_details.csv) | ⚠️ Suspect | `rounds_won` values may be incorrect (7 for FaZe in a 13-3 loss?) |

> [!IMPORTANT]
> The match_details `rounds_won` should also be validated. If FaZe lost 13-3 on Dust2 Final, they won 3 rounds total, but match_details says `rounds_won=7.0` on CT side. This could indicate another parsing bug in `parse_match_details.py` — or the final_score column may not reflect the same team's perspective.
