{
  description = "Prism Launcher Metadata generation scripts";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.flake-compat.follows = "";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs:
    inputs.flake-parts.lib.mkFlake
    {inherit inputs;}
    {
      imports = [
        inputs.git-hooks.flakeModule

        ./nix/dev.nix
        ./nix/nixos
        ./nix/packages.nix
      ];

      # Supported systems.
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
    };
}
