import numpy as np
from typing import Dict, List, Tuple
from app.engine.scoring import CUE_RANGES, sigmoid

def refit_logistic_model(
    current_weights: Dict[str, float],
    current_bias: float,
    prior_weights: Dict[str, float],
    training_data: List[Dict],
    lambda_reg: float = 0.5,
    learning_rate: float = 0.15,
    epochs: int = 40
) -> Tuple[Dict[str, float], float, float]:
    """
    Refits the biotic scoring model by minimizing regularized logistic loss:
    Loss = sum(logistic_loss(y_i, p_i)) + (lambda_reg / 2) * ||w - w0||^2
    - training_data: list of {'cues': dict, 'label': 1 for biotic, 0 for abiotic}
    - lambda_reg ensures the model does not overfit with only a handful of labels
      while visibly adjusting weights toward ground truth.
    Returns: (new_weights, new_bias, training_set_agreement_pct)
    """
    cue_keys = list(prior_weights.keys())
    w = np.array([current_weights[k] for k in cue_keys], dtype=np.float64)
    w0 = np.array([prior_weights[k] for k in cue_keys], dtype=np.float64)
    b = float(current_bias)

    if not training_data:
        return current_weights.copy(), current_bias, 100.0

    # Build feature matrix X and label vector Y
    X_rows = []
    Y_rows = []

    for row in training_data:
        cues = row["cues"]
        norm_vals = []
        for k in cue_keys:
            raw_v = cues.get(k, 0.0)
            rng = CUE_RANGES.get(k, 1.0)
            norm_vals.append(np.clip(raw_v / rng, -3.0, 3.0))
        X_rows.append(norm_vals)
        Y_rows.append(row["label"])

    X = np.array(X_rows, dtype=np.float64)
    Y = np.array(Y_rows, dtype=np.float64)
    N = len(Y)

    # Plain NumPy Gradient Descent
    for _ in range(epochs):
        z = np.dot(X, w) + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -15.0, 15.0)))
        error = p - Y

        # Gradients
        grad_w = (np.dot(X.T, error) / N) + lambda_reg * (w - w0)
        grad_b = np.sum(error) / N

        w -= learning_rate * grad_w
        b -= learning_rate * grad_b

    # Compute training set agreement
    z_final = np.dot(X, w) + b
    p_final = 1.0 / (1.0 + np.exp(-np.clip(z_final, -15.0, 15.0)))
    pred_classes = (p_final >= 0.5).astype(int)
    agreement = float(np.mean(pred_classes == Y)) * 100.0

    new_weights = {k: round(float(w[i]), 3) for i, k in enumerate(cue_keys)}
    return new_weights, round(b, 3), round(agreement, 1)

