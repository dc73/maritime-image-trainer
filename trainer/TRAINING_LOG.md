# Watchkeeper Vessel Classifier — Training Log

## Run 1 (stopped, no epoch completed)
- **Command:** `.venv/bin/python -m trainer.train --epochs 2 --batch 128`
- **Device:** CPU (GPU shared + OOM, `CUDA_VISIBLE_DEVICES=""` forced CPU)
- **Backbone:** resnet18 (ImageNet-pretrained)
- **Classes (6):** caesar_sarship, marinetraffic, roboflow, satellite, thermal_challenge, thermal_tau2
- **Split:** train=36,801 / val=4,089
- **Status:** STOPPED before epoch 1 finished (~5h25m CPU time burned). No checkpoint written because
  the run was halted mid-epoch 1 (only per-epoch logging).
- **Why stopped:** shared GPU OOM + RAM pressure (122 GB total, ~1 GB available) + the opencode
  agent consuming RAM. CPU training of ~37k 256×256 images through ResNet18 is slow.

## Resume
```
.venv/bin/python -m trainer.train --epochs 2 --batch 128 --resume checkpoints/last_vessel_classifier.pt
```
Added per-epoch resumable checkpoints (`last_vessel_classifier.pt` saved every epoch,
`best_vessel_classifier.pt` on best val_acc) so training can pick up where it left off.

## Dataset summary
- Raw images: 40,890 total across 6 sources
  - caesar_sarship: 39,729 (CAESAR SAR-Ship-Dataset)
  - thermal_challenge: 951 (rafariva/ThermalDatasets PBVS challenge)
  - thermal_tau2: 101 (rafariva/ThermalDatasets HR TAU2)
  - roboflow: 51 (Roboflow thermal-ships)
  - marinetraffic: 39
  - satellite: 19
- Kaggle `thermal-images-for-human-detection`: **not collected** (needs Kaggle login).
