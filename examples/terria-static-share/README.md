# Share a map from a static TerriaMap site

TerriaMap can put the current camera and active layers into a `#start=…` fragment. This lets people open the same view on a static host such as GitHub Pages. The normal **Share / Print** panel can generate the link without a link-shortening service.

## Configure an existing map

1. Copy [`init/static-share.json`](init/static-share.json) into your site's `wwwroot/init/` directory. Append `"static-share"` to the `initializationUrls` array in `wwwroot/config.json`, after your existing initialization sources. `settings.shortenShareUrls` belongs in the initialization file. It sets the browser's TerriaMap preference when the file loads, including for visitors who previously enabled shortening.
2. Copy [`static-server-config.json`](static-server-config.json) into `wwwroot/`. In `config.json` under `parameters`, set `"serverConfigUrl": "static-server-config.json"` and leave `shareUrl` at its default, `"share"`. A `null` server config URL falls back to `serverconfig/`. The static JSON file contains `{}` and advertises no shortening service.
3. If the site lives under a project path, set the HTML base to that path when building the map. For example, from the TerriaMap v0.4.8 checkout run `yarn gulp release --baseHref=/my-map/` with dependencies already installed, then publish `wwwroot/` at `/my-map/`. The trailing slash makes the map assets, static JSON files and share links resolve under the same path.
4. Open **Share / Print** and click **Copy**. Open the `#start=…` link in a fresh browser window at the same site and check that your map view comes back.

Keep your existing catalog and other configuration. The sample files include a separate local catalog for trying these steps without an external basemap.

[TerriaJS initialization file reference](https://docs-v8.terria.io/guide/customizing/initialization-files/#settings) · [TerriaMap static deployment guide](https://docs-v8.terria.io/guide/deploying/deploying-terriamap/) · [TerriaMap 0.4.8 build options](https://github.com/TerriaJS/TerriaMap/blob/v0.4.8/gulpfile.js#L22-L31)

## Try the included map

Use a disposable copy of the built TerriaMap 0.4.8 `wwwroot/`. Copy this example's `config.json`, `static-server-config.json`, `init/`, and `data/` into it. Serve the folder over HTTP and visit the map at the path used for its HTML base. In **Explore data**, choose **Sample point**, click **Add to the map**, then pan the map and copy a share link. The recipient should see **Sample point** in the workbench and the panned view when they open it.

The fragment contains map settings and references to shareable layers. Recipients still need access to the underlying data at the same URLs. For a public map, share only layer sources you intend to make public. A local-file upload is not included in a share link. The full URL can be long if the map has a lot of state.

Verified with TerriaMap 0.4.8 / TerriaJS 8.13.0 and Chromium. The example ran at a nested path on a local static server. It generated two different links and restored the second link's layer and camera in a fresh browser context without a `/share` request.

## Optional coffee

If this example saved you time, you can buy me a coffee. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
