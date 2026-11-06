# Import inside hjem.users.<name>, alongside systemd.packages = [ pkgs.syncthing ].
{config, ...}: {
  xdg.config.files."systemd/user/default.target.wants/syncthing.service".source =
    config.xdg.config.files."systemd/user/syncthing.service".source;
}
