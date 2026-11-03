# Reusable child messages in Miso

Give each child a function that adapts its own message into the parent's mailbox message type. The parent supplies that function when composing the children. Each child keeps its own message type and has no dependency on the parent module.

This example targets **Miso 1.14.0.0 in the browser/WASM**, with the default `Miso.JSON` codec (`aeson` Cabal flag disabled).

## Run the complete example

1. Open the [official Miso playground](https://try.haskell-miso.org/). Its compiler loads in the browser; the first load can take a while.
2. Replace the editor contents with the complete [Playground.hs](Playground.hs).
3. Click **Run**.
4. Click **Send A (7)**, **Send B (7)**, then **Send A (7)** again.

The parent should show A receipts **2**, B receipts **1**, and an ordered list **A7, B7, A7**. The children show their own send counts **2** and **1**. Both controls continue to work after the parent updates.

The displayed wire values are:

```json
{"tag":"A","contents":7}
{"tag":"B","contents":7}
```

Both bare child messages encode as `7`. The visible **checkMail round trips** result should be **PASS**.

Click **Send unknown tag**, then **Send bare MsgA**. The rejected-message count should become **2**, with an error message shown. Click **Send B (7)** again: B receipts should become **2**, while the rejected count stays **2**. An invalid payload does not stop later valid messages.

The rejection controls address the root's actual component ID through the public `mail` API. The payload reaches its mailbox through ordinary mail routing; the controls do not call the decode-error action directly.

## Keep the child reusable

[ChildA.hs](ChildA.hs) owns `MsgA`; its factory accepts an adapter:

```haskell
childA
  :: ToJSON message
  => (MsgA -> message)
  -> Component context () Int ActionA
```

The send handler does this:

```haskell
mailParent (toParent (MsgA 7))
```

`ChildA` knows only its own `MsgA` and the `ToJSON` constraint on the adapted result. A different parent can pass a different constructor or function. The function is a factory parameter captured by the handler; it is not a function-valued model or props field requiring an `Eq` instance.

[ChildB.hs](ChildB.hs) follows the same pattern with its own `MsgB`.

## Let the parent choose the envelope

[Main.hs](Main.hs) owns the union and derives its codec using `GHC.Generics` and `Miso.JSON`:

```haskell
data ParentMail = A MsgA | B MsgB
  deriving stock (Eq, Show, Generic)
  deriving anyclass (ToJSON, FromJSON)
```

It supplies the adapter when mounting each child:

```haskell
"child-a" +> childA A
"child-b" +> childB B
```

Its mailbox decodes the union and turns either outcome into a parent action:

```haskell
mailbox = checkMail Received Rejected
```

`Received (A message)` and `Received (B message)` then enter the ordinary parent update handler. `Rejected` handles an unknown tag or malformed payload.

Generic derives the encoder and decoder for the value actually passed to `mailParent`. It does not wrap a bare `MsgA` in `A` automatically. In this example `toJSON (MsgA 7)` and `toJSON (MsgB 7)` are identical, so a parent parser cannot reliably infer which child type a bare `7` meant. The explicit composition adapters give the wire message the necessary distinction.

If existing child formats are already distinguishable, a custom parent decoder is another option. Trying two overlapping decoders in order can silently choose the wrong one; it does not solve the ambiguous case shown here.

## Source layout

- `ChildA.hs` and `ChildB.hs` are reusable child modules. Neither imports `Main` or mentions `ParentMail`.
- `Main.hs` composes them and owns the union, parent model, mailbox and diagnostics.
- `Playground.hs` mechanically combines the same declaration bodies into one module for the playground's single editor. Its child and parent declarations match the separate sources.

For an existing Miso 1.14.0.0 browser project, copy the three separate modules and use its normal browser build. The example's entry point expects `<div id="app"></div>` in the page; adjust `mountPoint` to the host element your application uses.

The source imports only `base` and `miso`; state updates use the combinators re-exported by `Miso`. Browser/WASM is the scope of this example; the Lynx native mounting rules are different.

Both the combined file and the three separate modules were compiled and checked through software-operated browser checks in the official playground's GHC/WASM runtime with Miso 1.14.0.0. The checks covered A/B/A delivery, both rejected payloads, another valid B delivery afterward, and the displayed codec round trips. Removing the sender adapter, supplying the wrong adapters, or omitting the mailbox each made the receipt checks fail.

References: [stable JSON source](https://github.com/dmjio/miso/blob/1.14.0/src/Miso/JSON.hs), [stable mail and checkMail implementation](https://github.com/dmjio/miso/blob/1.14.0/src/Miso/Runtime.hs), [stable component and mounting API](https://github.com/dmjio/miso/blob/1.14.0/src/Miso/Types.hs).

## Optional coffee

The example is free. If it helps, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
