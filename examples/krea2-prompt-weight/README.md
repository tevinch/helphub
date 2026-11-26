# Add Krea2 Prompt Weight in ComfyUI

1. In ComfyUI Manager, search **Node Pack** for `ComfyUI-KJNodes` by `kijai`. Select `1.5.0` under **Version** if Manager offers it, and install it. [Manager version selection](https://docs.comfy.org/manager/pack-management) · [Comfy Registry entry](https://registry.comfy.org/nodes/comfyui-kjnodes)
2. Restart ComfyUI and refresh the browser.
3. Double-click an empty part of the canvas and search for **Krea2 Prompt Weight**. Select it and place it on the canvas. The node is under `KJNodes/experimental`.

If the node still doesn't appear, check the ComfyUI startup log for an import error for `ComfyUI-KJNodes`. [ComfyUI custom-node installation guide](https://docs.comfy.org/installation/install_custom_node)

Open [the sample workflow](krea2-prompt-weight.json) from the ComfyUI workflow menu to see the node and a sample weighted prompt. The sample is for inspecting the node and can be opened without any model files. To run a workflow with this node, connect your Krea 2 model and text encoder first.

The example was checked by adding the node, saving the workflow, and reopening the saved file in ComfyUI 0.46.0 with ComfyUI-KJNodes 1.5.0.

## Optional coffee

If this saved you some time, you're welcome to buy me a coffee. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
