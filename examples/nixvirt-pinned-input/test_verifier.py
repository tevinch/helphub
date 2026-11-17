"""Unit controls for evidence validation; these do not execute Nix."""
import copy
import unittest
import verify


def synthetic_evidence():
    return {
        "nixVersion": "unit-control-only",
        "nixvirtRevision": verify.NIXVIRT_REV,
        "rootRevision": verify.SELECTED_REV,
        "dependencyRevision": verify.SELECTED_REV,
        "baselineRevision": verify.BASELINE_REV,
        "rootPath": "/nix/store/selected-source", "dependencyPath": "/nix/store/selected-source",
        "baselinePath": "/nix/store/original-source",
        "rootVersion": "26.05-test", "dependencyVersion": "26.05-test", "baselineVersion": "24.11-test",
        "generatedXml": "<volume><name>fixture-volume</name><capacity unit='MiB'>1</capacity></volume>",
        "writeXmlDerivation": "/nix/store/selected-output.drv",
        "expectedDerivation": "/nix/store/selected-output.drv",
    }


class EvidenceChecks(unittest.TestCase):
    def test_complete_synthetic_record(self):
        self.assertEqual(verify.check_evidence(synthetic_evidence()), [])

    def test_every_operation_is_required(self):
        for field in verify.REQUIRED:
            with self.subTest(field=field):
                data = synthetic_evidence()
                del data[field]
                self.assertTrue(verify.check_evidence(data))

    def test_root_version_alone_cannot_pass(self):
        data = synthetic_evidence()
        data.update(dependencyRevision=verify.BASELINE_REV,
                    dependencyVersion="24.11-test", dependencyPath=data["baselinePath"])
        errors = verify.check_evidence(data)
        self.assertGreaterEqual(sum("NixVirt nixpkgs" in error for error in errors), 3)

    def test_real_generator_output_is_required(self):
        for xml in ("", "not XML", "<volume/>", "<volume><name>fixture-volume</name><capacity unit='GB'>1</capacity></volume>"):
            data = synthetic_evidence()
            data["generatedXml"] = xml
            self.assertTrue(verify.check_evidence(data))

    def test_selected_package_derivation_is_required(self):
        data = synthetic_evidence()
        data["writeXmlDerivation"] = "/nix/store/old-output.drv"
        self.assertTrue(any("derivation differs" in error for error in verify.check_evidence(data)))

    def test_revision_pins_are_enforced(self):
        for field in ("nixvirtRevision", "rootRevision", "dependencyRevision", "baselineRevision"):
            data = copy.deepcopy(synthetic_evidence())
            data[field] = "unrelated-revision"
            self.assertTrue(verify.check_evidence(data))


if __name__ == "__main__":
    unittest.main()
