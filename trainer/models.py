"""Model definitions for the maritime/thermal vessel classifier."""
import torch
import torch.nn as nn
import torchvision.models as models


def build_model(num_classes, backbone="resnet18"):
    """Return a classification backbone preloaded with ImageNet weights."""
    if backbone == "resnet18":
        m = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    elif backbone == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    elif backbone == "efficientnetb0":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
    else:
        raise ValueError(f"unknown backbone {backbone}")
    in_features = m.fc.in_features
    m.fc = nn.Linear(in_features, num_classes)
    return m


class ThermalSuperResNet(nn.Module):
    """Lightweight super-resolution model for LR->HR thermal images."""
    def __init__(self, scale=2):
        super().__init__()
        self.scale = scale
        self.body = nn.Sequential(
            nn.Conv2d(3, 32, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(32, 32, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(32, 32, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(32, 32, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(32, 3, 3, 1, 1),
        )
        self.upsample = nn.Sequential(
            nn.Upsample(scale_factor=scale, mode="bilinear"),
            nn.Conv2d(3, 3, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(3, 3, 3, 1, 1),
        )

    def forward(self, x):
        f = self.body(x)
        return self.upsample(f)
