"""LSTM yield prediction model definition.

A multi-layer LSTM with dropout for temporal crop yield forecasting.
Takes sequences of shape ``(batch, seq_len, input_size)`` and
outputs a single yield prediction per sequence.

This module contains only the model architecture — no training
logic, no data loading, no I/O.
"""

import torch.nn as nn


class LSTMYieldModel(nn.Module):
    """LSTM-based yield prediction model.

    Args:
        input_size: Number of features per timestep.
        hidden_size: LSTM hidden state dimension.
        num_layers: Number of stacked LSTM layers.
        dropout: Dropout between LSTM layers (ignored if
            ``num_layers == 1``).
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        num_layers: int,
        dropout: float,
    ) -> None:
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        """Forward pass.

        Args:
            x: Input tensor of shape ``(batch, seq_len, input_size)``.

        Returns:
            Yield predictions of shape ``(batch, 1)``.
        """
        lstm_out, _ = self.lstm(x)
        # Use the last timestep's hidden state
        last_hidden = lstm_out[:, -1, :]
        output = self.fc(last_hidden)
        return output
