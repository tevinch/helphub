{
  nixpkgs,
  hjem,
  pkgs,
  system,
}: let
  # The service is named syncthing.service to exercise enable-unit.nix unchanged.
  # It runs only this local marker writer, with no Syncthing or networking.
  fixture = version: let
    writeMarker = pkgs.writeShellScript "write-unit-marker-${version}" ''
      printf '%s\n' '${version}' > /var/tmp/unitcheck/unit-marker
    '';
  in
    pkgs.runCommand "packaged-user-unit-${version}" {} ''
      mkdir -p "$out/lib/systemd/user"
      cat > "$out/lib/systemd/user/syncthing.service" <<EOF
      [Unit]
      Description=Packaged user-unit startup check ${version}

      [Service]
      Type=oneshot
      RemainAfterExit=yes
      ExecStart=${writeMarker}

      [Install]
      WantedBy=default.target
      EOF
    '';

  snapshot = version: enableWants: let
    package = fixture version;
    evaluated = nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [
        hjem.nixosModules.default
        {
          system.stateVersion = "26.05";
          users.users.unitcheck = {
            isNormalUser = true;
            home = "/var/tmp/unitcheck";
          };
          hjem.users.unitcheck = {
            imports = pkgs.lib.optional enableWants ../enable-unit.nix;
            systemd.packages = [package];
          };
        }
      ];
    };
    services = evaluated.config.systemd.services;
  in {
    # Use the actual evaluated module scripts, including its real generated
    # manifest. Do not reconstruct Hjem's manifest or linking implementation.
    activate = pkgs.writeShellScript "activate-packaged-unit-${version}" services."hjem-activate@".script;
    updateState = pkgs.writeShellScript "record-packaged-unit-${version}" services."hjem-update-state@".script;
    originalUnit = "${package}/lib/systemd/user/syncthing.service";
  };
in {
  v1 = snapshot "v1" true;
  v2 = snapshot "v2" true;
  no-wants = snapshot "v2" false;
}
