{
  inputs,
  self,
  ...
}: {
  perSystem = {
    system,
    pkgs,
    ...
  }: {
    checks = {
      pre-commit-check = inputs.pre-commit-hooks.lib.${system}.run {
        src = self;
        hooks = {
          markdownlint.enable = true;

          alejandra.enable = true;
          deadnix.enable = true;
          nil.enable = true;

          black.enable = true;
        };
      };
    };

    devShells.default = pkgs.mkShell {
      inherit (self.checks.${system}.pre-commit-check) shellHook;

      packages = [
        (pkgs.python3.withPackages (ps:
          with ps; [
            cachecontrol
            filelock
            requests
            packaging
            pydantic

            coverage
          ]))
      ];
    };

    formatter = pkgs.alejandra;
  };
}
