#define SOL_ALL_SAFETIES_ON 1
#include <sol/sol.hpp>

#include <array>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

struct Location {
    const char* label;

    const char* name() const noexcept {
        return label;
    }
};

struct Selection {
    static inline int live = 0;
    const std::array<Location, 3> items{{{"Alpha"}, {"Beta"}, {"Gamma"}}};
    const int count;

    explicit Selection(int size) noexcept : count(size) {
        ++live;
    }

    Selection(const Selection&) = delete;
    Selection& operator=(const Selection&) = delete;

    ~Selection() noexcept {
        --live;
    }
};

int next_location(lua_State* state) {
    auto owner = sol::stack::check_get<Selection*>(state, lua_upvalueindex(1));
    if (!owner || !*owner) {
        return luaL_error(state, "iterator has no selection owner");
    }

    const Selection& selection = **owner;
    const lua_Integer index = lua_tointeger(state, lua_upvalueindex(2));
    if (index < 0 || index >= selection.count) {
        lua_pushnil(state);
        return 1;
    }

    lua_pushinteger(state, index + 1);
    lua_replace(state, lua_upvalueindex(2));
    return sol::stack::push(state, Location{selection.items[static_cast<std::size_t>(index)].label});
}

int locations(lua_State* state) {
    if (!sol::stack::check<Selection*>(state, 1)) {
        return luaL_error(state, "locations expects a Selection receiver");
    }

    // Retain the Lua-owned selection, not an unowned C++ pointer.
    lua_pushvalue(state, 1);
    lua_pushinteger(state, 0);
    lua_pushcclosure(state, &next_location, 2);
    return 1;
}

struct Catalog {
    std::vector<std::string> log_entries;

    std::shared_ptr<Selection> getselection() const {
        return std::make_shared<Selection>(3);
    }

    std::shared_ptr<Selection> getemptyselection() const {
        return std::make_shared<Selection>(0);
    }

    void log(const char* label) {
        log_entries.emplace_back(label);
    }
};

int main(int argc, char* argv[]) {
    Catalog catalog;
    std::unique_ptr<lua_State, decltype(&lua_close)> state(luaL_newstate(), &lua_close);
    if (!state) {
        std::cerr << "Cannot create Lua state\n";
        return 1;
    }

    {
        // This view shares the existing C API state and must die before lua_close.
        sol::state_view lua(state.get());
        lua.open_libraries(sol::lib::base, sol::lib::table, sol::lib::string);
        lua.new_usertype<Location>("Location", sol::no_constructor, "name", &Location::name);
        lua.new_usertype<Selection>("Selection", sol::no_constructor, "locations", &locations);
        lua.new_usertype<Catalog>("Catalog", sol::no_constructor,
            "getselection", &Catalog::getselection,
            "getemptyselection", &Catalog::getemptyselection,
            "log", &Catalog::log);
        lua["celestia"] = &catalog;

        const int stack_before = lua_gettop(state.get());
        {
            auto result = lua.safe_script_file(argc > 1 ? argv[1] : "check.lua", sol::script_pass_on_error);
            if (!result.valid()) {
                const sol::error error = result;
                std::cerr << error.what() << '\n';
                return 1;
            }
        }

        const sol::optional<bool> complete = lua["workflow_complete"];
        const std::vector<std::string> expected{"Alpha", "Beta", "Gamma", "Alpha", "Beta", "Gamma"};
        if (!complete.value_or(false) || catalog.log_entries != expected || Selection::live != 0
            || lua_gettop(state.get()) != stack_before) {
            std::cerr << "Host verification failed: completion, log values, owner cleanup or stack balance\n";
            return 1;
        }

        for (const auto& label : catalog.log_entries) {
            std::cout << "LOG " << label << '\n';
        }
        std::cout << "HOST complete: 6 expected names, 0 live selections, balanced stack\n";
        std::cout << "VERSIONS Sol2 " << SOL_VERSION_STRING << ", " << LUA_RELEASE << '\n';
    }

    return 0;
}
