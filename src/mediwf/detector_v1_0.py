"""MedIWF Tier-A item-writing-flaw detector (rule-based, no medical knowledge required).

Input item format (dict):
    {"stem": str, "options": {"A": str, "B": str, ...}, "answer": "C"}
Output: dict with one boolean per flaw plus an "evidence" dict and a "features" dict.

Flaw definitions follow the NBME Item-Writing Guide (6th ed.) and Haladyna, Downing & Rodriguez (2002),
operationalized so that every decision is reproducible from the text alone. Where a published tool
(SAQUET, BenchMarker) fixed a threshold, we adopt it and say so in the comment.
Compatible with Python 3.9.
"""
import re
import statistics
from typing import Dict, List, Optional

# ----------------------------------------------------------------------------- lexicons
ABSOLUTE_TERMS = {"always", "never", "all", "none", "only", "every", "completely", "absolutely",
                  "totally", "definitely", "impossible", "invariably", "entirely", "exclusively"}
# Phrases in which an absolute word is idiomatic, not a universal claim (BenchMarker example list, extended)
ABSOLUTE_EXEMPT = [r"every (other )?(day|week|month|year|hour|\d+ (hours|days|weeks))", r"all of the above",
                   r"none of the above", r"all-cause", r"all-trans", r"once daily", r"only child", r"every \d+",
                   r"\bonly (a |an |one |two |three |four |five |few |\d+)", r"\ball (but|of the|of these|three|four|five|\d+)\b",
                   r"\bnone of (the|these)\b", r"\bat all\b", r"\ball\b(?=.*\bof\b)"]
VAGUE_TERMS = {"usually", "often", "frequently", "sometimes", "rarely", "seldom", "occasionally",
               "generally", "regularly", "infrequently", "commonly"}
# Negation that governs the question (NBME: negatively phrased lead-in). Quoted or incidental "not" inside a
# vignette sentence does not count; the negative must sit in the interrogative clause or be capitalised for emphasis.
NEGATIVE_LEADIN = re.compile(
    r"(\b(which|what|who|where|all|each)\b[^.?!]*\b(not|except|least|false|incorrect|never)\b)"   # 'which ... is NOT'
    r"|(\b(is|are|was|were|does|do|did|would|should|could|can|will|has|have)\s+not\b[^.?!]*\?)"     # 'does not ...?'
    r"|(\bexcept\b\s*[:?]?\s*$)"                                                                   # trailing 'EXCEPT'
    r"|(\b(NOT|EXCEPT|LEAST|FALSE|INCORRECT)\b)"                                                     # emphasised negative
)
# Words that carry no content for the clang-cue test
STOPWORDS = set("""a an the and or of to in on at for with by from as is are was were be been being this that these those
it its he she his her they them their which what who whom whose where when why how most likely following best next
step management appropriate diagnosis initial patient patients year years old man woman boy girl male female presents
presenting present comes brought because history physical examination shows show findings finding laboratory studies
study test results result likely cause causes causing mechanism treatment therapy would should could also than then
after before during over under between into within without about above below more less than other another some any
each such same only very also"""
    .split())

META_OPTION_ALL = re.compile(r"\ball of (the )?(above|these|them)\b|\ball (options|choices) (are|apply)\b", re.I)
META_OPTION_NONE = re.compile(r"\bnone of (the )?(above|these|them)\b|\bneither of (the )?(above|these)\b", re.I)
COMBO_OPTION = re.compile(r"^\s*(both\s+)?[A-J](\s*,\s*[A-J])*\s*(,?\s*(and|or|&)\s*[A-J])\s*(only)?\s*$", re.I)
ROMAN_COMBO = re.compile(r"^\s*(I|II|III|IV|V)(\s*,\s*(I|II|III|IV|V))*\s*(,?\s*(and|or|&)\s*(I|II|III|IV|V))?\s*(only)?\s*$")
NUMBER = re.compile(r"[-+]?\d[\d,]*\.?\d*")
BLANK = re.compile(r"_{2,}|\[blank\]|\(blank\)", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _tokens(s: str) -> List[str]:
    return re.findall(r"[a-z][a-z\-']+", (s or "").lower())


def _content_words(s: str) -> set:
    out = set()
    for w in _tokens(s):
        w = w.strip("-'")
        if len(w) < 4 or w in STOPWORDS:
            continue
        # crude lemmatization: strip plural/verb endings so 'infections' ~ 'infection'
        for suf in ("ies", "es", "s", "ing", "ed"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)] + ("y" if suf == "ies" else "")
                break
        out.add(w)
    return out


