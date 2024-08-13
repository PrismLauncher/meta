{
  description = "Prism Launcher Metadata generation scripts";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.nixpkgs-stable.follows = "nixpkgs";
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
        "riscv64-linux"
      ];
    };
}
