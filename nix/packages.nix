{inputs, ...}: {
  imports = [inputs.flake-parts.flakeModules.easyOverlay];

  perSystem = {
    config,
    final,
    ...
  }: {
    packages = {
      blockgame-meta = final.python3.pkgs.callPackage ./pkgs/blockgame-meta.nix {};
      default = config.packages.blockgame-meta;
    };

    overlayAttrs = {
      inherit (config.packages) blockgame-meta;
    };
  };
}
