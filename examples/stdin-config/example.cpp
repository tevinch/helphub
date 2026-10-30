#include <CLI/CLI.hpp>
#include <iostream>

int main(int argc, char **argv) {
    CLI::App app{"Read configuration from a file or standard input"};
    int value = 10;
    int config_only = 20;
    int untouched = 30;

    // POSIX: /dev/stdin keeps input in CLI11's normal config-file processing.
    // Transformer leaves every other path unchanged.
    app.set_config("--config_file")->transform(CLI::Transformer({{"-", "/dev/stdin"}}));
    app.allow_config_extras(false);
    app.add_option("--value", value, "An integer from 0 to 100")
        ->envname("CLI11_CONFIG_EXAMPLE_VALUE")
        ->check(CLI::Range(0, 100));
    app.add_option("--config_only", config_only, "Another configurable integer");
    app.add_option("--untouched", untouched, "An integer left at its default in the example");

    // This is the application's completed operation, after all sources are read.
    app.callback([&] {
        std::cout << "{\"value\":" << value << ",\"config_only\":" << config_only
                  << ",\"untouched\":" << untouched << "}\n";
    });

    CLI11_PARSE(app, argc, argv);
}

