# Folders-first navigation

```space-lua
local outline = "Library/Space Tree Outline"

local function trim(text)
  return string.match(text, "^%s*(.-)%s*$")
end

-- The outline stores names in its first nested list and attributes at the end
-- of each line. Read hide flags without touching its saved order or icons.
local function outlineHiddenPaths()
  local hidden = {}
  if not space.fileExists(outline .. ".md") then return hidden end

  local markdown = space.readPage(outline):gsub("\r\n?", "\n")
  local parents = {}
  local started, afterBlank = false, false
  for line in string.gmatch(markdown .. "\n", "([^\n]*)\n") do
    local indent, name = string.match(line, "^([ \t]*)[%*%+%-]%s+(.*)$")
    if name and (started or indent == "") then
      started, afterBlank = true, false
      local width = #indent:gsub("\t", "    ")
      while #parents > 0 and parents[#parents].width >= width do
        table.remove(parents)
      end

      local hide
      while true do
        local before, key, value = string.match(name, "^(.-)%s*%[([^%[%]:]*):([^%[%]]*)%]%s*$")
        if not before then break end
        if trim(key) == "hide" and hide == nil then hide = trim(value) == "true" end
        name = before
      end
      local parent = parents[#parents]
      name = trim(name)
      if name ~= "" then
        local fullPath = parent and parent.path .. "/" .. name or name
        if hide ~= nil then hidden[fullPath] = hide end
        table.insert(parents, { width = width, path = fullPath })
      end
    elseif started and trim(line) == "" then
      afterBlank = true
    elseif started and afterBlank and not name then
      break
    end
  end
  return hidden
end

local function libraryPath(name)
  return name == "Library" or string.sub(name, 1, 8) == "Library/"
end

local function treeSource(ctx)
  if not index.isAvailable() then return {} end
  local hidden = outlineHiddenPaths()
  local rows, byName, hasChildren = {}, {}, {}

  local function allowed(name)
    if libraryPath(name) then return false end
    while name do
      if hidden[name] then return false end
      name = string.match(name, "^(.*)/[^/]+$")
    end
    return true
  end

  local function markParents(name)
    local parent = string.match(name, "^(.*)/[^/]+$")
    while parent and not hasChildren[parent] do
      hasChildren[parent] = true
      parent = string.match(parent, "^(.*)/[^/]+$")
    end
  end

  local function add(name, ref)
    local row = { name = name, ref = ref }
    table.insert(rows, row)
    byName[name] = row
    return row
  end

  for _, page in ipairs(query [[from p = index.pages()]]) do
    markParents(page.name)
    local deco = page.pageDecoration or {}
    if deco.hide ~= true and not (deco.tree and deco.tree.hide == true) and allowed(page.name) then
      add(page.name, page.ref or page.name)
    end
  end
  for _, document in ipairs(query [[from d = index.documents()]]) do
    if string.sub(document.name, 1, 1) ~= "_" then
      markParents(document.name)
      if allowed(document.name) then add(document.name, document.ref or document.name) end
    end
  end

  local folders = space.listFolders() or {}
  for _, folder in ipairs(folders) do markParents(folder) end
  for _, folder in ipairs(folders) do
    if allowed(folder) and not hasChildren[folder] then
      local row = byName[folder] or add(folder, nil)
      row.isFolder = true
    end
  end

  if ctx.phrase and ctx.phrase ~= "" then
    rows = search.rank(rows, ctx.phrase, { fields = { name = { weight = 1, segments = true } } })
  end
  return query [[from row = rows order by row.name]]
end

view.define {
  name = "foldersFirstNavigation",
  title = "Folders First",
  command = "Navigate: Folders First",
  dock = "lhs",
  supportedDocks = { "lhs", "rhs" },
  followEditor = true,
  refreshOn = { "index", "folder:changed" },
  search = "source",
  presentation = { mode = "tree", foldersFirst = true, limit = 500 },
  source = treeSource,
  onSelect = function(row)
    if row.ref then editor.navigate(row.ref) end
    return false
  end,
}
```
