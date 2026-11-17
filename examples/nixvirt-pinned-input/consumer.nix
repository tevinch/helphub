{ fixture ? toString ./. }:
let
  system = "x86_64-linux";
  caller = import (builtins.toPath (fixture + "/default.nix"));
  selectedSource = caller.inputs.nixpkgs;
  dependencySource = caller.inputs.NixVirt.inputs.nixpkgs;
  selectedPackages = import selectedSource { inherit system; };
  dependencyPackages = import dependencySource { inherit system; };

  # Evaluate the original entrypoint too, without changing its source or lock.
  original = import (caller.inputs.NixVirt.outPath + "/default.nix");
  baselineSource = original.inputs.nixpkgs;
  baselinePackages = import baselineSource { inherit system; };

  volume = { name = "fixture-volume"; capacity = { count = 1; unit = "MiB"; }; };
  xml = caller.nixvirt.lib.volume.getXML volume;
  actualFile = caller.nixvirt.lib.volume.writeXML volume;
  expectedFile = selectedPackages.writeTextFile {
    name = "NixVirt-volume-fixture-volume";
    text = xml;
  };
in
{
  nixVersion = builtins.nixVersion;
  nixvirtRevision = caller.inputs.NixVirt.rev;
  rootRevision = selectedSource.rev;
  dependencyRevision = dependencySource.rev;
  baselineRevision = baselineSource.rev;
  rootPath = toString selectedSource.outPath;
  dependencyPath = toString dependencySource.outPath;
  baselinePath = toString baselineSource.outPath;
  rootVersion = selectedPackages.lib.version;
  dependencyVersion = dependencyPackages.lib.version;
  baselineVersion = baselinePackages.lib.version;
  generatedXml = xml;
  writeXmlDerivation = actualFile.drvPath;
  expectedDerivation = expectedFile.drvPath;
}
