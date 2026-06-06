"""
Prepare the RSNA Pneumonia Detection Challenge dataset for PneumoScan training.

The RSNA download contains DICOM files plus CSV labels. This script:
  - reads the RSNA label files
  - converts labeled DICOM X-rays to JPG
  - places clean examples into:

dataset/
  pneumonia/
    rsna/
  normal/
    rsna/

By default, it uses only:
  - Lung Opacity -> pneumonia
  - Normal -> normal

It skips "No Lung Opacity / Not Normal" because those are not true normal
examples. You can include them as negative examples with
--include-nonnormal-negative, but that makes the "normal" class less clean.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import pydicom
except ImportError as exc:  # pragma: no cover - user environment helper
    raise SystemExit(
        "Missing pydicom. Install it with:\n"
        "python -m pip install pydicom\n"
        "or run:\n"
        "python -m pip install -r training\\requirements.txt"
    ) from exc


PNEUMONIA_CLASS = "Lung Opacity"
NORMAL_CLASS = "Normal"
NONNORMAL_NEGATIVE_CLASS = "No Lung Opacity / Not Normal"


def read_target_labels(labels_path: Path) -> dict[str, int]:
    labels: dict[str, int] = {}

    with labels_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            patient_id = row["patientId"].strip()
            target = int(row["Target"])
            labels[patient_id] = max(labels.get(patient_id, 0), target)

    return labels


def read_detail_labels(detail_path: Path) -> dict[str, set[str]]:
    details: dict[str, set[str]] = {}

    with detail_path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            patient_id = row["patientId"].strip()
            details.setdefault(patient_id, set()).add(row["class"].strip())

    return details


def choose_label(
    patient_id: str,
    target_labels: dict[str, int],
    detail_labels: dict[str, set[str]],
    include_nonnormal_negative: bool,
) -> str | None:
    target = target_labels.get(patient_id, 0)
    classes = detail_labels.get(patient_id, set())

    if target == 1 or PNEUMONIA_CLASS in classes:
        return "pneumonia"

    if NORMAL_CLASS in classes:
        return "normal"

    if include_nonnormal_negative and NONNORMAL_NEGATIVE_CLASS in classes:
        return "normal"

    return None


def dicom_to_uint8(path: Path) -> np.ndarray:
    dataset = pydicom.dcmread(str(path))
    pixels = dataset.pixel_array.astype(np.float32)

    slope = float(getattr(dataset, "RescaleSlope", 1.0) or 1.0)
    intercept = float(getattr(dataset, "RescaleIntercept", 0.0) or 0.0)
    pixels = pixels * slope + intercept

    if getattr(dataset, "PhotometricInterpretation", "") == "MONOCHROME1":
        pixels = pixels.max() - pixels

    pixels -= pixels.min()
    max_value = pixels.max()
    if max_value > 0:
        pixels /= max_value

    return (pixels * 255).clip(0, 255).astype(np.uint8)


def convert_dicom_to_jpg(source: Path, destination: Path) -> None:
    image_array = dicom_to_uint8(source)
    image = Image.fromarray(image_array, mode="L")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="JPEG", quality=94, optimize=True)


def collect_jobs(
    rsna_dir: Path,
    output_dataset: Path,
    include_nonnormal_negative: bool,
    max_per_class: int,
) -> list[tuple[Path, Path, str]]:
    labels_path = rsna_dir / "stage_2_train_labels.csv"
    detail_path = rsna_dir / "stage_2_detailed_class_info.csv"
    image_dir = rsna_dir / "stage_2_train_images"

    if not labels_path.exists():
        raise SystemExit(f"Missing labels file: {labels_path}")
    if not detail_path.exists():
        raise SystemExit(f"Missing detailed class file: {detail_path}")
    if not image_dir.exists():
        raise SystemExit(f"Missing DICOM image folder: {image_dir}")

    target_labels = read_target_labels(labels_path)
    detail_labels = read_detail_labels(detail_path)
    class_counts: Counter[str] = Counter()
    jobs: list[tuple[Path, Path, str]] = []
    skipped = Counter()

    for source in sorted(image_dir.glob("*.dcm")):
        patient_id = source.stem
        label = choose_label(
            patient_id,
            target_labels,
            detail_labels,
            include_nonnormal_negative,
        )

        if label is None:
            skipped["not_clean_label"] += 1
            continue

        if max_per_class > 0 and class_counts[label] >= max_per_class:
            skipped[f"{label}_over_limit"] += 1
            continue

        destination = output_dataset / label / "rsna" / f"rsna_{patient_id}.jpg"
        jobs.append((source, destination, label))
        class_counts[label] += 1

    print("RSNA images selected:")
    print(f"  normal: {class_counts.get('normal', 0)}")
    print(f"  pneumonia: {class_counts.get('pneumonia', 0)}")
    if skipped:
        print("Skipped:")
        for reason, count in sorted(skipped.items()):
            print(f"  {reason}: {count}")

    if not jobs:
        raise SystemExit("No labeled RSNA images were selected.")

    return jobs


def prepare_dataset(
    rsna_dir: Path,
    output_dataset: Path,
    include_nonnormal_negative: bool,
    max_per_class: int,
) -> None:
    jobs = collect_jobs(
        rsna_dir=rsna_dir,
        output_dataset=output_dataset,
        include_nonnormal_negative=include_nonnormal_negative,
        max_per_class=max_per_class,
    )

    converted = Counter()
    skipped_existing = Counter()
    failed = Counter()

    total = len(jobs)
    for index, (source, destination, label) in enumerate(jobs, start=1):
        if destination.exists():
            skipped_existing[label] += 1
        else:
            try:
                convert_dicom_to_jpg(source, destination)
                converted[label] += 1
            except Exception as exc:
                failed[label] += 1
                print(f"Could not convert {source.name}: {exc}")

        if index == 1 or index % 500 == 0 or index == total:
            print(f"Prepared {index}/{total} RSNA images...")

    print("")
    print("Done preparing RSNA images.")
    print(f"Output dataset folder: {output_dataset}")
    print(f"Converted normal: {converted.get('normal', 0)}")
    print(f"Converted pneumonia: {converted.get('pneumonia', 0)}")
    print(f"Already existed normal: {skipped_existing.get('normal', 0)}")
    print(f"Already existed pneumonia: {skipped_existing.get('pneumonia', 0)}")
    if failed:
        print(f"Failed normal: {failed.get('normal', 0)}")
        print(f"Failed pneumonia: {failed.get('pneumonia', 0)}")

    print("")
    print("Next train with:")
    print('python "training\\train_pneumonia_model.py" --data-dir "dataset" --output "models\\pneumonia_model.json"')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rsna-dir",
        required=True,
        help="Folder containing stage_2_train_images and the RSNA CSV label files",
    )
    parser.add_argument(
        "--output-dataset",
        default="dataset",
        help="Your PneumoScan dataset folder",
    )
    parser.add_argument(
        "--include-nonnormal-negative",
        action="store_true",
        help="Also add RSNA 'No Lung Opacity / Not Normal' images as negative examples",
    )
    parser.add_argument(
        "--max-per-class",
        type=int,
        default=0,
        help="Optional cap per class. Use 0 for all clean labeled images.",
    )
    args = parser.parse_args()

    prepare_dataset(
        rsna_dir=Path(args.rsna_dir),
        output_dataset=Path(args.output_dataset),
        include_nonnormal_negative=args.include_nonnormal_negative,
        max_per_class=args.max_per_class,
    )


if __name__ == "__main__":
    main()
