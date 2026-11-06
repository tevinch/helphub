#include <torch/torch.h>
#include "json_float.h"

#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

struct NetImpl : torch::nn::Module {
    NetImpl() {
        fc1 = register_module("fc1", torch::nn::Linear(2, 4));
        fc2 = register_module("fc2", torch::nn::Linear(4, 1));
    }
    torch::Tensor forward(torch::Tensor x) {
        return fc2->forward(torch::relu(fc1->forward(x)));
    }
    torch::nn::Linear fc1{nullptr}, fc2{nullptr};
};
TORCH_MODULE(Net);

using State = std::vector<std::pair<std::string, torch::Tensor>>;

State snapshot(const Net& model) {
    State state;
    for (const auto& item : model->named_parameters()) {
        state.emplace_back(item.key(), item.value().detach().cpu().contiguous().clone());
    }
    // No buffers in this small network, but never silently omit registered ones.
    for (const auto& item : model->named_buffers()) {
        state.emplace_back(item.key(), item.value().detach().cpu().contiguous().clone());
    }
    return state;
}

void write_string(std::ostream& out, const std::string& value) {
    const char* hex = "0123456789abcdef";
    out << '"';
    for (const unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c < 0x20) out << "\\u00" << hex[c >> 4] << hex[c & 15];
        else out << c;
    }
    out << '"';
}

void write_values(std::ostream& out, const torch::Tensor& source) {
    const auto tensor = source.detach().cpu().contiguous().flatten();
    if (tensor.scalar_type() != torch::kFloat32) {
        throw std::runtime_error("This example exports float32 tensors only");
    }
    const float* data = tensor.data_ptr<float>();
    out << '[';
    for (int64_t i = 0; i < tensor.numel(); ++i) {
        if (!std::isfinite(data[i])) throw std::runtime_error("Non-finite tensor value");
        if (i) out << ',';
        out << data[i];
    }
    out << ']';
}

void write_matrix(std::ostream& out, const torch::Tensor& matrix) {
    if (matrix.dim() != 2) throw std::runtime_error("Expected a matrix");
    out << '[';
    for (int64_t row = 0; row < matrix.size(0); ++row) {
        if (row) out << ',';
        write_values(out, matrix[row]);
    }
    out << ']';
}

void write_state(std::ostream& out, const State& state) {
    out << '[';
    for (size_t i = 0; i < state.size(); ++i) {
        if (i) out << ',';
        const auto& [name, tensor] = state[i];
        out << "{\"name\":";
        write_string(out, name);
        out << ",\"dtype\":\"float32\",\"shape\":[";
        for (int64_t dim = 0; dim < tensor.dim(); ++dim) {
            if (dim) out << ',';
            out << tensor.size(dim);
        }
        out << "],\"data\":";
        write_values(out, tensor);
        out << '}';
    }
    out << ']';
}

int main(int argc, char* argv[]) {
    try {
        if (argc != 3) throw std::runtime_error("Usage: train weights.json checkpoint.pt");
        torch::manual_seed(17);
        torch::set_num_threads(1);
        Net model;
        const auto input = torch::tensor({{-1.0f, -1.0f}, {-1.0f, 1.0f},
            {0.0f, -1.0f}, {0.0f, 1.0f}, {1.0f, -1.0f}, {1.0f, 1.0f},
            {0.5f, 0.25f}, {-0.5f, -0.25f}});
        const auto target = (input.select(1, 0) * 1.5f - input.select(1, 1) * 0.75f + 0.2f).unsqueeze(1);
        const auto initial_state = snapshot(model);
        const float initial_loss = torch::mse_loss(model->forward(input), target).item<float>();
        torch::optim::SGD optimizer(model->parameters(), torch::optim::SGDOptions(0.03));
        constexpr int steps = 300;
        model->train();
        for (int step = 0; step < steps; ++step) {
            optimizer.zero_grad();
            const auto loss = torch::mse_loss(model->forward(input), target);
            loss.backward();
            optimizer.step();
        }
        model->eval();
        torch::NoGradGuard no_grad;
        const float final_loss = torch::mse_loss(model->forward(input), target).item<float>();
        if (!(final_loss < initial_loss)) throw std::runtime_error("C++ training did not improve loss");
        const auto final_state = snapshot(model);
        torch::save(model, argv[2]);
        // Reload the native trained checkpoint and use that model for the bridge.
        Net restored;
        torch::load(restored, argv[2]);
        restored->eval();
        const auto held_out = torch::tensor({{-2.0f, 0.5f}, {2.0f, -0.5f},
            {0.25f, -0.75f}, {-0.25f, 0.75f}, {0.8f, 0.4f}, {-0.8f, -0.4f}});
        const auto reference = model->forward(held_out);
        const auto restored_output = restored->forward(held_out);
        if (!torch::equal(reference, restored_output)) throw std::runtime_error("Native checkpoint round trip changed output");

        std::ofstream out(argv[1]);
        out.exceptions(std::ios::failbit | std::ios::badbit);
        configure_float_json(out);
        out << "{\"format\":\"libtorch-float32-v1\",\"architecture\":\"linear2-relu4-linear1\",\"state\":";
        write_state(out, snapshot(restored));
        out << ",\"training\":{\"steps\":" << steps << ",\"initial_loss\":" << initial_loss
            << ",\"final_loss\":" << final_loss << ",\"initial_state\":";
        write_state(out, initial_state);
        out << ",\"input\":";
        write_matrix(out, input);
        out << ",\"target\":";
        write_matrix(out, target);
        out << "},\"checks\":{\"input\":";
        write_matrix(out, held_out);
        out << ",\"output\":";
        write_matrix(out, restored_output);
        out << "}}\n";
        out.close();
        std::cout << "Native checkpoint restored; C++ SGD loss " << initial_loss
                  << " -> " << final_loss << "; exported " << final_state.size() << " state tensors\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
