import 'dart:js_interop';

typedef PrimitiveCallback = String Function(String label, int amount);
typedef PersonCallback = Person Function(Person person);

extension type Person._(JSObject _) implements JSObject {
  external factory Person({required String name, required int age});
  external String get name;
  external int get age;
}

@JS('typedFunctions.primitive')
external set primitive(JSFunction<PrimitiveCallback> callback);

@JS('typedFunctions.person')
external set person(JSFunction<PersonCallback> callback);

@JS('typedFunctions.repeat')
external set repeat(JSFunction<void Function()> callback);

// This function originates in JavaScript. Its T describes its signature;
// callAsFunction still needs explicit JS values and return conversion.
@JS('typedFunctions.format')
external JSFunction<JSString Function(JSString)> get formatter;

@JS('typedFunctions.runRound')
external void runHostRound(int round);

@JS('typedFunctions.recordRound')
external void recordRound(
  int round,
  int primitiveCalls,
  int personCalls,
  String formatted,
);

@JS('typedFunctions.ready')
external void ready();

int _round = 0;
int _primitiveCalls = 0;
int _personCalls = 0;

String describe(String label, int amount) {
  _primitiveCalls++;
  return '$label:${amount * 2}';
}

Person celebrate(Person input) {
  _personCalls++;
  return Person(name: input.name.toUpperCase(), age: input.age + 1);
}

void run() {
  _round++;
  runHostRound(_round);
  final result =
      formatter.callAsFunction(null, 'round$_round'.toJS) as JSString;
  recordRound(_round, _primitiveCalls, _personCalls, result.toDart);
}

void main() {
  // The exported Dart function retains its complete static function type.
  primitive = describe.toJS;
  person = celebrate.toJS;
  repeat = run.toJS;
  ready();
  run();
}
