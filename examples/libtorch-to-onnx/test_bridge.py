"""Consumer checks: strict state mapping and the original C++ output contract."""

import copy
import unittest


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "format": "libtorch-float32-v1",
            "architecture": "linear2-relu4-linear1",
            "state": [
                {"name": "fc1.weight", "dtype": "float32", "shape": [4, 2],
                 "data": [1, 0, 0, 1, -1, 0, 0, -1]},
                {"name": "fc1.bias", "dtype": "float32", "shape": [4], "data": [0, 0, 0, 0]},
                {"name": "fc2.weight", "dtype": "float32", "shape": [1, 4], "data": [2, 3, -2, -3]},
                {"name": "fc2.bias", "dtype": "float32", "shape": [1], "data": [0.5]},
            ],
            "checks": {
                "input": [[1, 2], [-1, 2], [0, -2], [1, -2]],
                "output": [[8.5], [4.5], [-5.5], [-3.5]],
            },
        }

    def bridge(self):
        import bridge
        return bridge

    def test_preserves_named_weights_and_inference(self):
        bridge = self.bridge()
        model = bridge.load_model(self.payload)
        self.assertEqual(set(model.state_dict()), {item["name"] for item in self.payload["state"]})
        bridge.check_cpp_outputs(model, self.payload)

    def test_returns_cpp_reference_even_when_python_differs_within_tolerance(self):
        bridge = self.bridge()
        self.payload["checks"]["output"][0][0] = 8.50002
        model = bridge.load_model(self.payload)
        _, reference = bridge.check_cpp_outputs(model, self.payload)
        # This slight C++/Python difference is accepted by the parity tolerance.
        # The later ONNX Runtime check must retain the independent C++ reference.
        self.assertEqual(reference[0, 0].item(),
                         bridge.torch.tensor(8.50002, dtype=bridge.torch.float32).item())

    def test_missing_weight_is_rejected(self):
        bridge = self.bridge()
        self.payload["state"].pop()
        with self.assertRaisesRegex(ValueError, "names"):
            bridge.load_model(self.payload)

    def test_wrong_shape_is_rejected(self):
        bridge = self.bridge()
        self.payload["state"][0]["shape"] = [2, 4]
        with self.assertRaisesRegex(ValueError, "shape"):
            bridge.load_model(self.payload)

    def test_duplicate_weight_is_rejected(self):
        bridge = self.bridge()
        self.payload["state"].append(copy.deepcopy(self.payload["state"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            bridge.load_model(self.payload)

    def test_modified_weight_fails_cpp_parity(self):
        bridge = self.bridge()
        self.payload["state"][-1]["data"][0] += 1
        model = bridge.load_model(self.payload)
        with self.assertRaises(AssertionError):
            bridge.check_cpp_outputs(model, self.payload)

    def test_unsupported_dtype_is_rejected(self):
        bridge = self.bridge()
        self.payload["state"][0]["dtype"] = "float64"
        with self.assertRaisesRegex(ValueError, "dtype"):
            bridge.load_model(self.payload)


if __name__ == "__main__":
    unittest.main()
