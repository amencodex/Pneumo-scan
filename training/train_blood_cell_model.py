"""
Train a local white blood cell image model for PneumoScan admin review.

Expected dataset layout:

dataset2-master/
  dataset2-master/
    images/
      TRAIN/
        EOSINOPHIL/
        LYMPHOCYTE/
        MONOCYTE/
        NEUTROPHIL/
      TEST/
        EOSINOPHIL/
        LYMPHOCYTE/
        MONOCYTE/
        NEUTROPHIL/

Output:
  models/blood_cell_model.json

Important:
This model classifies white blood cell image type. It does not diagnose viral
or bacterial pneumonia. The admin UI uses the cell type as one cautious support
signal for clinician review only.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
CLASSES = ["EOSINOPHIL", "LYMPHOCYTE", "MONOCYTE", "NEUTROPHIL"]


def load_image(path: Path, size: int) -> np.ndarray:
    image = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32) / 255.0


def extract_features(path: Path, size: int) -> list[float]:
    rgb = load_image(path, size)
    gray = rgb.mean(axis=2)
    values = gray.reshape(-1)
    features: list[float] = rgb.reshape(-1).astype(np.float32).tolist()

    for channel_index in range(3):
        channel = rgb[:, :, channel_index].reshape(-1)
        features.extend(
            [
                float(channel.mean()),
                float(channel.std()),
                float(np.percentile(channel, 10)),
                float(np.percentile(channel, 50)),
                float(np.percentile(channel, 90)),
            ]
        )
        hist = np.bincount(np.clip((channel * 8).astype(int), 0, 7), minlength=8).astype(np.float32)
        hist = hist / max(1, channel.size)
        features.extend(float(value) for value in hist)

    features.extend(
        [
            float(values.mean()),
            float(values.std()),
            float(np.percentile(values, 10)),
            float(np.percentile(values, 50)),
            float(np.percentile(values, 90)),
        ]
    )
    gray_hist = np.bincount(np.clip((values * 12).astype(int), 0, 11), minlength=12).astype(np.float32)
    gray_hist = gray_hist / max(1, values.size)
    features.extend(float(value) for value in gray_hist)
    return features


def infer_label(path: Path) -> str | None:
    parts = {part.upper() for part in path.parts}
    for label in CLASSES:
        if label in parts:
            return label
    return None


def collect_dataset(data_dir: Path, size: int, max_per_class: int, seed: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    by_class: dict[str, list[Path]] = {label: [] for label in CLASSES}
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        label = infer_label(path.relative_to(data_dir))
        if label:
            by_class[label].append(path)

    random.seed(seed)
    rows: list[list[float]] = []
    labels: list[str] = []
    paths: list[str] = []

    for label in CLASSES:
        candidates = by_class[label]
        if len(candidates) < 10:
            raise SystemExit(f"Add more labeled images for {label}. Found {len(candidates)}.")
        random.shuffle(candidates)
        selected = candidates[:max_per_class] if max_per_class > 0 else candidates
        print(f"{label}: using {len(selected)} of {len(candidates)} images")
        for path in selected:
            try:
                rows.append(extract_features(path, size))
                labels.append(label)
                paths.append(str(path))
            except Exception as exc:
                print(f"Skipping {path}: {exc}")

    if len(rows) < 40:
        raise SystemExit("Add more labeled blood cell images before training.")

    return np.asarray(rows, dtype=np.float32), np.asarray(labels), paths


def train_model(data_dir: Path, output_path: Path, size: int, max_per_class: int, seed: int) -> None:
    x, y_names, paths = collect_dataset(data_dir, size, max_per_class, seed)
    y = np.asarray([CLASSES.index(label) for label in y_names], dtype=np.int64)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.22,
        random_state=seed,
        stratify=y,
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    classifier = MLPClassifier(
        hidden_layer_sizes=(80,),
        activation="relu",
        solver="adam",
        alpha=0.0008,
        batch_size=128,
        learning_rate_init=0.001,
        max_iter=90,
        early_stopping=True,
        validation_fraction=0.12,
        n_iter_no_change=12,
        random_state=seed,
    )
    classifier.fit(x_train_scaled, y_train)

    predictions = classifier.predict(x_test_scaled)
    accuracy = float(accuracy_score(y_test, predictions))
    report = classification_report(
        y_test,
        predictions,
        labels=list(range(len(CLASSES))),
        target_names=CLASSES,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y_test, predictions, labels=list(range(len(CLASSES)))).tolist()

    model = {
        "name": "PneumoScan local white blood cell model",
        "model_type": "standardized_one_hidden_layer_mlp_blood_cell_features",
        "version": 1,
        "input_size": size,
        "feature_count": int(x.shape[1]),
        "classes": CLASSES,
        "mean": scaler.mean_.astype(float).tolist(),
        "scale": scaler.scale_.astype(float).tolist(),
        "hidden_weights": classifier.coefs_[0].astype(float).tolist(),
        "hidden_bias": classifier.intercepts_[0].astype(float).tolist(),
        "output_weights": classifier.coefs_[1].astype(float).tolist(),
        "output_bias": classifier.intercepts_[1].astype(float).tolist(),
        "labels": {
            "EOSINOPHIL": "eosinophil-like white cell",
            "LYMPHOCYTE": "lymphocyte-like white cell",
            "MONOCYTE": "monocyte-like white cell",
            "NEUTROPHIL": "neutrophil-like white cell",
        },
        "validation": {
            "image_count": int(len(paths)),
            "accuracy": accuracy,
            "confusion_matrix_labels": CLASSES,
            "confusion_matrix": matrix,
            "classification_report": report,
        },
        "medical_warning": (
            "Research/education only. This classifies blood cell image type and is not a viral/bacterial "
            "diagnostic device. Confirm infection concerns with qualified clinicians and approved tests."
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(model, indent=2), encoding="utf-8")

    print(f"Saved model to: {output_path}")
    print(f"Validation accuracy: {accuracy:.3f}")
    print(f"Confusion matrix labels: {CLASSES}")
    print(matrix)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Folder containing white blood cell class folders")
    parser.add_argument("--output", default="models/blood_cell_model.json", help="Output JSON model path")
    parser.add_argument("--size", type=int, default=32, help="Resize images to this square size")
    parser.add_argument("--max-per-class", type=int, default=2000, help="Balanced sample cap per class; use 0 for all")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train_model(Path(args.data_dir), Path(args.output), args.size, args.max_per_class, args.seed)


if __name__ == "__main__":
    main()
