# Export weights trained in LibTorch to ONNX

This example starts with a network trained in C++, keeps its trained weights, and exports an equivalent Python network to ONNX. Python does not retrain it.

The important distinction is between a checkpoint and an inference graph. A native `torch::nn::Module` checkpoint stores registered state; it does not describe an arbitrary C++ `forward` implementation for the Python exporter. Here, the small Python `Net` reproduces that computation explicitly. This is a worked bridge for the supplied network, not an automatic converter for arbitrary `.pt` files.

## Run the complete example

Use Linux, Python 3.12, a C++20 compiler and CMake 3.22 or later. The verification workflow uses Ubuntu 24.04 with GCC 13. PyTorch 2.15 requires C++20; the Python wheel supplies its matching LibTorch headers and libraries, so a separate LibTorch download is unnecessary.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.15.0
.venv/bin/python -m pip install -r requirements.txt

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$(.venv/bin/python -c 'import torch; print(torch.utils.cmake_prefix_path)')"
cmake --build build --parallel 1
./build/train weights.json checkpoint.pt

.venv/bin/python -m unittest discover -v
.venv/bin/python bridge.py weights.json model.onnx
```

The final files have distinct purposes:

| File | Contents |
| --- | --- |
| `checkpoint.pt` | The native C++ training checkpoint, saved and reloaded by LibTorch. |
| `weights.json` | Explicit tensor names, shapes and float32 values, plus C++ training and held-out inference results. |
| `model.onnx` | The exported inference graph with the trained weights included. |
| `model.verification.json` | Loss comparison, state tensor names, dependency versions and ONNX Runtime output error. |

## What crosses the language boundary

`train.cpp` trains a `Linear(2, 4) → ReLU → Linear(4, 1)` network with SGD. It then saves and restores the native checkpoint before collecting its registered parameters and buffers. The JSON writer uses `max_digits10` and a decimal point, preserving finite float32 values, including negative zero, when read back as float32.

`bridge.py` defines the same registered names and forward computation:

```python
class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(2, 4)
        self.fc2 = nn.Linear(4, 1)

    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))
```

It checks the complete set of tensor names, each shape and dtype, then calls `load_state_dict(..., strict=True)`. It also checks that the loaded tensors equal the serialized tensors. An unknown, missing, duplicated, malformed or unsupported tensor fails the load instead of leaving random initialization in place.

The export itself uses the documented Python exporter:

```python
program = torch.onnx.export(
    model,
    (inputs,),
    dynamo=True,
    input_names=["input"],
    output_names=["output"],
    dynamic_shapes={"x": {0: torch.export.Dim("batch", min=1)}},
    opset_version=18,
)
program.save("model.onnx", external_data=False)
```

The checks compare the restored model with C++ inference on six inputs that were excluded from training. They then run ONNX's checker and compare ONNX Runtime CPU inference with those C++ results at batch sizes 1, 3 and 6. The loss and initial/final tensor comparison establish that the exported state came after C++ optimization. Negative controls reject missing tensors, duplicate names, wrong shapes and unsupported dtypes; a modified output bias must fail the C++ inference comparison.

## Adapting it to your model

1. Recreate the actual C++ `forward` computation in a Python `nn.Module`, including activation order, preprocessing and tensor layout. Matching layer names alone does not establish equivalent behavior.
2. Export all registered parameters **and buffers**, preserving their original names, shapes and dtypes. This tiny JSON writer deliberately supports only finite float32 tensors. It rejects other dtypes rather than casting them; it needs extending for integer buffers such as BatchNorm's `num_batches_tracked`.
3. Use inference mode consistently: call `eval()` on both models, supply representative inputs, and compare their outputs before attempting ONNX export.
4. Choose an ONNX opset and dynamic dimensions appropriate to the deployment runtime, then compare that runtime's outputs with the original C++ model. Custom C++ operators and data-dependent control flow may require additional export work.

JSON keeps this small example easy to inspect. It is inefficient for large models; use a suitable tensor container or binary representation with explicit metadata for production-sized weights. This example neither recovers an unknown architecture from a checkpoint nor converts optimizer state into an inference graph.

Official references: [C++ saving and loading](https://docs.pytorch.org/cppdocs/api/serialize/save_load.html), [C++ frontend](https://docs.pytorch.org/cppdocs/frontend), [Python state dictionaries](https://docs.pytorch.org/docs/stable/notes/serialization#saving-and-loading-torch-nn-modules), and [ONNX export](https://docs.pytorch.org/docs/stable/onnx).

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It's entirely optional; the example is free to use.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
