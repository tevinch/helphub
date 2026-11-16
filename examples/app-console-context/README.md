# App console context

Open a local IRB console as a Ruby app subcommand, inspect and change its existing state, then return to the app with ordinary `exit`.

The native entry point is [`Binding#irb`](https://ruby.github.io/irb/Binding.html). Call it where the objects and local variables you want to inspect already exist:

```ruby
require "irb"

def console
  app = Counter.new(2)
  local_note = "ready"

  binding.irb(show_code: false)

  puts "Back in the app: #{app.value}, #{local_note}"
end
```

`show_code: false` only hides the source excerpt when the session opens. The binding still gives the session access to the caller's local context. Put the call in your own application's console-command handler; this example's `Counter` is just a small object to inspect.

[`IRB.start`](https://ruby.github.io/irb/IRB.html) starts with the top-level binding. For a console that needs a method's local objects, use that method's `binding.irb`. This example leaves `ARGV` intact and does not pass the app's flags to an IRB command-line parser.

## Run

Use Ruby 3.3 or later and Bundler. The lockfile pins IRB 1.19.0 and its dependencies. From this directory:

```sh
bundle config set --local path vendor/bundle
bundle install
bundle exec ruby app.rb status
bundle exec ruby app.rb console --keep demo
```

At the console, try:

```ruby
app.value                         # => 2
app.doubled                       # => 4
raise "unexpected" unless app.doubled == 4
app.add(3)
local_note = "edited"
ARGV                              # => ["console", "--keep", "demo"]
exit
```

The app then prints:

```text
RESUMED session=1 value=5 note=edited argv=["console", "--keep", "demo"]
COMPLETE value=5 note=edited argv=["console", "--keep", "demo"]
```

Use `exit` to leave this session and continue the caller. `exit!` ends the process. Only evaluate Ruby you intend to run in your local app.

To try returning and opening another session in the same process:

```sh
bundle exec ruby app.rb console --twice --keep demo
```

After the first `exit`, the second session sees the changed object and local variable. The `--keep demo` arguments simply demonstrate that ordinary app arguments remain available; they do not enable another feature.

## Verification

The test uses Python 3's standard-library PTY support on macOS or Linux to operate a real Ruby terminal session:

```sh
bundle exec python3 -m unittest discover -s test -v
```

It independently checks the displayed values, a manual method assertion, object and local-variable mutations, the caller's resumed output, a second usable session, the exact retained arguments, normal process exit, the default single-session command and the non-console `status` command. The terminal waits for prompts and checks result lines separately from echoed input.

The recorded run used Ruby 3.3.4, IRB 1.19.0 and Bundler 2.5.17 on macOS arm64: three tests passed. [example-session.txt](example-session.txt) contains the two-session transcript from that scripted terminal run. A control using the top-level binding failed because it could not inspect the method's local `app`.

The test supplies a temporary IRB configuration with history disabled, simple prompts and no color. It does not change personal IRB configuration. This verifies the local console workflow in this example; it does not establish compatibility with an unavailable original app, every framework, custom IRB configuration, line-editing behavior or other platforms. No human manual validation is claimed.

## Optional coffee

The example is free under the MIT license. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
