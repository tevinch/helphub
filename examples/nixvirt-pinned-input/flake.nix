{
  description = "Pinned package input for a legacy NixVirt consumer";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/b349185bb79c7cf7ad8ea8c097931730bf473c71";
  inputs.NixVirt = {
    url = "github:AshleyYakeley/NixVirt/b9489f0e4b1cef1d5fe5dcc48f705c1cdfc9e7a8";
    inputs.nixpkgs.follows = "nixpkgs";
  };
  inputs.flake-compat.url = "github:nix-community/flake-compat/38fd3954cf65ce6faf3d0d45cd26059e059f07ea";

  outputs = { NixVirt, ... }: {
    nixvirt = NixVirt;
  };
}
