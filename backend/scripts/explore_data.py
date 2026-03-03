"""Quick exploration of the 3 crop datasets."""

import os

import pandas as pd

base = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# Dataset 1
d1 = pd.read_csv(os.path.join(base, "dataset1", "Crop_recommendation.csv"))
print("=== DATASET 1: dataset1/Crop_recommendation.csv ===")
print(f"Shape: {d1.shape}")
print(f"Columns: {list(d1.columns)}")
print(f"Labels: {d1.iloc[:,-1].nunique()} unique -> {sorted(d1.iloc[:,-1].unique())}")
print(d1.head(3).to_string())
print(d1.dtypes)
print(f"Nulls:\n{d1.isnull().sum()}")
print()

# Dataset 2 files
for f in ["Crop_recommendation.csv", "Central_datafile.csv", "Statewise_datafile.csv"]:
    fp = os.path.join(base, "data set(2)", f)
    d = pd.read_csv(fp)
    print(f"=== DATASET 2: {f} ===")
    print(f"Shape: {d.shape}")
    print(f"Columns: {list(d.columns)}")
    if "label" in [c.lower() for c in d.columns]:
        lbl_col = next(c for c in d.columns if c.lower() == "label")
        print(f"Labels: {d[lbl_col].nunique()} unique -> {sorted(d[lbl_col].unique())[:15]}")
    print(d.head(2).to_string())
    print(d.dtypes)
    print()

# Dataset 3 files
for f in ["Crop_recommendation.csv", "Crop_Data.xlsx.csv"]:
    fp = os.path.join(base, "dataset-3", f)
    d = pd.read_csv(fp)
    print(f"=== DATASET 3: {f} ===")
    print(f"Shape: {d.shape}")
    print(f"Columns: {list(d.columns)}")
    if "label" in [c.lower() for c in d.columns]:
        lbl_col = next(c for c in d.columns if c.lower() == "label")
        print(f"Labels: {d[lbl_col].nunique()} unique -> {sorted(d[lbl_col].unique())[:15]}")
    print(d.head(2).to_string())
    print(d.dtypes)
    print()
