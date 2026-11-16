# Stateful Lua iteration with Sol2

Return a C closure from `locations()` to keep this Lua loop while mixing C API callbacks with Sol2-bound methods:

```lua
for loc in celestia:getselection():locations() do
    celestia:log(loc:name())
end
```

Sol2 recognizes the exact signature `int(lua_State*)` as a raw C function. `main.cpp` binds `locations` that way and binds `getselection`, `name` and `log` as ordinary C++ methods. Both use the same real Lua state.

The closure stores two upvalues: the selection userdata and the next index. Each call yields a `Location` value, advances its own index and returns nil at exhaustion. It uses Lua's generic-for protocol directly, so it does not depend on `__pairs` or convert the collection into a table.

The key factory operation is:

```cpp
lua_pushvalue(state, 1); // the receiver from selection:locations()
lua_pushinteger(state, 0);
lua_pushcclosure(state, &next_location, 2);
return 1;
```

The complete callback and registration are in [main.cpp](main.cpp); [check.lua](check.lua) runs the whole workflow.

## Ownership and integration

This example returns a `std::shared_ptr<Selection>` from `getselection`. Retaining its Lua userdata keeps that owned selection alive. Each yielded `Location` is copied into Lua, so it remains usable after the iterator and selection are collected. The example collection is immutable.

The labels here point to static string literals. If your yielded type points to nonstatic storage, copying that type alone does not own the storage; copy the data or retain its owner as well.

Capturing userdata does not extend the lifetime of an external raw C++ pointee. If your existing binding returns raw pointers, preserve its real owner or ensure that owner and collection outlive every iterator. Decide separately what collection mutation should mean.

Raw C callbacks do not receive Sol2's usual C++ exception trampoline. The callbacks here perform checked type access, C API cursor operations and a trivial value copy; they report an invalid receiver with a Lua error. Handle throwing application operations before they can escape a raw callback. Ordinary C++ methods registered by Sol2 retain its normal handling.

`sol::state_view` provides bindings on an existing `lua_State*` without owning it. Keep the view and any Sol2 references inside the state's lifetime; the scope in `main.cpp` ends before `lua_close`.

## Build and run

Requires a C++17 compiler, a C compiler, make, curl and shasum. These commands use a temporary dependency directory and do not install globally. Run them from this example's directory in one shell:

```sh
sh -eu <<'BUILD'
ITERATOR_DEPS="$(mktemp -d)"
curl --fail --location https://www.lua.org/ftp/lua-5.4.9.tar.gz \
    --output "$ITERATOR_DEPS/lua-5.4.9.tar.gz"
curl --fail --location https://codeload.github.com/ThePhD/sol2/tar.gz/9190880c593dfb018ccf5cc9729ab87739709862 \
    --output "$ITERATOR_DEPS/sol2.tar.gz"

shasum -a 256 -c <<EOF
2335b6c582a52654f94612bf10d2f4672805d05329aa6568b1d8cd9e5c6fb8e6  $ITERATOR_DEPS/lua-5.4.9.tar.gz
f1d3dd8122e47ce6d1983c8455d044ccfe24a46939d66c076dcbf3e9b871a96d  $ITERATOR_DEPS/sol2.tar.gz
EOF

tar -xzf "$ITERATOR_DEPS/lua-5.4.9.tar.gz" -C "$ITERATOR_DEPS"
tar -xzf "$ITERATOR_DEPS/sol2.tar.gz" -C "$ITERATOR_DEPS"
make -C "$ITERATOR_DEPS/lua-5.4.9" generic
c++ -std=c++17 -O2 -Wall -Wextra -pedantic \
    -I"$ITERATOR_DEPS/sol2-9190880c593dfb018ccf5cc9729ab87739709862/include" \
    -I"$ITERATOR_DEPS/lua-5.4.9/src" \
    main.cpp "$ITERATOR_DEPS/lua-5.4.9/src/liblua.a" -lm \
    -o "$ITERATOR_DEPS/iterator-example"
"$ITERATOR_DEPS/iterator-example" check.lua
BUILD
```

The Sol2 commit is the target of tag **v3.5.0** and its headers report 3.5.0. Sol2's [latest published GitHub Release](https://github.com/ThePhD/sol2/releases/latest) separately lists v3.3.0. Lua **5.4.9** is a 5.4 maintenance release; this example does not claim support for the newer Lua 5.5 line.

Successful output:

```text
LIFETIME retained owner, released owner, retained yielded value
LUA complete: repeated loop, empty selection, exhaustion, independent cursors
LOG Alpha
LOG Beta
LOG Gamma
LOG Alpha
LOG Beta
LOG Gamma
HOST complete: 6 expected names, 0 live selections, balanced stack
VERSIONS Sol2 3.5.0, Lua 5.4.9
```

## What was verified

Native scripted execution passed on macOS 14.6 arm64 with Apple Clang 15, tagged Sol2 3.5.0 and Lua 5.4.9. The Lua checks cover owner retention through garbage collection, owner release, a yielded value surviving the selection, complete repeated loops, empty input, repeated exhaustion and interleaved independent cursors on the same selection. The C++ caller independently checks the exact logged names, a completion marker, zero remaining selections and a balanced stack.

Contained copies with cursor advancement, owner retention or host logging omitted each fail the corresponding acceptance check. The ownership control fails before dereferencing a missing owner.

This is a standalone fixture with synthetic names and the requested API shape. It has not been integrated into the original Celestia application, and no human manual validation, cross-version matrix or concurrent collection mutation is claimed.

## References

- [Sol2 raw C functions](https://github.com/ThePhD/sol2/blob/v3.5.0/documentation/source/functions.rst#raw-functions-lua_cfunction)
- [Sol2 public stack helpers](https://github.com/ThePhD/sol2/blob/v3.5.0/documentation/source/api/stack.rst)
- [Sol2 ownership](https://github.com/ThePhD/sol2/blob/v3.5.0/documentation/source/tutorial/ownership.rst)
- [Lua generic-for](https://www.lua.org/manual/5.4/manual.html#3.3.5) and [C closures](https://www.lua.org/manual/5.4/manual.html#lua_pushcclosure)
- [Sol2 license](https://github.com/ThePhD/sol2/blob/v3.5.0/LICENSE.txt) and [Lua license](https://www.lua.org/license.html)

## Optional coffee

The example is free under the MIT license. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
