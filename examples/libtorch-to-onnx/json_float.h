#pragma once

#include <iomanip>
#include <limits>
#include <locale>
#include <ostream>

inline void configure_float_json(std::ostream& out) {
    out.imbue(std::locale::classic());
    // A decimal point also keeps -0.0 a float in JSON readers that parse -0 as int.
    out << std::showpoint << std::setprecision(std::numeric_limits<float>::max_digits10);
}
