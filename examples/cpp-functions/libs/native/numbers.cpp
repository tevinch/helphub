#include <stdint.h>

extern "C" int32_t example_add(int32_t left, int32_t right) {
  return left + right;
}

extern "C" int32_t example_twice(int32_t value) {
  return value * 2;
}
