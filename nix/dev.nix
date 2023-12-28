{
  perSystem = {
    config,
    pkgs,
    self',
    ...
  }: {
    pre-commit.settings = {
      excludes = ["flake.lock"];
      hooks = {
        markdownlint.enable = true;

        alejandra.enable = true;
        deadnix.enable = true;
        nil.enable = true;

        black.enable = true;
      };
    };

    devShells.default = pkgs.mkShell {
      shellHook = ''
        ${config.pre-commit.installationScript}
      '';

      buildInputs = with pkgs; [
        poetry
      ];

      inputsFrom = [self'.packages.default];
    };

    formatter = pkgs.alejandra;
  };
}
