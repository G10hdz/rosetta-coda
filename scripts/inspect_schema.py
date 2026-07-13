"""Schema inspection for sw-combinatoriality CSVs (Rosetta Coda step 1)."""
import pandas as pd

pd.set_option("display.width", 120)

FILES = {
    "DominicaCodas": ("external/sw-combinatoriality/data/DominicaCodas.csv", "utf-8-sig"),
    "sperm-whale-dialogues": ("external/sw-combinatoriality/data/sperm-whale-dialogues.csv", "utf-8-sig"),
}


def per_column(df):
    for c in df.columns:
        s = df[c]
        base = f"  {c:<12} {str(s.dtype):<8} nonnull={s.notna().sum():<5} null={s.isna().sum():<4}"
        if pd.api.types.is_numeric_dtype(s):
            print(f"{base} min={s.min():.4g} max={s.max():.4g} mean={s.mean():.4g}")
        else:
            samp = list(pd.Series(s.dropna().unique())[:8])
            print(f"{base} n_unique={s.nunique()} sample={samp}")


def main():
    for name, (path, enc) in FILES.items():
        df = pd.read_csv(path, encoding=enc)
        print(f"\n{'='*70}\n{name}  ({path})\n  rows={len(df)}  cols={df.shape[1]}\n{'-'*70}")
        per_column(df)

        if name == "DominicaCodas":
            print("\n  -- dataset summary --")
            for col in ["IDN", "Unit", "UnitNum", "Clan", "CodaType"]:
                print(f"  distinct {col}: {df[col].nunique()}")
            print("\n  CodaType top15:\n", df["CodaType"].value_counts().head(15).to_string())
            print("\n  nClicks distribution:\n", df["nClicks"].value_counts().sort_index().to_string())
            print(f"\n  Duration min/max/mean: {df.Duration.min():.4g}/{df.Duration.max():.4g}/{df.Duration.mean():.4g}")
        else:
            print("\n  -- dataset summary --")
            for col in ["Whale", "REC"]:
                if col in df.columns:
                    print(f"  distinct {col}: {df[col].nunique()}")
            print("\n  nClicks distribution:\n", df["nClicks"].value_counts().sort_index().to_string())
            print(f"\n  Duration min/max/mean: {df.Duration.min():.4g}/{df.Duration.max():.4g}/{df.Duration.mean():.4g}")


if __name__ == "__main__":
    main()
