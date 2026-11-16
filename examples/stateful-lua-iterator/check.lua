-- A closure must keep its Lua-owned selection alive, then release it.
do
    local selection = celestia:getselection()
    local weak = setmetatable({ selection }, { __mode = "v" })
    local step = selection:locations()
    assert(type(step) == "function", "locations must return an iterator function")
    selection = nil
    collectgarbage("collect")
    assert(weak[1] ~= nil, "iterator must retain its selection owner")

    local first = step()
    assert(first:name() == "Alpha", "first location")
    assert(step():name() == "Beta", "cursor must advance to the second location")
    assert(step():name() == "Gamma", "third location")
    assert(step() == nil, "iterator must terminate")
    assert(step() == nil, "exhausted iterator must stay exhausted")

    step = nil
    collectgarbage("collect")
    assert(weak[1] == nil, "released iterator must release its selection owner")
    assert(first:name() == "Alpha", "yielded values must outlive the selection")
end
collectgarbage("collect")
print("LIFETIME retained owner, released owner, retained yielded value")

-- This is the original chained generic-for expression, repeated in full.
for round = 1, 2 do
    for loc in celestia:getselection():locations() do
        celestia:log(loc:name())
    end
end

do
    local visits = 0
    for loc in celestia:getemptyselection():locations() do
        visits = visits + 1
    end
    assert(visits == 0, "empty selection must not yield a location")
    local empty = celestia:getemptyselection():locations()
    assert(empty() == nil and empty() == nil, "empty iterator stays exhausted")
end

do
    local selection = celestia:getselection()
    local a = selection:locations()
    local b = selection:locations()
    assert(a():name() == "Alpha", "first cursor starts at Alpha")
    assert(b():name() == "Alpha", "second cursor must start independently")
    assert(a():name() == "Beta", "first cursor keeps its progress")
    assert(b():name() == "Beta", "second cursor keeps its progress")
    assert(a():name() == "Gamma" and a() == nil, "first cursor finishes")
    assert(b():name() == "Gamma" and b() == nil, "second cursor finishes")
end

collectgarbage("collect")
workflow_complete = true
print("LUA complete: repeated loop, empty selection, exhaustion, independent cursors")
