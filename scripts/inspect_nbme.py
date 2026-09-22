"""Print ONLY the structure and numeric summaries of the NBME files. Never prints item text."""
import pandas as pd, numpy as np, pathlib
root = pathlib.Path(__file__).resolve().parents[1] / "data" / "nbme"
for f in ["train_final.xlsx", "test_final.xlsx", "gold_final.xlsx"]:
    df = pd.read_excel(root / f)
    print("=" * 60, "\n", f, df.shape)
    print("columns:", list(df.columns))
    num = df.select_dtypes(include=[np.number])
    if not num.empty:
        print(num.describe().T.round(3).to_string())
    for c in ["Answer_Key", "ItemType", "EXAM"]:
        if c in df:
            print(c, df[c].value_counts().to_dict())
