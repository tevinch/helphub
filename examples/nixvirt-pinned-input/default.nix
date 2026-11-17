# Import this caller-owned directory, rather than the upstream default.nix.
let
  lock = builtins.fromJSON (builtins.readFile ./flake.lock);
  root = lock.nodes.${lock.root};
  compat = lock.nodes.${root.inputs.flake-compat}.locked;
  source = builtins.fetchTarball {
    url = "https://github.com/${compat.owner}/${compat.repo}/archive/${compat.rev}.tar.gz";
    sha256 = compat.narHash;
  };
in
(import source { src = ./.; system = "x86_64-linux"; }).defaultNix
