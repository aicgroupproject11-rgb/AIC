from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent 
MANIFEST_PATH = BASE_DIR / "data_processing" / "manifest.csv"
DATA_ROOT = BASE_DIR / "data_processing" 

REQUIRED_COLUMNS = [
    "keyframe_id", "collection_id", "video_id",
    "frame_number", "timestamp_ms", "image_path", "video_path",
]

_manifest_df = None  


def load_manifest() -> pd.DataFrame:
    global _manifest_df
    if _manifest_df is not None:
        return _manifest_df

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Not found: {MANIFEST_PATH}")

    df = pd.read_csv(MANIFEST_PATH, dtype={"video_id": str, "keyframe_id": str, "collection_id": str})
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"manifest.csv not found: {missing}")

    df = df.set_index("keyframe_id", drop=False)
    _manifest_df = df
    return df


def get_manifest_row(keyframe_id: str) -> dict:
    df = load_manifest()
    if keyframe_id not in df.index:
        raise ValueError(f"keyframe_id not found in manifest: {keyframe_id}")
    row = df.loc[keyframe_id]
    return row.to_dict()


def resolve_image_path(relative_path: str) -> str:
    return str(DATA_ROOT / relative_path)