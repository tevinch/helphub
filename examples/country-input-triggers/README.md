# Country input triggers across htmx versions

When country radio buttons live inside a known container, listen for their bubbling `input` events on that container. The city field can use the same trigger in htmx 2.0.11 and 4.0.0:

```html
<ul data-source="city">
  <li><label><input type="radio" name="country" value="fr"> France</label></li>
  <li><label><input type="radio" name="country" value="de"> Germany</label></li>
</ul>

<select name="city"
        hx-post="/cities/city"
        hx-trigger="input from:[data-source~=city]"
        hx-swap="outerHTML">
  <option value="">Choose a city</option>
</select>
```

This avoids the differing syntax for a `target:` selector containing spaces. The listener attaches to the matching `<ul>`; `input` events from its nested radios bubble there. Inputs outside that container do not reach the listener. `~=` matches a token in the `data-source` attribute.

The runnable example puts these fields inside a form, so htmx includes its form values in each POST. If your fields have a different form arrangement, configure the submitted values for that arrangement as well. The server returns a replacement city select with the same trigger and updated options. A second field group demonstrates that the destination and shipping controls stay separate.

## Run

Requires Node.js 22 or newer.

```sh
npm ci --ignore-scripts
npm start
```

Open [the local example](http://127.0.0.1:3000/). Its two links load the exact htmx 2.0.11 and 4.0.0 npm artifacts, served locally. As checked on October 28, 2026, npm's `latest` channel points to 2.0.11 and its `next` channel points to 4.0.0. The example pins both; it does not use a moving channel tag.

Choose a destination country and city, enter notes, then change the country again. Only that group's city options reload. Choose a shipping destination, edit the other field, and submit the form to see the values actually received by the local server. This teaching server displays the submission and keeps its request log in memory.

## Checks and boundaries

```sh
npx playwright install chromium
npm test
```

The Chromium check runs the complete form workflow on both versions. It verifies real HTTP requests, returned options, independent field groups, unrelated edits, repeated updates, a nested radio added to an existing source container, retained notes, and the final submitted values. The page uses a Content Security Policy without `unsafe-eval`, inline scripts, or inline event handlers. The optional htmx 2 indicator stylesheet is disabled in its configuration so the page can keep `style-src 'self'` too.

These are software-operated browser checks, not confirmation from the original application or its user.

`from:` resolves its source elements when the receiving field is initialized. Keep the source container mounted. New children inside that container work through bubbling; replacing the entire container is different. If your page replaces it, replace the receiving field as part of that render too so it binds to the new source. Events stopped before reaching the container will not trigger a request. Keep each source token scoped to the field group you intend to update.

The example covers this input-source pattern. It does not translate other attributes or event APIs between htmx versions.

See the official [`hx-trigger` documentation](https://htmx.org/attributes/hx-trigger/) and the [htmx package versions](https://www.npmjs.com/package/htmx.org?activeTab=versions).

## Optional coffee

This example is free. If it saved you some time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
