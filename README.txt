PneumoScan Research folder layout

website/
  pneumonia_scan_local_model.html
  Open this file in your browser.

training/
  train_pneumonia_model.py
  Run this file to train your local model.

dataset/
  pneumonia/
    Put confirmed pneumonia chest X-ray images here.

  normal/
    Put confirmed normal chest X-ray images here.

models/
  The trained pneumonia_model.json file will be saved here.

notes/
  Optional folder for dataset notes, citations, and source links.


Training command from inside the "pneumonia scan" folder:

python training\train_pneumonia_model.py --data-dir dataset --output models\pneumonia_model.json


Training command using the full path:

python "C:\Users\previ\Documents\Codex\2026-06-01\can-you-give-me-full-code\outputs\pneumonia scan\training\train_pneumonia_model.py" --data-dir "C:\Users\previ\Documents\Codex\2026-06-01\can-you-give-me-full-code\outputs\pneumonia scan\dataset" --output "C:\Users\previ\Documents\Codex\2026-06-01\can-you-give-me-full-code\outputs\pneumonia scan\models\pneumonia_model.json"


After training:

1. Open website\pneumonia_scan_local_model.html
2. Click "Select pneumonia_model.json"
3. Choose models\pneumonia_model.json
4. Upload a chest X-ray image
5. Run local analysis


What "labeled images" means:

The folder name is the label.

dataset\pneumonia
  Images confirmed by the dataset/source as pneumonia.

dataset\normal
  Images confirmed by the dataset/source as normal.

Do not guess labels by looking at the X-ray yourself. Use a dataset where experts or the dataset publisher already labeled the images.


Possible public dataset sources:

Kaggle Chest X-Ray Pneumonia dataset:
https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia

RSNA Pneumonia Detection Challenge:
https://www.rsna.org/education/ai-resources-and-training/%20%5C%20ai-image-challenge/RSNA-Pneumonia-Detection-Challenge-2018


Safety note:
This project is for research and education only. It must not be used to diagnose pneumonia or tell a patient they have pneumonia. Chest X-rays should be interpreted by qualified clinicians with symptoms, exam findings, oxygen level, and other clinical information.
