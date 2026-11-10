local options = ...
local previous_convert = options.convert
options.convert = function(item)
  local converted = previous_convert and previous_convert(item) or {}
  return vim.tbl_extend('force', converted, { equal = 1 })
end
return options
