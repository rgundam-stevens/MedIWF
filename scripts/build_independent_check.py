"""Build the blind independent-reader check for the three most frequently flagged rules.

Inputs (public data files, Datasets 1 and 2 of the submission package):
  data/MedIWF_Dataset1_items_full_part{1..4}_*.csv   item text (analysed rows)
  data/MedIWF_Dataset2_detector_flags_part1_main_corpus.csv   detector flags

Outputs (out/):
  MedIWF_independent_check_rating_sheet.xlsx      the sheet each reader fills in (no model, prompt or flag information)
  MedIWF_independent_check_items.csv              the same 120 items as plain CSV (item_id, stem, options, key)
  independent_check_key_DO_NOT_SEND.csv           item_id -> job_id, model, prompt, stratum and the detector's flags
  independent_check_sampling_log.txt              counts per stratum, seed, and the sampling rule

Sampling rule (seed 20261021): from the 12,000 analysed main-corpus items, 30 items flagged only by the
longest-option rule, 30 only by the word-repetition (clang) rule, 20 only by the absolute-terms rule,
10 flagged by two or three of these rules, and 30 flagged by none of the three (other rules may fire);
within each stratum half plain-prompt and half guided-prompt items where the stratum allows; random order.
"""
import csv, random, collections, os, sys
csv.field_size_limit(10**9)

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
OUT = os.path.join(BASE, 'out')
os.makedirs(OUT, exist_ok=True)
SEED = 20261021
RULES = ['longest_option_key', 'clang_cue', 'absolute_terms']
TARGET = {'longest_only': 30, 'clang_only': 30, 'absolute_only': 20, 'multi': 10, 'none': 30}

flags = {}
with open(os.path.join(DATA, 'MedIWF_Dataset2_detector_flags_part1_main_corpus.csv'), encoding='utf-8-sig', newline='') as fh:
    for r in csv.DictReader(fh):
        flags[r['job_id']] = r
items = {}
for part in ['part1_plain_rep0', 'part2_plain_rep1', 'part3_guided_rep0', 'part4_guided_rep1']:
    with open(os.path.join(DATA, f'MedIWF_Dataset1_items_full_{part}.csv'), encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            if r['analysed'] == 'True':
                items[r['job_id']] = r
assert set(flags) == set(items), 'flag rows and analysed items differ'

def stratum(f):
    p = tuple(int(f[k]) for k in RULES)
    s = sum(p)
    if s == 0: return 'none'
    if s >= 2: return 'multi'
    return {0: 'longest_only', 1: 'clang_only', 2: 'absolute_only'}[p.index(1)]

pools = collections.defaultdict(list)
for j, f in flags.items():
    pools[(stratum(f), f['condition'])].append(j)
for k in pools: pools[k].sort()  # deterministic order before shuffling

rng = random.Random(SEED)
chosen = []
log = [f'seed {SEED}', 'stratum, condition: available -> sampled']
for st, n in TARGET.items():
    half = n // 2
    picks = []
    for cond, want in (('plain', half), ('guided', n - half)):
        pool = pools[(st, cond)]
        rng.shuffle(pool)
        take = pool[:want]
        picks += take
        log.append(f'{st}, {cond}: {len(pool)} -> {len(take)}')
    chosen += picks
assert len(chosen) == 120 and len(set(chosen)) == 120
rng.shuffle(chosen)

# model and prompt mix, for the log only
mix = collections.Counter(items[j]['model_label'] for j in chosen)
log.append('models represented: ' + ', '.join(f'{m} {c}' for m, c in sorted(mix.items())))
log.append('prompt: ' + str(collections.Counter(items[j]['condition'] for j in chosen)))
for k in RULES:
    log.append(f'detector-positive for {k}: {sum(int(flags[j][k]) for j in chosen)} of 120')

# answer key (never sent to readers)
with open(os.path.join(OUT, 'independent_check_key_DO_NOT_SEND.csv'), 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['item_id', 'job_id', 'model_label', 'tier', 'condition', 'rep', 'specialty', 'stratum'] + RULES + ['n_flaws', 'key'])
    for i, j in enumerate(chosen, 1):
        f = flags[j]; it = items[j]
        w.writerow([f'IND-{i:03d}', j, it['model_label'], f['tier'], f['condition'], f['rep'], f['specialty'], stratum(f)]
                   + [f[k] for k in RULES] + [f['n_flaws'], it['answer']])

# plain CSV of the items as shown
with open(os.path.join(OUT, 'MedIWF_independent_check_items.csv'), 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['item_id', 'stem', 'A', 'B', 'C', 'D', 'E', 'correct_answer'])
    for i, j in enumerate(chosen, 1):
        it = items[j]
        w.writerow([f'IND-{i:03d}', it['stem']] + [it[f'option_{L}'] for L in 'ABCDE'] + [it['answer']])

# rating sheet
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
wb = Workbook()
ws = wb.active
ws.title = 'ratings'
head = ['Item', 'Question (stem)', 'A', 'B', 'C', 'D', 'E', 'Correct answer',
        'Q1 Longest option: is the correct answer noticeably longer or more detailed than the other options? (yes / no / unsure)',
        'Q2 Word repetition: does the stem contain a word or phrase that is repeated in the correct answer but in none of the other options, in a way that could point to the answer? (yes / no / unsure)',
        'Q3 Absolute terms: does any option use absolute wording such as always, never, all, none, only, every, completely? (yes / no / unsure)',
        'Comment (optional)']
ws.append(head)
for c in ws[1]:
    c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical='top')
    c.fill = PatternFill('solid', fgColor='DDEBF7')
for i, j in enumerate(chosen, 1):
    it = items[j]
    ws.append([f'IND-{i:03d}', it['stem']] + [it[f'option_{L}'] for L in 'ABCDE'] + [it['answer'], '', '', '', ''])
widths = [9, 70, 22, 22, 22, 22, 22, 9, 18, 18, 18, 30]
for col, wdt in zip('ABCDEFGHIJKL', widths):
    ws.column_dimensions[col].width = wdt
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical='top')
dv = DataValidation(type='list', formula1='"yes,no,unsure"', allow_blank=True, showErrorMessage=True,
                    errorTitle='Answer', error='Please choose yes, no or unsure')
ws.add_data_validation(dv)
dv.add(f'I2:K{len(chosen) + 1}')
ws.freeze_panes = 'B2'
ws.row_dimensions[1].height = 120
info = wb.create_sheet('read me')
for line in [
    'MedIWF independent reader check: 120 multiple-choice questions.',
    'Please read the instruction sheet first, then answer the three questions for every item with yes, no or unsure.',
    'Work on your own, without discussing items with anyone and without any AI tool. There are no right answers to look up; we want your reading.',
    'The correct answer column shows which option the item writer keyed as correct. Do not judge whether the key is medically right; the three questions are only about the wording and shape of the options.',
    'Save the file with your initials added to the file name and return it by the date in the instruction sheet.',
]:
    info.append([line])
info.column_dimensions['A'].width = 120
for row in info.iter_rows():
    for c in row: c.alignment = Alignment(wrap_text=True, vertical='top')
wb.save(os.path.join(OUT, 'MedIWF_independent_check_rating_sheet.xlsx'))

with open(os.path.join(OUT, 'independent_check_sampling_log.txt'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(log) + '\n')
print('\n'.join(log))
