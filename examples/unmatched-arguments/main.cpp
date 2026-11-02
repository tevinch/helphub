#include <cxxopts.hpp>

#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
  try
  {
    cxxopts::Options options("label-number", "Format a labelled integer.");
    options.add_options()
      ("l,label", "Label for the value", cxxopts::value<std::string>()->default_value("value"))
      ("n,number", "Integer to format", cxxopts::value<int>()->default_value("0"))
      ("h,help", "Print help");

    const auto result = options.parse(argc, argv);

    if (!result.unmatched().empty())
    {
      std::cerr << "Unexpected arguments:";
      for (const auto& argument : result.unmatched())
        std::cerr << ' ' << std::quoted(argument);
      std::cerr << '\n';
      return 2;
    }

    if (result.count("help") != 0)
    {
      std::cout << options.help();
      return 0;
    }

    std::cout << result["label"].as<std::string>() << ": "
              << result["number"].as<int>() << '\n';
    return 0;
  }
  catch (const cxxopts::exceptions::exception& error)
  {
    std::cerr << error.what() << '\n';
    return 2;
  }
}
