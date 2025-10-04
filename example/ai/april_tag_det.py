import time
import torch
import torch.nn as nn
import torch.nn.functional as F


# 1. MLP Model with Aggregated Features
class MLPClassifier(nn.Module):
    def __init__(self, input_dim):
        """
        Args:
            input_dim (int): Number of input features.
        """
        super(MLPClassifier, self).__init__()
        self.fc1 = nn.Linear(input_dim, 32)
        self.fc2 = nn.Linear(32, 16)
        self.fc3 = nn.Linear(16, 1)  # Final output (1 neuron for binary classification)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = torch.sigmoid(self.fc3(x))  # Sigmoid to output probability between 0 and 1
        return x


# 2. Lightweight 1D CNN Model for Temporal Sequence Input
class CNNClassifier(nn.Module):
    def __init__(self, window_size, feature_dim):
        """
        Args:
            window_size (int): Number of time steps (e.g., 5-10 frames).
            feature_dim (int): Number of features per time step.
        """
        super(CNNClassifier, self).__init__()
        # For Conv1d, input shape must be (batch_size, channels, sequence_length)
        self.conv1 = nn.Conv1d(
            in_channels=feature_dim, out_channels=16, kernel_size=3, padding=1
        )
        self.conv2 = nn.Conv1d(
            in_channels=16, out_channels=32, kernel_size=3, padding=1
        )
        # Global average pooling will collapse the sequence dimension
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.fc1 = nn.Linear(32, 16)
        self.fc2 = nn.Linear(16, 1)

    def forward(self, x):
        # x shape: (batch_size, window_size, feature_dim)
        # Permute to (batch_size, feature_dim, window_size) for Conv1d
        x = x.permute(0, 2, 1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = self.global_pool(x)  # Shape becomes (batch_size, 32, 1)
        x = x.view(x.size(0), -1)  # Flatten to (batch_size, 32)
        x = F.relu(self.fc1(x))
        x = torch.sigmoid(self.fc2(x))
        return x


# Example usage:
if __name__ == "__main__":
    # For the MLP model, assume we have 5 engineered features (e.g., x, y, delta_x, delta_y, confidence)
    mlp_input_dim = 5
    mlp_model = MLPClassifier(input_dim=mlp_input_dim)
    print("MLP Model Architecture:")
    print(mlp_model)

    # Create a dummy input for the MLP (batch_size=2, input_dim=5)
    dummy_mlp_input = torch.randn(2, mlp_input_dim)
    mlp_output = mlp_model(dummy_mlp_input)
    print("MLP output:", mlp_output)

    # For the CNN model, assume a window of 10 time steps with 5 features each
    window_size = 10
    feature_dim = 5
    cnn_model = CNNClassifier(window_size=window_size, feature_dim=feature_dim)
    print("\nCNN Model Architecture:")
    print(cnn_model)

    # Create a dummy input for the CNN (batch_size=2, window_size=10, feature_dim=5)
    dummy_cnn_input = torch.randn(2, window_size, feature_dim)
    start_time = time.time()
    cnn_output = cnn_model(dummy_cnn_input)
    end_time = time.time()
    print(f"CNN output: {cnn_output}")
    print(f"Time taken: {(end_time - start_time) * 1000} ms")
