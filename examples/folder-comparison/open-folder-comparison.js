// Save this complete file in a normal folder inside your vault.
module.exports = async ({ app, obsidian }) => {
  const view = app.workspace.getActiveViewOfType(obsidian.MarkdownView);
  if (!view?.file?.parent) {
    new obsidian.Notice('Open a Markdown note before running Folder comparison.');
    return;
  }

  const scroll = view.editor.getScrollInfo();
  const folder = view.file.parent.path;
  const files = app.vault.getMarkdownFiles()
    .filter(file => file.parent?.path === folder)
    .sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true })
      || (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));

  let anchor = view.leaf;
  try {
    for (const file of files) {
      const leaf = app.workspace.createLeafBySplit(anchor, 'vertical', false);
      await leaf.openFile(file, { active: false });
      anchor = leaf;
    }
  } finally {
    // Creating a split activates it, even when openFile uses active: false.
    app.workspace.setActiveLeaf(view.leaf, { focus: true });
    view.editor.scrollTo(scroll.left, scroll.top);
  }
};
