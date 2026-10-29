# Typed functions

`JSFunction<T>` takes a complete **function type**: return type plus parameter types. Dart primitives and `JSObject`-backed extension types can appear in that signature.

```dart
typedef PrimitiveCallback = String Function(String label, int amount);
typedef PersonCallback = Person Function(Person person);

extension type Person._(JSObject _) implements JSObject {
  external factory Person({required String name, required int age});
  external String get name;
  external int get age;
}
```

In [main.dart](main.dart), `describe.toJS` retains its `String Function(String, int)` type, so it fits `JSFunction<PrimitiveCallback>`. `celebrate.toJS` fits `JSFunction<PersonCallback>`. An unrelated ordinary Dart class cannot replace `Person` at this boundary.

JavaScript in [host.js](host.js) calls both callbacks with real values. The first run returns `batch1:6` and `{name: "PERSON1", age: 32}`. Click **Run again** for `batch2:8` and `{name: "PERSON2", age: 33}`; each host and Dart callback count reaches two.

## Run

Requires Dart **3.13.7**. There are no package dependencies.

```sh
dart pub get
dart analyze --fatal-infos
mkdir -p build
dart compile js -O1 -o build/main.js main.dart
python3 -m http.server --bind 127.0.0.1 8000
```

Open `http://127.0.0.1:8000/`. The page should show `PASS — 1 round`; after clicking **Run again**, it should show `PASS — 2 rounds` and both sets of results. Generated files are ignored by Git.

## JavaScript-origin functions

The example also retrieves a known JavaScript function as `JSFunction<JSString Function(JSString)>`. Its call still explicitly converts the argument with `.toJS`, states the expected JS result type and converts that result with `.toDart`:

```dart
final result = formatter.callAsFunction(null, 'round1'.toJS) as JSString;
final String text = result.toDart;
```

Here `null` is the JavaScript `this` argument. The result cast states the known API contract; it does not validate an arbitrary JavaScript value. `JSFunction`'s generic supplies static signature information, not JavaScript runtime checks or an automatically typed `callAsFunction`. An arbitrary JavaScript-origin `JSFunction` has no `.toDart` conversion to a Dart function. That conversion is available for `JSExportedDartFunction<T>` values created from Dart callbacks.

## Verification

Verified with the official checksum-matched Dart 3.13.7 SDK and software-operated Chromium 156. Strict raw-type analysis and JavaScript compilation passed. A callback with the wrong parameter list failed analysis. Two consecutive browser rounds checked the values above, separate host/Dart invocation counts and the visible result. Temporary variants omitting a binding or callback invocation failed the same acceptance checks.

These checks cover this JavaScript example. WebAssembly and the original application's migration were not tested.

References: [JSFunction](https://api.dart.dev/dart-js_interop/JSFunction-extension-type.html), [allowed boundary types](https://dart.dev/interop/js-interop/js-types#requirements-on-external-declarations-and-function-tojs), [toJS](https://api.dart.dev/dart-js_interop/FunctionToJSExportedDartFunction/toJS.html).

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
