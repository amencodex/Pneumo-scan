"""
Train a browser-loadable pneumonia research model from chest X-ray images.

Expected folder layout:

dataset/
  pneumonia/
    image_001.jpg
    image_002.png
  normal/
    image_101.jpg
    image_102.png

The script also supports common nested dataset layouts such as:

dataset/
  train/
    PNEUMONIA/
    NORMAL/
  test/
    PNEUMONIA/
    NORMAL/

Output:
  models/pneumonia_model.json

Important:
This is for research and education only. It is not a medical device and must not
be used to diagnose a patient.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

FEATURE_NAMES = [
    "mean_gray",
    "std_gray",
    "min_gray",
    "max_gray",
    "p10_gray",
    "p25_gray",
    "p50_gray",
    "p75_gray",
    "p90_gray",
    "dark_ratio",
    "mid_ratio",
    "bright_ratio",
    "edge_mean",
    "edge_strong_ratio",
    "symmetry_abs_diff",
]

for bin_index in range(16):
    FEATURE_NAMES.append(f"hist_gray_{bin_index}")

for grid_y in range(4):
    for grid_x in range(4):
        FEATURE_NAMES.append(f"grid_mean_{grid_y}_{grid_x}")
        FEATURE_NAMES.append(f"grid_std_{grid_y}_{grid_x}")


def load_xray(path: Path, size: int) -> np.ndarray:
    image = Image.open(path).convert("L").resize((size, size), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32) / 255.0


def add_histogram(features: dict[str, float], gray: np.ndarray) -> None:
    values = gray.reshape(-1)
    indices = np.clip((values * 16).astype(int), 0, 15)
    counts = np.bincount(indices, minlength=16).astype(np.float32)
    counts = counts / max(1, values.size)

    for index, value in enumerate(counts):
        features[f"hist_gray_{index}"] = float(value)


def add_grid_features(features: dict[str, float], gray: np.ndarray) -> None:
    size = gray.shape[0]
    grid = 4
    cell = size // grid

    for grid_y in range(grid):
        for grid_x in range(grid):
            y_start = grid_y * cell
            y_end = size if grid_y == grid - 1 else (grid_y + 1) * cell
            x_start = grid_x * cell
            x_end = size if grid_x == grid - 1 else (grid_x + 1) * cell
            patch = gray[y_start:y_end, x_start:x_end]

            features[f"grid_mean_{grid_y}_{grid_x}"] = float(patch.mean())
            features[f"grid_std_{grid_y}_{grid_x}"] = float(patch.std())


def symmetry_abs_diff(gray: np.ndarray) -> float:
    left = gray[:, : gray.shape[1] // 2]
    right = np.fliplr(gray[:, -left.shape[1] :])
    return float(np.abs(left - right).mean())


def extract_features(path: Path, size: int) -> list[float]:
    gray = load_xray(path, size)
    values = gray.reshape(-1)
    dx = gray[:-1, 1:] - gray[:-1, :-1]
    dy = gray[1:, :-1] - gray[:-1, :-1]
    edge = np.sqrt(dx * dx + dy * dy)

    features = {
        "mean_gray": float(values.mean()),
        "std_gray": float(values.std()),
        "min_gray": float(values.min()),
        "max_gray": float(values.max()),
        "p10_gray": float(np.percentile(values, 10)),
        "p25_gray": float(np.percentile(values, 25)),
        "p50_gray": float(np.percentile(values, 50)),
        "p75_gray": float(np.percentile(values, 75)),
        "p90_gray": float(np.percentile(values, 90)),
        "dark_ratio": float((values < 0.25).mean()),
        "mid_ratio": float(((values >= 0.25) & (values <= 0.75)).mean()),
        "bright_ratio": float((values > 0.75).mean()),
        "edge_mean": float(edge.mean()),
        "edge_strong_ratio": float((edge > 0.18).mean()),
        "symmetry_abs_diff": symmetry_abs_diff(gray),
    }

    add_histogram(features, gray)
    add_grid_features(features, gray)
    return [features[name] for name in FEATURE_NAMES]


def infer_label(path: Path) -> int | None:
    parts = {part.lower() for part in path.parts}

    if "pneumonia" in parts:
        return 1

    if "normal" in parts:
        return 0

    return None


def collect_dataset(data_dir: Path, size: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rows: list[list[float]] = []
    labels: list[int] = []
    paths: list[str] = []

    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        label = infer_label(path.relative_to(data_dir))
        if label is None:
            continue

        try:
            rows.append(extract_features(path, size))
            labels.append(label)
            paths.append(str(path))
        except Exception as exc:
            print(f"Skipping {path}: {exc}")

    if len(rows) < 10:
        raise SystemExit("Add more labeled images before training. Found fewer than 10.")

    class_counts = {label: labels.count(label) for label in sorted(set(labels))}
    if len(class_counts) != 2:
        raise SystemExit("Training needs both pneumonia and normal images.")

    if min(class_counts.values()) < 2:
        raise SystemExit("Add at least 2 images in each class before training.")

    print(f"Loaded {len(rows)} images:")
    print(f"  normal: {class_counts.get(0, 0)}")
    print(f"  pneumonia: {class_counts.get(1, 0)}")

    return np.asarray(rows, dtype=np.float32), np.asarray(labels, dtype=np.int64), paths


def train_model(data_dir: Path, output_path: Path, size: int, threshold: float) -> None:
    x, y, paths = collect_dataset(data_dir, size)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    classifier = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        solver="liblinear",
        random_state=42,
    )
    classifier.fit(x_train_scaled, y_train)

    predictions = classifier.predict(x_test_scaled)
    accuracy = float(accuracy_score(y_test, predictions))
    report = classification_report(
        y_test,
        predictions,
        target_names=["normal", "pneumonia"],
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y_test, predictions).tolist()

    model = {
        "name": "PneumoScan local pneumonia-like X-ray model",
        "model_type": "standardized_logistic_regression_xray_features",
        "version": 1,
        "input_size": size,
        "threshold": threshold,
        "feature_names": FEATURE_NAMES,
        "mean": scaler.mean_.astype(float).tolist(),
        "scale": scaler.scale_.astype(float).tolist(),
        "weights": classifier.coef_[0].astype(float).tolist(),
        "bias": float(classifier.intercept_[0]),
        "labels": {
            "positive": "pneumonia_like_pattern",
            "negative": "normal_xray_pattern",
        },
        "validation": {
            "image_count": int(len(paths)),
            "accuracy": accuracy,
            "confusion_matrix": matrix,
            "classification_report": report,
        },
        "medical_warning": (
            "Research/education only. Not a pneumonia diagnostic device. "
            "Confirm medical concerns with qualified clinicians and approved care."
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(model, indent=2), encoding="utf-8")

    print(f"Saved model to: {output_path}")
    print(f"Validation accuracy: {accuracy:.3f}")
    print("Confusion matrix [[true normal, false pneumonia], [false normal, true pneumonia]]:")
    print(matrix)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Folder containing pneumonia and normal image folders")
    parser.add_argument("--output", default="models/pneumonia_model.json", help="Output JSON model path")
    parser.add_argument("--size", type=int, default=96, help="Resize images to this square size")
    parser.add_argument("--threshold", type=float, default=0.5, help="Detection threshold from 0 to 1")
    args = parser.parse_args()

    train_model(Path(args.data_dir), Path(args.output), args.size, args.threshold)


if __name__ == "__main__":
    main()
