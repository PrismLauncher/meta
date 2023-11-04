{...}: {
  imports = [
    ./dev.nix
  ];

  # Supported systems.
  systems = [
    "x86_64-linux"
    "aarch64-linux"
  ];
}
