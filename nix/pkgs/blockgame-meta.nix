{
  lib,
  buildPythonApplication,
  poetry-core,
  bash,
  cachecontrol,
  requests,
  filelock,
  git,
  openssh,
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
        "init.sh"
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
    install -Dm755 $src/init.sh $out/bin/init

    wrapProgram $out/bin/update \
      --prefix PYTHONPATH : "$PYTHONPATH" \
      --prefix PATH : ${lib.makeBinPath [git openssh python rsync]}

    wrapProgram $out/bin/init \
      --prefix PATH : ${lib.makeBinPath [git openssh]}
  '';

  meta = with lib; {
    description = "Metadata generator for blockgame launcher.";
    platforms = platforms.linux;
    license = licenses.mspl;
    maintainers = with maintainers; [Scrumplex];
    mainProgram = "update";
  };
}
