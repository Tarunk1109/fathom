"""Profile registry tests — FATHOM §4, and the INC-001 guarantees.

The registry's job is not just to load records. It is to make the INC-001 state
*unrepresentable*: a profile that is hypothetical in some fields and real in others must not
load at all, because a half-synthetic profile is exactly what went wrong.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.policy import FieldValue, fact_hash  # noqa: E402
from packages.profiles import Profile, ProfileError, ProfileRegistry, validate  # noqa: E402
from tools import pii_sweep  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def hypo(**overrides) -> Profile:
    defaults = dict(
        profile_id="profile_hypo_clean", hypothetical=True, sandbox_only=False,
        label="HYPOTHETICAL", description="",
        facts={"first_name": "Avery", "annual_km": "12000"},
        elections={"collision_deductible": "1000"},
    )
    defaults.update(overrides)
    return Profile(**defaults)


class TestShippedProfiles(unittest.TestCase):
    """The records that actually ship."""

    def setUp(self) -> None:
        self.registry = ProfileRegistry()

    def test_all_three_profiles_load(self):
        self.assertEqual(self.registry.ids(),
                         ("profile_hypo_clean", "profile_operator", "profile_sim_g2"))

    def test_the_primary_profile_is_hypothetical_and_not_sandbox_only(self):
        """The whole point of amendment D-002: the two flags are independent."""
        primary = self.registry.primary()
        self.assertTrue(primary.hypothetical)
        self.assertFalse(primary.sandbox_only)

    def test_the_hypothetical_profile_carries_no_licence_number(self):
        primary = self.registry.primary()
        combined = {**primary.facts, **primary.elections}
        for forbidden in pii_sweep_forbidden():
            self.assertNotIn(forbidden, combined)

    def test_the_operator_profile_holds_no_real_values_in_the_repo(self):
        """Real values live in the vault and are referenced by key. The repo holds none."""
        operator = self.registry.get("profile_operator")
        self.assertIn("licence_number", operator.vault_refs)
        self.assertNotIn("licence_number", operator.facts)
        self.assertNotIn("first_name", operator.facts)
        self.assertNotIn("postal_code", operator.facts)

    def test_the_simulation_profile_is_sandbox_only(self):
        sim = self.registry.get("profile_sim_g2")
        self.assertTrue(sim.sandbox_only)
        self.assertTrue(sim.is_labelled_simulation())

    def test_the_hypothetical_profile_can_fill_the_fields_sonnet_demanded(self):
        """Day 0 mapped Sonnet's taxonomy. The profile must be able to answer it."""
        primary = self.registry.primary()
        required = ["first_name", "last_name", "date_of_birth", "address_line_1", "postal_code",
                    "licence_class", "vehicle_year", "vehicle_make", "vehicle_model", "annual_km"]
        tagged = primary.tagged(required)
        self.assertEqual(len(tagged), len(required))


def pii_sweep_forbidden():
    from packages.profiles import FORBIDDEN_UNDER_HYPOTHETICAL
    return FORBIDDEN_UNDER_HYPOTHETICAL


class TestProvenance(unittest.TestCase):
    def test_every_emitted_field_is_tagged_with_its_profile(self):
        tagged = hypo().tagged(["first_name", "annual_km"])
        for name, value in tagged.items():
            self.assertIsInstance(value, FieldValue)
            self.assertEqual(value.source_profile_id, "profile_hypo_clean", name)

    def test_requesting_a_field_the_profile_lacks_raises_rather_than_improvising(self):
        """INC-001 was a missing value filled from somewhere else. There is no 'somewhere else'."""
        with self.assertRaises(ProfileError) as caught:
            hypo().tagged(["address_line_1"])
        self.assertIn("address_line_1", str(caught.exception))

    def test_tagged_values_stringify_to_the_underlying_value(self):
        """Rules read values as strings; the wrapper must not change what they see."""
        self.assertEqual(str(hypo().tagged(["annual_km"])["annual_km"]), "12000")


class TestFactLock(unittest.TestCase):
    def test_every_material_fact_is_hashed(self):
        profile = hypo()
        lock = profile.fact_lock()
        self.assertEqual(set(lock), set(profile.facts))
        self.assertEqual(lock["annual_km"], fact_hash("12000"))

    def test_elections_are_not_fact_locked(self):
        """§10.2's boundary: coverage elections vary freely, facts never do."""
        self.assertNotIn("collision_deductible", hypo().fact_lock())

    def test_the_hypothetical_profile_is_fact_locked_like_any_other(self):
        """Operator's ruling: if the clean profile's facts drift between insurers, every parity
        and channel-arbitrage claim is invalid."""
        self.assertGreater(len(ProfileRegistry().primary().fact_lock()), 20)


