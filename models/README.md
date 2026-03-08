# Models Directory

Place trained model files here:

| File | Description |
|------|-------------|
| `atm_surveillance.pt` | Custom YOLOv8 nano model (gun, knife, helmet, mask) |
| `atm_surveillance.onnx` | ONNX export for Raspberry Pi inference |
| `yolov8n.pt` | Pre-trained YOLOv8 nano (person detection) |

## Training your own model

1. Prepare datasets: `python data/prepare_dataset.py`
2. Merge datasets: `python data/merge_datasets.py`
3. Train: `python training/train.py`
4. Export: `python training/export_model.py --model training/runs/atm_surveillance/weights/best.pt`

## Download pre-trained YOLOv8n

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
mv yolov8n.pt models/
```

> **Note**: Model files are excluded from version control via `.gitignore`.
> Do NOT commit large model files to the repository.
