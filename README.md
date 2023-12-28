# Prism Launcher Meta

Scripts to generate jsons and jars that Prism Launcher will access.

## Recommended Deployment

Assuming you have a Flake-based NixOS configuration

- Add Flake input:

    ```nix
    {
      inputs.prism-meta.url = "github:PrismLauncher/meta";
    }
    ```

- Import NixOS module and configure

    ```nix
    {inputs, ...}: {
      imports = [inputs.prism-meta.nixosModules.default];
      services.blockgame-meta = {
        enable = true;
        settings = {
          DEPLOY_TO_GIT = "true";
          GIT_AUTHOR_NAME = "Herpington Derpson";
          GIT_AUTHOR_EMAIL = "herpderp@derpmail.com";
          GIT_COMMITTER_NAME = "Herpington Derpson";
          GIT_COMMITTER_EMAIL = "herpderp@derpmail.com";
        };
      };
    }
    ```

- Rebuild and activate!
- Trigger it `systemctl start blockgame-meta.service`
- Monitor it `journalctl -fu blockgame-meta.service`
