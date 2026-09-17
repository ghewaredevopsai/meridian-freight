"""The manifest must agree with the quote.

The depot collects what the quote says. If these two ever disagree, one of them is
wrong and the customer is the one who finds out.
"""

import unittest
from datetime import datetime

from meridian import manifest, rating, tariffs
from meridian.models import Consignment, Parcel, Party, Scope, Service

BOOKED = datetime(2026, 3, 4, 9, 0, 0)


def consignment(**over):
    fields = dict(
        id="MF-9200",
        shipper=Party("Ashcroft Mills", "BOM"),
        consignee=Party("Verity Labs", "DEL"),
        parcels=[Parcel(30, 20, 15, 4000)],
        service=Service.STANDARD,
        scope=Scope.DOMESTIC,
        booked_at=BOOKED,
    )
    fields.update(over)
    return Consignment(**fields)


class ManifestAgreesWithTheQuote(unittest.TestCase):
    def setUp(self):
        self.tariff = tariffs.load()

    def test_a_plain_consignment_matches(self):
        c = consignment()
        self.assertEqual(manifest.manifest_total_minor(c, self.tariff),
                         rating.quote(c, self.tariff).total_minor)

    def test_the_weight_the_sheet_prints_is_the_weight_that_was_priced(self):
        c = consignment(parcels=[Parcel(30, 20, 15, 4000), Parcel(25, 25, 25, 6000)])
        line = manifest.manifest_line(c, self.tariff)
        self.assertEqual(line["weight_g"], c.actual_weight_g)
        self.assertEqual(line["pieces"], 2)


class ManifestSheet(unittest.TestCase):
    def setUp(self):
        self.tariff = tariffs.load()

    def test_a_manifest_only_carries_what_leaves_that_depot(self):
        out = consignment()
        other = consignment(id="MF-9201", shipper=Party("Dunlin Tools", "CCU"))
        built = manifest.build([out, other], "BOM", self.tariff)
        self.assertEqual([line["consignment"] for line in built["lines"]], ["MF-9200"])

    def test_the_sheet_totals_its_own_lines(self):
        built = manifest.build(
            [consignment(), consignment(id="MF-9202")], "BOM", self.tariff)
        self.assertEqual(built["amount_total_minor"],
                         sum(line["amount_minor"] for line in built["lines"]))

    def test_the_printed_sheet_has_a_line_per_consignment(self):
        built = manifest.build(
            [consignment(), consignment(id="MF-9202")], "BOM", self.tariff)
        text = manifest.as_text(built, datetime(2026, 3, 4, 18, 0, 0))
        self.assertIn("MF-9200", text)
        self.assertIn("MF-9202", text)
        self.assertIn("TOTAL", text)


if __name__ == "__main__":
    unittest.main()
