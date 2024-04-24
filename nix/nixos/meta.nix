{
  config,
  lib,
  pkgs,
  ...
}: let
  inherit (lib) getExe mkEnableOption mkIf mkOption mkPackageOption types;

  settingsFormat = pkgs.formats.keyValue {};

  cfg = config.services.blockgame-meta;
in {
  options.services.blockgame-meta = {
    enable = mkEnableOption "blockgame-meta service";

    package = mkPackageOption pkgs "blockgame-meta" {};

    settings = mkOption {
      type = types.submodule {
        freeformType = settingsFormat.type;
        options = {
          DEPLOY_TO_S3 = mkOption {
            type = types.str;
            default = "false";
          };
          DEPLOY_TO_FOLDER = mkOption {
            type = types.str;
            default = "false";
          };
          DEPLOY_TO_GIT = mkOption {
            type = types.str;
            default = "false";
          };
        };
      };
    };
  };
  config = mkIf cfg.enable {
    users.users."blockgame-meta" = {
      isSystemUser = true;
      group = "blockgame-meta";
    };

    users.groups."blockgame-meta" = {};

    systemd = {
      services."blockgame-meta" = {
        description = "blockgame metadata generator";
        after = ["network-online.target"];
        wants = ["network-online.target"];
        serviceConfig = {
          EnvironmentFile = [(settingsFormat.generate "blockgame-meta.env" cfg.settings)];
          ExecStart = getExe cfg.package;
          StateDirectory = "blockgame-meta";
          CacheDirectory = "blockgame-meta";
          User = "blockgame-meta";
        };
      };

      timers."blockgame-meta" = {
        timerConfig = {
          OnCalendar = "hourly";
          RandomizedDelaySec = "5m";
        };
        wantedBy = ["timers.target"];
      };
    };
  };
}
