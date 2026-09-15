"""PyTorch dataset for the maritime + thermal ship images.

Wraps the raw image folders (ship_data/raw/*) into a torchvision Dataset.
Each sample: (image tensor, label) where label is the source folder name.
Used by train.py to train a vessel/thermal classifier.
"""
from pathlib import Path
from torch.utils.data import Dataset

import torch
import torchvision.transforms as T


class ShipImageDataset(Dataset):
    """Dataset over ship_data/raw/<source>/*.{jpg,png}.

    Label = source folder name (marinetraffic, roboflow, caesar_sarship,
    satellite, thermal_tau2, thermal_challenge, ...).
    """

    IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    def __init__(self, root, split="train", transform=None):
        root = Path(root)
        self.folders = sorted([d for d in root.iterdir() if d.is_dir()])
        self.class_to_idx = {d.name: i for i, d in enumerate(self.folders)}
        self.samples = []
        for d in self.folders:
            for f in sorted(d.iterdir()):
                if f.suffix.lower() in self.IMG_EXTS:
                    self.samples.append((str(f), self.class_to_idx[d.name]))
        if transform is None:
            self.transform = T.Compose([
                T.Resize((256, 256)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        else:
            self.transform = transform
        # Optional train/val split by index for reproducibility.
        if split == "val":
            n = len(self.samples)
            self.samples = self.samples[int(n * 0.9):]
        elif split == "train":
            n = len(self.samples)
            self.samples = self.samples[: int(n * 0.9)]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        from PIL import Image
        img = Image.open(path).convert("RGB")
        return self.transform(img), torch.tensor(label)

    @property
    def class_names(self):
        return list(self.class_to_idx.keys())
