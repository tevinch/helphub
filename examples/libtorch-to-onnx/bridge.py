"""Load this example's explicit tensor data, then use the Python ONNX exporter."""

import argparse
import json
import math
from pathlib import Path

import torch
from torch import nn


class Net(nn.Module):
    """The same forward computation and registered names as train.cpp."""

    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(2, 4)
        self.fc2 = nn.Linear(4, 1)

    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))


def load_model(payload):
    if payload.get("format") != "libtorch-float32-v1":
        raise ValueError("Unsupported tensor format")
    if payload.get("architecture") != "linear2-relu4-linear1":
        raise ValueError("This example requires its matching Python architecture")
    model = Net().eval()
    expected = model.state_dict()
    state = {}
    for item in payload["state"]:
        name = item["name"]
        if name in state:
            raise ValueError(f"Duplicate tensor name: {name}")
        if name not in expected:
            raise ValueError(f"Unexpected tensor names: {name}")
        if item["dtype"] != "float32":
            raise ValueError(f"Unsupported dtype for {name}; this example accepts float32 only")
        shape = item["shape"]
        if shape != list(expected[name].shape):
            raise ValueError(f"Wrong shape for {name}: {shape}")
        values = item["data"]
        if len(values) != expected[name].numel():
            raise ValueError(f"Wrong data length for {name}")
        if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
            raise ValueError(f"Non-finite or non-numeric data for {name}")
        tensor = torch.tensor(values, dtype=torch.float32).reshape(shape)
        if not torch.isfinite(tensor).all():
            raise ValueError(f"Float32 overflow for {name}")
        state[name] = tensor
    if set(state) != set(expected):
        raise ValueError("Tensor names do not match the model's complete state_dict")
    model.load_state_dict(state, strict=True)
    for name, value in model.state_dict().items():
        if not torch.equal(value, state[name]):
            raise AssertionError(f"Loaded tensor changed: {name}")
    return model


def check_cpp_outputs(model, payload):
    inputs = torch.tensor(payload["checks"]["input"], dtype=torch.float32)
    expected = torch.tensor(payload["checks"]["output"], dtype=torch.float32)
    with torch.no_grad():
        actual = model(inputs)
    torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)
    return inputs, expected


def check_training(model, payload):
    training = payload["training"]
    initial = load_model({**payload, "state": training["initial_state"]})
    inputs = torch.tensor(training["input"], dtype=torch.float32)
    target = torch.tensor(training["target"], dtype=torch.float32)
    with torch.no_grad():
        initial_loss = nn.functional.mse_loss(initial(inputs), target).item()
        final_loss = nn.functional.mse_loss(model(inputs), target).item()
    assert initial_loss > final_loss, "The C++ training must reduce the loss"
    assert training["steps"] > 0, "No C++ optimization steps were recorded"
    assert math.isclose(initial_loss, training["initial_loss"], rel_tol=1e-5, abs_tol=1e-6)
    assert math.isclose(final_loss, training["final_loss"], rel_tol=1e-5, abs_tol=1e-6)
    changed = [name for name, tensor in model.state_dict().items()
               if not torch.equal(tensor, initial.state_dict()[name])]
    assert changed, "The final state must differ from the untrained C++ state"
    return {"initial_loss": initial_loss, "final_loss": final_loss, "changed_tensors": changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("weights", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.weights.read_text())
    model = load_model(payload)
    inputs, cpp_reference = check_cpp_outputs(model, payload)
    training = check_training(model, payload)

    # Keep the training checkpoint separate from the exported inference graph.
    # Python only restores the C++ tensors; it never runs an optimizer.
    program = torch.onnx.export(
        model,
        (inputs,),
        dynamo=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_shapes={"x": {0: torch.export.Dim("batch", min=1)}},
        opset_version=18,
    )
    program.save(args.output, external_data=False)

    import numpy as np
    import onnx
    import onnxruntime as ort

    onnx.checker.check_model(str(args.output), full_check=True)
    session = ort.InferenceSession(str(args.output), providers=["CPUExecutionProvider"])
    max_error = 0.0
    # Three batch lengths exercise the actual exported dynamic batch dimension.
    for batch in (1, 3, len(inputs)):
        actual = session.run(["output"], {"input": inputs[:batch].numpy()})[0]
        expected = cpp_reference[:batch].numpy()
        np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-6)
        max_error = max(max_error, float(np.max(np.abs(actual - expected))))

    result = {
        "torch": torch.__version__, "onnx": onnx.__version__, "onnxruntime": ort.__version__,
        "state_tensors": list(model.state_dict()), "training": training,
        "held_out_rows": len(inputs), "batch_sizes": [1, 3, len(inputs)],
        "max_absolute_error_vs_cpp": max_error,
        "onnx_checker": "passed", "python_retraining": False,
    }
    args.output.with_suffix(".verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
