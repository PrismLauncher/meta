{self, ...}: {
  flake.nixosModules = {
    default = self.nixosModules.meta;
    meta = {
      imports = [self.nixosModules.metaBare];
      nixpkgs.overlays = [self.overlays.default];
    };
    metaBare = ./meta.nix;
  };
}
