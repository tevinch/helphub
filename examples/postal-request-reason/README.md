# Tell a postal-field refresh from a validation request

One postal input can keep both triggers: refresh when the country changes, and validate when the user leaves the postal field. Add a small reason header in an external script using htmx's request configuration event.

This recipe requires the page to load the external listener script. It does not satisfy an attributes-only library that cannot require additional page JavaScript. The original requester confirmed the hook works under strict CSP, while clarifying that a built-in header is still needed for that library. See the [follow-up](https://github.com/bigskysoftware/htmx/issues/4161#issuecomment-6480569924).

The event APIs differ between the two pinned packages:

| Package | Configuration event | Original DOM event | Headers |
| --- | --- | --- | --- |
| 2.0.11 | htmx:configRequest | event.detail.triggeringEvent | event.detail.headers |
| 4.0.0 | htmx:config:request | event.detail.ctx.sourceEvent | event.detail.ctx.request.headers |

For example, the 4.0.0 listener in reason.js reads the original event, checks the requesting postal field, and sets X-Postal-Reason to refresh or validate. The 2.0.11 listener calls the same small function through its own API. Neither listener changes the form values or sends a second request.

The input retains its original trigger arrangement:

    <input id="postal_code" name="postal_code" data-postal
           hx-post="/postal"
           hx-trigger="focusout, input from:#country"
           hx-include="#country"
           hx-target="#postal-row" hx-swap="outerHTML">

The server uses the reason to decide which feedback to display. A country refresh updates the format hint without showing a required-field error. Postal focusout performs validation. Final form submission always validates the actual country and postal value; the header cannot make an invalid address save.

## Run

Requires Node.js 22 or newer.

    npm ci --ignore-scripts
    npm start

Open [the local form](http://127.0.0.1:3000/). Its links select either exact npm package. As checked on October 29, 2026, latest is 2.0.11 and next is 4.0.0; this example pins versions rather than those moving channel names.

Change the country from FR to CA. The empty postal field gets a Canadian-format hint without an error. Enter the postal field and leave it: the required message now appears. Enter K1A 0B1 and leave it again to clear the message. Change the country to FR, then enter 75001, add notes and save. The result displays the values the local server actually received.

The server returns a complete replacement table row, preserving the postal value. The external listeners remain on document through those replacements. There are no extra sibling elements next to a table row.

## Checks and scope

    npx playwright install chromium
    npm test

The Chromium check completes the refresh, empty/invalid/valid focusout, repeated row replacement and actual final POST on both packages. It checks request headers independently in browser network records and in the server's captured requests. It waits for each native swap to finish settling before the next interaction.

The example keeps a CSP with script-src 'self', without inline scripts, inline handlers, unsafe-eval, per-element nonces or a CSP extension. Optional built-in indicator styles are disabled through the respective configuration names. The normal workflow produces no CSP violations; separate inline-script and string-evaluation probes are then required to be blocked.

These are software-operated Chromium and local HTTP checks, not original-application or human manual validation. The field marker, country ID and two reason values are deliberately specific to this form. Adapt their selectors when integrating the listener. This is a native request-hook recipe, not a change to htmx's standard headers or a general event-serialization extension.

The small server only demonstrates two postal formats and displays a result. It does not verify real addresses or persist them.

See the official [2.x event reference](https://htmx.org/events/#htmx:configRequest) and [4.x request configuration event](https://four.htmx.org/reference/events/htmx-config-request).

## Optional coffee

This example is free. If it saved you some time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
