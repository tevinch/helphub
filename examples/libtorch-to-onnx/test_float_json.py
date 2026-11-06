"""Exercise the same standard-library stream configuration used by train.cpp."""

import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class FloatJsonTests(unittest.TestCase):
    def test_negative_zero_survives_cpp_json_python(self):
        compiler = shutil.which("c++")
        self.assertIsNotNone(compiler, "A C++20 compiler is required for this example")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "probe.cpp"
            executable = Path(directory) / "probe"
            source.write_text(
                '#include "json_float.h"\n#include <iostream>\n'
                'int main() { configure_float_json(std::cout); std::cout << -0.0f; }\n'
            )
            subprocess.run([compiler, "-std=c++20", "-I", str(Path(__file__).parent),
                            str(source), "-o", str(executable)], check=True,
                           capture_output=True, text=True)
            text = subprocess.check_output([str(executable)], text=True)
        parsed = json.loads(text)
        self.assertEqual(math.copysign(1.0, parsed), -1.0,
                         "The C++ formatter must keep negative zero through JSON decoding")


if __name__ == "__main__":
    unittest.main()
