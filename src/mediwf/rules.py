"""The single place where the flaw composites are defined (added 17 Sep 2026 after the second audit, which found four
different "any flaw" definitions across scripts). Every analysis script imports from here.

CORE       - the 14 Tier-A flaws counted in the primary outcome "any structural flaw" (Table 1 of the manuscript).
             Three detector outputs are computed but are NOT flaws: option_length_outlier (a broader length feature),
             options_not_alphabetical (an ordering convention) and numeric_units_inconsistent (a formatting convention);
             they are reported separately as FEATURES.
VALIDATED  - the CORE rules that were tested against BenchMarker's human labels (scripts/validate_benchmarker.py).
             The other four CORE rules (longest_option_key, nonparallel_options, overlapping_options, true_false_stem)
             have no external validation and rest on the author's hand-verification.
SENSITIVITY- CORE minus the three rules whose agreement with human labels was poor (absolute_terms, vague_terms,
             grammatical_cue); the "11-rule composite" of the manuscript.
CUEING     - the flaws that give away the answer (used in the NBME examinee-statistics analysis).
"""
CORE = ["negative_stem", "none_of_the_above", "all_of_the_above", "combination_options", "fill_in_blank", "true_false_stem",
        "longest_option_key", "absolute_terms", "vague_terms", "clang_cue", "grammatical_cue", "nonparallel_options",
        "numeric_not_ordered", "overlapping_options"]
FEATURES = ["option_length_outlier", "numeric_units_inconsistent", "options_not_alphabetical"]
VALIDATED = ["negative_stem", "none_of_the_above", "all_of_the_above", "combination_options", "fill_in_blank",
             "absolute_terms", "vague_terms", "clang_cue", "grammatical_cue", "numeric_not_ordered"]
UNVALIDATED = [r for r in CORE if r not in VALIDATED]
POOR_AGREEMENT = ["absolute_terms", "vague_terms", "grammatical_cue"]
SENSITIVITY = [r for r in CORE if r not in POOR_AGREEMENT]
CUEING = ["longest_option_key", "absolute_terms", "clang_cue", "grammatical_cue"]
assert len(CORE) == 14 and len(VALIDATED) == 10 and len(SENSITIVITY) == 11 and len(UNVALIDATED) == 4


def any_flaw(df, rules=CORE):
    """0/1 Series: at least one of `rules` fired (works on any flags_*.csv DataFrame)."""
    return (df[list(rules)].sum(axis=1) > 0).astype(int)


def n_flaws(df, rules=CORE):
    return df[list(rules)].sum(axis=1).astype(int)
