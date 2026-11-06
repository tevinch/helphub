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
          # State updates register GC roots through nix-store. Make this
          # dependency explicit in the evaluated test services' real PATH.
          systemd.services."hjem-activate@".path = [pkgs.nix];
          systemd.services."hjem-update-state@".path = [pkgs.nix];
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
    serviceEntry = name: let
      service = services.${name};
      # NixOS builds the actual strict-shell-checked job script and appends
      # scriptArgs to ExecStart. Supply the instance argument ourselves here.
      command = pkgs.lib.removeSuffix " %i" service.serviceConfig.ExecStart;
    in
      assert service.scriptArgs == "%i";
      assert pkgs.lib.hasSuffix " %i" service.serviceConfig.ExecStart;
      pkgs.writeShellScript "run-${name}-${version}" ''
        export PATH=${pkgs.lib.escapeShellArg service.environment.PATH}
        exec ${command} "$@"
      '';
  in {
    # Use the actual evaluated module job scripts and service PATH, including
    # their real generated manifest. Do not reconstruct the manifest/linker.
    activate = serviceEntry "hjem-activate@";
    updateState = serviceEntry "hjem-update-state@";
    originalUnit = "${package}/lib/systemd/user/syncthing.service";
  };
in {
  v1 = snapshot "v1" true;
  v2 = snapshot "v2" true;
  no-wants = snapshot "v2" false;
}
