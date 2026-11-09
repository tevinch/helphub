import { $typst, loadFonts } from '@myriaddreamin/typst.ts';

// Pin the font revision; serve a licensed copy from your own origin if needed.
const FONT_URL = 'https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf';

// Configure before getCompiler(), svg(), pdf(), or any other first compile.
$typst.setCompilerInitOptions({
  getModule: () => './node_modules/@myriaddreamin/typst-ts-web-compiler/pkg/typst_ts_web_compiler_bg.wasm',
  beforeBuild: [loadFonts([FONT_URL], { assets: false })],
});
$typst.setRendererInitOptions({
  getModule: () => './node_modules/@myriaddreamin/typst-ts-renderer/pkg/typst_ts_renderer_bg.wasm',
});

const source = document.querySelector('#source');
const button = document.querySelector('#render');
const status = document.querySelector('#status');
const preview = document.querySelector('#preview');
const diagnostics = document.querySelector('#diagnostics');
let rendered = 0;

async function render() {
  button.disabled = true;
  status.textContent = 'Compiling…';
  try {
    const compiler = await $typst.getCompiler();
    await compiler.addSource('/main.typ', source.value);
    const result = await compiler.compile({ mainFilePath: '/main.typ', diagnostics: 'full' });
    diagnostics.textContent = JSON.stringify(result.diagnostics || [], null, 2);
    if (!result.result) {
      preview.replaceChildren();
      status.textContent = 'Compile failed. See compiler diagnostics below.';
      return;
    }
    preview.innerHTML = await $typst.svg({ vectorData: result.result });
    status.textContent = `Rendered ${++rendered}`;
  } catch (error) {
    preview.replaceChildren();
    status.textContent = `Compile failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}
button.addEventListener('click', render);
await render();