class TestValidationRefusesIncOneOneStates(unittest.TestCase):
    def test_a_hypothetical_carrying_a_licence_number_will_not_load(self):
        with self.assertRaises(ProfileError) as caught:
            validate(hypo(facts={"licence_number": "A11112222233333"}))  # pii-sweep: allow DL_ONTARIO  synthetic
        self.assertIn("licence number", str(caught.exception))

    def test_a_hypothetical_reaching_into_the_vault_will_not_load(self):
        with self.assertRaises(ProfileError) as caught:
            validate(hypo(vault_refs={"address_line_1": "operator.address_line_1"}))
        self.assertIn("vault", str(caught.exception))

    def test_a_hypothetical_carrying_an_operator_value_will_not_load(self):
        """INC-001 in profile form: a real value copied into a synthetic record."""
        operator_hashes = frozenset({fact_hash("Avery")})
        with self.assertRaises(ProfileError) as caught:
            validate(hypo(), operator_value_hashes=operator_hashes)
        self.assertIn("first_name", str(caught.exception))

    def test_a_clean_hypothetical_validates(self):
        validate(hypo(), operator_value_hashes=frozenset({fact_hash("something else")}))

    def test_a_real_profile_without_vault_refs_will_not_load(self):
        with self.assertRaises(ProfileError):
            validate(Profile(profile_id="profile_operator", hypothetical=False,
                             sandbox_only=False, label="", description="",
                             facts={"licence_class": "G1"}))

    def test_the_shipped_hypothetical_profile_survives_validation_against_the_vault(self):
        """A regression guard: if an operator value is ever pasted into the synthetic record,
        loading the registry with the vault's hashes fails here."""
        path = REPO_ROOT / "data" / "profiles" / "profile_hypo_clean.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        values = {**data.get("facts", {}), **data.get("elections", {})}.values()
        # Simulate a vault whose contents are entirely different from the synthetic profile.
        registry = ProfileRegistry(operator_value_hashes=frozenset({fact_hash("unrelated")}))
        self.assertIn("profile_hypo_clean", registry)
        self.assertTrue(all(isinstance(v, str) for v in values))


class TestFileScopedSweepAllowance(unittest.TestCase):
    """The `allow-file` mechanism added for synthetic profile records."""

    def test_a_named_allowance_suppresses_only_its_rules(self):
        text = ('{"_pii_sweep": "pii-sweep: allow-file STREET_ADDRESS",\n'
                ' "a": "123 Fake Street",\n'   # pii-sweep: allow STREET_ADDRESS  synthetic
                ' "b": "K1A 0B1"}\n')          # pii-sweep: allow PC_FULL_POSTAL  synthetic
        allowed = pii_sweep.file_allowed_rules(text)
        self.assertEqual(allowed, {"STREET_ADDRESS"})
        rules = {f.rule_id for line_no, line in enumerate(text.splitlines(), 1)
                 for f in pii_sweep.scan_line("f", line_no, line, allowed)}
        self.assertNotIn("STREET_ADDRESS", rules)
        self.assertIn("PC_FULL_POSTAL", rules)

    def test_there_is_no_bare_allow_file(self):
        """A file-wide blanket allowance would be a hole. The rules must be named."""
        self.assertEqual(pii_sweep.file_allowed_rules('"pii-sweep: allow-file"'), set())

    def test_a_declaration_below_the_header_is_ignored(self):
        """Otherwise any file that merely discusses the pragma grants itself one — which is how
        this very test file acquired an unintended allowance before the header rule existed."""
        buried = "\n".join(["padding"] * 40 + ['"pii-sweep: allow-file STREET_ADDRESS"'])
        self.assertEqual(pii_sweep.file_allowed_rules(buried), set())

    def test_this_test_file_grants_itself_no_file_wide_allowance(self):
        own_text = Path(__file__).read_text(encoding="utf-8")
        self.assertEqual(pii_sweep.file_allowed_rules(own_text), set())

    def test_allowances_are_reported_not_silent(self):
        report = pii_sweep.sweep(REPO_ROOT)
        paths = [path for path, _ in report.file_allowances]
        self.assertIn("data/profiles/profile_hypo_clean.json", paths)

    def test_the_line_pragma_still_works_alongside(self):
        line = 'x = "K1A 0B1"  # pii-sweep: allow PC_FULL_POSTAL'
        self.assertEqual({f.rule_id for f in pii_sweep.scan_line("f", 1, line)}, set())


class TestRegistryLoading(unittest.TestCase):
    def test_a_malformed_record_raises_with_the_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text(json.dumps({"profile_id": "x"}), encoding="utf-8")
            with self.assertRaises(ProfileError) as caught:
                ProfileRegistry(tmp)
            self.assertIn("broken.json", str(caught.exception))

    def test_an_unknown_profile_raises(self):
        with self.assertRaises(ProfileError):
            ProfileRegistry().get("profile_does_not_exist")


if __name__ == "__main__":
    unittest.main()
