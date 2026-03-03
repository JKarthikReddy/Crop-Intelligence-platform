"""Crop Recommendation Neural Network architecture.

A multi-layer feedforward classifier:
  Input(7) -> 64 -> ReLU -> BN -> Dropout
           -> 128 -> ReLU -> BN -> Dropout
           -> 64 -> ReLU -> BN -> Dropout
           -> num_classes (softmax at inference)
"""

import torch
import torch.nn as nn


class CropRecommendationNet(nn.Module):
    """Feedforward neural network for crop recommendation."""

    def __init__(self, input_dim: int = 7, num_classes: int = 22, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(dropout),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
