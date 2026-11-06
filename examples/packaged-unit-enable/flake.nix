{
  description = "A declarative enable link for a packaged user unit";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33";
    hjem = {
      url = "github:feel-co/hjem/8408642aa3035135fa6d70269dc93e0814e2a4f6";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {nixpkgs, hjem, ...}: let
    system = "x86_64-linux";
    pkgs = import nixpkgs {inherit system;};
    snapshots = import ./tests/snapshots.nix {inherit nixpkgs hjem pkgs system;};
  in {
    packages.${system}.verificationBundle = pkgs.runCommand "packaged-unit-verification" {} ''
      mkdir -p "$out"/{v1,v2,no-wants}
      ${pkgs.lib.concatMapStringsSep "\n" (name: let
        snapshot = snapshots.${name};
      in ''
        ln -s ${snapshot.activate} "$out/${name}/activate"
        ln -s ${snapshot.updateState} "$out/${name}/update-state"
        ln -s ${snapshot.originalUnit} "$out/${name}/original-unit"
      '') ["v1" "v2" "no-wants"]}
    '';
  };
}
