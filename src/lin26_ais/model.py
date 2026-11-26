"""Load JSON gradient-boosting models and predict using NumPy.

Float32 inputs and ordered float64 sums match scikit-learn predictions.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

FORMAT = "lin26-ais-gradient-boosting"
FORMAT_VERSION = 1


def _number(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not np.isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


class GradientBoostingModel:
    """Gradient-boosting regressor loaded from JSON."""

    @classmethod
    def load(cls, path: Path) -> GradientBoostingModel:
        with Path(path).open(encoding="utf-8") as stream:
            return cls(json.load(stream))

    def __init__(self, document: dict):
        if (
            not isinstance(document, dict)
            or document.get("format") != FORMAT
            or type(document.get("format_version")) is not int
            or document["format_version"] != FORMAT_VERSION
        ):
            raise ValueError("Unsupported JSON model format or version")
        if (
            document.get("input_dtype") != "float32"
            or document.get("accumulation_dtype") != "float64"
            or document.get("comparison") != "less_equal"
        ):
            raise ValueError("Unsupported JSON model prediction conventions")
        names = document.get("feature_names")
        if (
            not isinstance(names, list)
            or not names
            or not all(isinstance(name, str) and name for name in names)
            or len(set(names)) != len(names)
        ):
            raise ValueError("JSON model requires unique, non-empty feature names")
        self.feature_names_in_ = np.asarray(names)
        self.learning_rate = _number(document.get("learning_rate"), "learning_rate")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        self.initial_prediction = _number(
            document.get("initial_prediction"), "initial_prediction"
        )
        trees = document.get("trees")
        if not isinstance(trees, list) or not trees:
            raise ValueError("JSON model requires at least one tree")

        left, right, features, thresholds, values, roots = [], [], [], [], [], []
        self._max_depth = 0
        offset = 0
        for tree in trees:
            if not isinstance(tree, dict):
                raise TypeError("Each JSON tree must be an object")
            arrays = [
                tree.get(key)
                for key in (
                    "children_left",
                    "children_right",
                    "feature",
                    "threshold",
                    "value",
                )
            ]
            if (
                not all(isinstance(array, list) and array for array in arrays)
                or len({len(array) for array in arrays}) != 1
            ):
                raise ValueError("Tree node arrays must have equal, non-zero lengths")
            lchild, rchild, feature, threshold, value = arrays
            count = len(lchild)
            if any(type(item) is not int for array in arrays[:3] for item in array):
                raise ValueError("Tree children and features must be integers")
            for item in threshold:
                _number(item, "threshold")
            for item in value:
                _number(item, "value")

            # Each node must be reachable exactly once from the root.
            visited = set()
            pending = [(0, 0)]
            while pending:
                node, depth = pending.pop()
                if not 0 <= node < count or node in visited:
                    raise ValueError(
                        "Tree must be rooted at node 0 without cycles or shared nodes"
                    )
                visited.add(node)
                self._max_depth = max(self._max_depth, depth)
                if lchild[node] == rchild[node] == -1:
                    if feature[node] != -2:
                        raise ValueError("Leaf feature must be -2")
                else:
                    if (
                        not 0 <= feature[node] < len(names)
                        or not 0 <= lchild[node] < count
                        or not 0 <= rchild[node] < count
                    ):
                        raise ValueError("Invalid split feature or child index")
                    pending.extend(
                        ((lchild[node], depth + 1), (rchild[node], depth + 1))
                    )
            if len(visited) != count:
                raise ValueError("Tree contains unreachable nodes")

            roots.append(offset)
            # Keep leaf nodes fixed during vectorized traversal.
            left.extend(
                offset + (i if child == -1 else child) for i, child in enumerate(lchild)
            )
            right.extend(
                offset + (i if child == -1 else child) for i, child in enumerate(rchild)
            )
            features.extend(max(index, 0) for index in feature)
            thresholds.extend(threshold)
            values.extend(value)
            offset += count
        self._roots = np.asarray(roots, dtype=np.int64)
        self._left = np.asarray(left, dtype=np.int64)
        self._right = np.asarray(right, dtype=np.int64)
        self._features = np.asarray(features, dtype=np.int64)
        self._thresholds = np.asarray(thresholds, dtype=np.float64)
        self._values = np.asarray(values, dtype=np.float64)

    def predict(self, data) -> np.ndarray:
        """Predict rows whose columns follow the stored feature order."""
        if hasattr(data, "columns") and list(data.columns) != list(
            self.feature_names_in_
        ):
            raise ValueError(
                "Prediction columns must match the JSON model's feature order"
            )
        with np.errstate(over="ignore", invalid="ignore"):
            inputs = np.asarray(data, dtype=np.float32)
        if inputs.ndim != 2 or inputs.shape[1] != len(self.feature_names_in_):
            raise ValueError("Prediction input has an invalid feature dimension")
        if not np.isfinite(inputs).all():
            raise ValueError(
                "Prediction inputs must be finite after float32 conversion"
            )
        prediction = np.empty(len(inputs), dtype=np.float64)
        for start in range(0, len(inputs), 2048):
            batch = inputs[start : start + 2048]
            nodes = np.broadcast_to(self._roots, (len(batch), len(self._roots)))
            rows = np.arange(len(batch))[:, None]
            for _ in range(self._max_depth):
                go_left = batch[rows, self._features[nodes]] <= self._thresholds[nodes]
                nodes = np.where(go_left, self._left[nodes], self._right[nodes])
            contributions = self._values[nodes] * self.learning_rate
            contributions[:, 0] += self.initial_prediction
            prediction[start : start + len(batch)] = np.cumsum(contributions, axis=1)[
                :, -1
            ]
        return prediction
