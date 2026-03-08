# Model Training Guide

## Environment Setup

Recommended: GPU workstation or Google Colab (not Raspberry Pi for training).

```bash
pip install ultralytics==8.1.0
```

## Train

```bash
python training/train.py \
  --data data/data.yaml \
  --epochs 100 \
  --batch 16 \
  --imgsz 640 \
  --device 0          # GPU; use "cpu" if no GPU
```

Outputs saved to `training/runs/atm_surveillance/`.

## Evaluate

```bash
python training/evaluate.py \
  --model training/runs/atm_surveillance/weights/best.pt \
  --data data/data.yaml
```

## Export to ONNX (for Raspberry Pi)

```bash
python training/export_model.py \
  --model training/runs/atm_surveillance/weights/best.pt \
  --output-dir models
```

Copy `models/atm_surveillance.onnx` to the Raspberry Pi.

## Hyperparameter Tips

| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| `--epochs` | 100–150 | Use early stopping |
| `--batch` | 16 (GPU) / 8 (CPU) | Adjust to VRAM |
| `--imgsz` | 640 | Balance accuracy/speed |
| `--lr0` | 0.01 | Default YOLOv8 |

## Expected Metrics (target)

| Metric | Target |
|--------|--------|
| Precision | > 0.85 |
| Recall | > 0.80 |
| mAP@50 | > 0.85 |
| mAP@50-95 | > 0.60 |
