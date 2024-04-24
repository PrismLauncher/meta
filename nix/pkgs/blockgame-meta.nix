{
  lib,
  buildPythonApplication,
  poetry-core,
  bash,
  cachecontrol,
  requests,
  filelock,
  git,
  packaging,
  pydantic_1,
  python,
  rsync,
}:
buildPythonApplication {
  pname = "blockgame-meta";
  version = "unstable";

  pyproject = true;

  src = with lib.fileset;
    toSource {
      root = ../../.;
      fileset = unions (map (fileName: ../../${fileName}) [
        "meta"
        "pyproject.toml"
        "poetry.lock"
        "README.md"
        "update.sh"
      ]);
    };

  nativeBuildInputs = [
    poetry-core
  ];

  buildInputs = [
    bash
  ];

  propagatedBuildInputs = [
    cachecontrol
    requests
    filelock
    packaging
    pydantic_1
  ];

  postInstall = ''
    install -Dm755 $src/update.sh $out/bin/update

    wrapProgram $out/bin/update \
      --prefix PYTHONPATH : "$PYTHONPATH" \
      --prefix PATH : "${lib.makeBinPath [git python rsync]}"
  '';

  meta = with lib; {
    description = "Metadata generator for blockgame launcher.";
    platforms = platforms.linux;
    license = licenses.mspl;
    maintainers = with maintainers; [Scrumplex];
    mainProgram = "update";
  };
}