def _lead_in(stem: str) -> str:
    """The sentence that poses the question: the last sentence ending in '?' or ':' or, failing that, the last sentence."""
    s = _norm(stem)
    sents = re.split(r"(?<=[.?!:])\s+", s)
    for sent in reversed(sents):
        if sent.endswith("?") or sent.endswith(":"):
            return sent
    return sents[-1] if sents else s


def _first_word(s: str) -> str:
    m = re.match(r"\s*([A-Za-z][A-Za-z\-']*)", s or "")
    return m.group(1) if m else ""


def _is_numeric_option(s: str) -> bool:
    s = _norm(s)
    return bool(NUMBER.match(s)) and len(NUMBER.findall(s)) >= 1 and len(re.sub(r"[\d\s.,%/:+\-–]", "", s)) <= 12


def _num_value(s: str) -> Optional[float]:
    m = NUMBER.search(_norm(s))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _unit(s: str) -> str:
    s = _norm(s)
    m = NUMBER.search(s)
    if not m:
        return ""
    return re.sub(r"[\d\s.,]", "", s[m.end():]).lower()


# ----------------------------------------------------------------------------- detector
class Detector:
    """Rule-based Tier-A flaw detector. All thresholds are class attributes so they are visible and reportable."""

    # Key is flagged as "longest" when it is longer than every distractor by this factor (SAQUET uses 1/0.75 = 1.33 on chars).
    LONGEST_RATIO = 1.25
    LONGEST_MIN_WORDS = 4
    # An option is a length outlier when its length is outside median +/- this fraction and it is the unique outlier.
    OUTLIER_RATIO = 1.75
    NONPARALLEL_CV = 0.60

    FLAWS = [
        "negative_stem", "none_of_the_above", "all_of_the_above", "combination_options", "fill_in_blank",
        "true_false_stem", "longest_option_key", "option_length_outlier", "absolute_terms", "vague_terms",
        "clang_cue", "grammatical_cue", "nonparallel_options", "numeric_not_ordered", "numeric_units_inconsistent",
        "overlapping_options", "options_not_alphabetical",
    ]

    def detect(self, item: Dict) -> Dict:
        stem = _norm(item.get("stem", ""))
        opts_in = item.get("options") or {}
        if isinstance(opts_in, list):
            opts_in = {chr(65 + i): o for i, o in enumerate(opts_in)}
        opts = {str(k).strip().upper()[:1]: _norm(str(v)) for k, v in opts_in.items()}
        key = str(item.get("answer", "")).strip().upper()[:1]
        letters = sorted(opts)
        distractors = [opts[l] for l in letters if l != key]
        key_text = opts.get(key, "")
        lead = _lead_in(stem)
        ev: Dict[str, object] = {}
        f: Dict[str, bool] = {}

        # --- stem flaws
        neg = [m.group(0)[:60] for m in NEGATIVE_LEADIN.finditer(lead)]
        f["negative_stem"] = bool(neg)
        ev["negative_words"] = neg
        f["fill_in_blank"] = bool(BLANK.search(stem))
        f["true_false_stem"] = bool(re.search(r"\bwhich (of the following )?(statement|statements)?\s*(is|are)\s*(true|correct|false|incorrect|accurate)\b", lead, re.I)) \
            or all(o.lower() in {"true", "false", "yes", "no"} for o in opts.values()) if opts else False

        # --- meta options
        f["all_of_the_above"] = any(META_OPTION_ALL.search(o) for o in opts.values())
        f["none_of_the_above"] = any(META_OPTION_NONE.search(o) for o in opts.values())
        f["combination_options"] = any(COMBO_OPTION.match(o) or ROMAN_COMBO.match(o) for o in opts.values()) \
            or (sum(bool(re.search(r"\b(and|&)\b", o)) for o in opts.values()) >= 2 and self._shared_components(opts))

        # --- length cues
        lens = {l: len(opts[l]) for l in letters}
        ev["option_chars"] = lens
        if key in opts and distractors:
            longest_d = max(len(d) for d in distractors)
            f["longest_option_key"] = (len(key_text) > self.LONGEST_RATIO * longest_d) and (len(key_text.split()) >= self.LONGEST_MIN_WORDS)
            ev["key_to_longest_distractor_ratio"] = round(len(key_text) / longest_d, 2) if longest_d else None
        else:
            f["longest_option_key"] = False
        f["option_length_outlier"] = self._length_outlier([opts[l] for l in letters])

        # --- lexical cues in options
        abs_hits = self._absolute_hits(opts)
        f["absolute_terms"] = bool(abs_hits)
        ev["absolute_hits"] = abs_hits
        vague_hits = {l: sorted(set(_tokens(o)) & VAGUE_TERMS) for l, o in opts.items()}
        vague_hits = {l: v for l, v in vague_hits.items() if v}
        f["vague_terms"] = bool(vague_hits)
        ev["vague_hits"] = vague_hits

        # --- clang / word repetition: content words shared by stem and key but absent from every distractor
        if key in opts:
            stem_w = _content_words(stem)
            key_w = _content_words(key_text)
            d_w = set().union(*[_content_words(d) for d in distractors]) if distractors else set()
            clang = sorted((stem_w & key_w) - d_w)
            # BenchMarker operationalization: the key must have substantially higher overlap with the stem than every
            # distractor. We require an exclusive shared word AND key overlap >= 2x the best distractor overlap
            # (or >= 2 exclusive words).
            ov_key = len(stem_w & key_w) / max(len(key_w), 1)
            ov_d = max((len(stem_w & _content_words(d)) / max(len(_content_words(d)), 1)) for d in distractors) if distractors else 0.0
            f["clang_cue"] = bool(clang) and (len(clang) >= 2 or ov_key >= 2 * ov_d)
            ev["clang_words"] = clang
            ev["stem_overlap_key_vs_best_distractor"] = (round(ov_key, 2), round(ov_d, 2))
        else:
            f["clang_cue"] = False

        # --- grammatical cue: lead-in article vs option initial sound; singular/plural mismatch of the key only
        f["grammatical_cue"], ev["grammatical_note"] = self._grammatical_cue(lead, opts, key)

        # --- parallelism: numeric/non-numeric mix, sentence/fragment mix, or very uneven lengths
        f["nonparallel_options"], ev["nonparallel_note"] = self._nonparallel(opts)

        # --- numeric options
        nums = [(l, _num_value(opts[l]), _unit(opts[l])) for l in letters if _is_numeric_option(opts[l])]
        if len(nums) >= 3 and len(nums) == len(letters):
            vals = [v for _, v, _ in nums if v is not None]
            f["numeric_not_ordered"] = not (vals == sorted(vals) or vals == sorted(vals, reverse=True))
            units = {u for _, _, u in nums}
            f["numeric_units_inconsistent"] = len(units) > 1
            ev["numeric_units"] = sorted(units)
        else:
            f["numeric_not_ordered"] = False
            f["numeric_units_inconsistent"] = False

        # --- overlapping options: one option's text contained in another's
        low = {l: opts[l].lower() for l in letters}
        overlap = [(a, b) for a in letters for b in letters if a != b and len(low[a]) >= 6 and low[a] in low[b]]
        f["overlapping_options"] = bool(overlap)
        ev["overlaps"] = overlap

        # --- ordering of non-numeric options (NBME convention: alphabetical). Reported as a feature-like flaw.
        texts = [opts[l].lower() for l in letters]
        f["options_not_alphabetical"] = (not nums) and len(texts) >= 3 and texts != sorted(texts)

        features = {
            "n_options": len(letters), "key": key, "stem_words": len(stem.split()), "lead_in": lead,
            "key_chars": len(key_text), "mean_distractor_chars": round(statistics.mean(len(d) for d in distractors), 1) if distractors else None,
            "n_flaws": sum(1 for k in self.FLAWS if f.get(k) and k != "options_not_alphabetical"),
        }
        return {"flaws": f, "evidence": ev, "features": features}

    # ------------------------------------------------------------------ helpers
    def _absolute_hits(self, opts: Dict[str, str]) -> Dict[str, List[str]]:
        hits = {}
        for l, o in opts.items():
            text = o.lower()
            for pat in ABSOLUTE_EXEMPT:
                text = re.sub(pat, " ", text)
            words = sorted(set(_tokens(text)) & ABSOLUTE_TERMS)
            if words:
                hits[l] = words
        return hits

    def _length_outlier(self, texts: List[str]) -> bool:
        if len(texts) < 3:
            return False
        lens = sorted(len(t) for t in texts)
        med = statistics.median(lens)
        if med == 0:
            return False
        long_out = [x for x in lens if x > self.OUTLIER_RATIO * med]
        short_out = [x for x in lens if x < med / self.OUTLIER_RATIO]
        # BenchMarker: if half are shorter and half longer, pass. Flag only a unique outlier.
        return len(long_out) == 1 or (len(short_out) == 1 and med >= 12)

    def _grammatical_cue(self, lead: str, opts: Dict[str, str], key: str):
        if not opts:
            return False, ""
        m = re.search(r"\b(a|an)\s*[:?]?\s*$", lead.strip(), re.I)
        if m:
            art = m.group(1).lower()
            bad = []
            for l, o in opts.items():
                fw = _first_word(o).lower()
                if not fw:
                    continue
                vowel = fw[0] in "aeiou"
                if (art == "an") != vowel:
                    bad.append(l)
            if bad and len(bad) < len(opts):
                return True, "article '%s' mismatches options %s" % (art, bad)
        # key differs from all distractors in a simple form feature (ends with '.', starts with -ing, plural 's')
        if key in opts and len(opts) >= 3:
            def form(o):
                fw = _first_word(o).lower()
                return (o.endswith("."), fw.endswith("ing"), bool(re.search(r"\b\w+s\b$", o.split()[0] if o.split() else "")))
            kf = form(opts[key])
            df = [form(o) for l, o in opts.items() if l != key]
            for i, name in enumerate(["terminal period", "-ing start", "plural first word"]):
                if all(d[i] != kf[i] for d in df):
                    return True, "key alone differs in %s" % name
        return False, ""

    def _nonparallel(self, opts: Dict[str, str]):
        texts = list(opts.values())
        if len(texts) < 3:
            return False, ""
        numeric = [_is_numeric_option(t) for t in texts]
        if 0 < sum(numeric) < len(texts) and sum(numeric) >= 2:
            return True, "mix of numeric and non-numeric options"
        sentences = [t.endswith(".") and len(t.split()) >= 4 for t in texts]
        if 0 < sum(sentences) < len(texts):
            return True, "mix of full sentences and fragments"
        wc = [max(len(t.split()), 1) for t in texts]
        if statistics.mean(wc) >= 3 and statistics.pstdev(wc) / statistics.mean(wc) > self.NONPARALLEL_CV:
            return True, "word-count coefficient of variation %.2f" % (statistics.pstdev(wc) / statistics.mean(wc))
        return False, ""

    def _shared_components(self, opts: Dict[str, str]) -> bool:
        parts = [set(p.strip().lower() for p in re.split(r",|\band\b|&", o) if p.strip()) for o in opts.values()]
        allp = [p for s in parts for p in s]
        return len(allp) - len(set(allp)) >= 2


def detect(item: Dict) -> Dict:
    return Detector().detect(item)
