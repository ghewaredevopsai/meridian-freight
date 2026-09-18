import unittest
from datetime import datetime

from meridian import rating, tariffs
from meridian.errors import RatingError
from meridian.models import Consignment, Parcel, Party, Scope, Service

BOOKED = datetime(2026, 3, 4, 9, 0, 0)


def consignment(**over):
    fields = dict(
        id="MF-9001",
        shipper=Party("Ashcroft Mills", "BOM"),
        consignee=Party("Verity Labs", "DEL"),
        parcels=[Parcel(30, 20, 15, 4000)],
        service=Service.STANDARD,
        scope=Scope.DOMESTIC,
        booked_at=BOOKED,
    )
    fields.update(over)
    return Consignment(**fields)


class ChargeableWeight(unittest.TestCase):
    def setUp(self):
        self.tariff = tariffs.load()

    def test_actual_weight_wins_when_the_parcel_is_dense(self):
        c = consignment(parcels=[Parcel(20, 20, 20, 9000)])
        self.assertEqual(rating.chargeable_weight_g(c, self.tariff), 9000)

    def test_dimensional_weight_wins_when_the_parcel_is_light_and_bulky(self):
        c = consignment(parcels=[Parcel(60, 50, 40, 2000)])
        # 120000 cm3 / 5000 = 24 kg
        self.assertEqual(rating.chargeable_weight_g(c, self.tariff), 24000)

    def test_export_uses_a_different_divisor(self):
        parcels = [Parcel(60, 50, 40, 2000)]
        home = consignment(parcels=parcels)
        away = consignment(parcels=parcels, scope=Scope.EXPORT,
                           consignee=Party("Pellam Foods", "DEL", "SG"))
        self.assertEqual(rating.chargeable_weight_g(home, self.tariff), 24000)
        self.assertEqual(rating.chargeable_weight_g(away, self.tariff), 20000)

    def test_weights_add_up_across_pieces(self):
        c = consignment(parcels=[Parcel(20, 20, 20, 3000), Parcel(20, 20, 20, 2500)])
        self.assertEqual(c.actual_weight_g, 5500)


class Quoting(unittest.TestCase):
    def setUp(self):
        self.tariff = tariffs.load()

    def test_a_quote_totals_its_own_charges(self):
        q = rating.quote(consignment(), self.tariff)
        self.assertEqual(q.total_minor, sum(c.amount_minor for c in q.charges))

    def test_fuel_is_charged_on_the_surcharges_too(self):
        """Fuel is a percentage of what the shipment costs, and a surcharge is
        part of what it costs. Fuel on the base alone under-bills."""
        q = rating.quote(consignment(dangerous_goods=True), self.tariff)
        base = q.charge("BASE").amount_minor
        fuel = q.charge("FUEL").amount_minor
        pre_fuel = sum(c.amount_minor for c in q.charges if c.code != "FUEL")
        self.assertGreater(pre_fuel, base)
        self.assertEqual(fuel, (pre_fuel * 1485) // 10_000)

    def test_every_piece_pays_handling(self):
        one = rating.quote(consignment(), self.tariff)
        three = rating.quote(consignment(
            parcels=[Parcel(30, 20, 15, 4000)] * 3), self.tariff)
        self.assertEqual(three.charge("HANDLING").amount_minor,
                         3 * one.charge("HANDLING").amount_minor)

    def test_an_oversize_piece_adds_its_surcharge_once(self):
        c = consignment(parcels=[Parcel(130, 60, 50, 20000), Parcel(130, 60, 50, 20000)])
        q = rating.quote(c, self.tariff)
        self.assertEqual(q.charge("OVERSIZE").amount_minor, 78000)

    def test_a_consignment_with_no_parcels_cannot_be_priced(self):
        with self.assertRaises(RatingError):
            rating.quote(consignment(parcels=[]), self.tariff)

    def test_insurance_never_falls_below_the_minimum(self):
        q = rating.quote(consignment(declared_value_minor=10_000), self.tariff)
        self.assertEqual(q.charge("INSURANCE").amount_minor, 9000)

    def test_insurance_is_the_full_percentage_of_declared_value(self):
        # 1.15% of 62,200.00 is 715.30. 1.15 * 100 is 114.999... as a float, so
        # truncating it instead of rounding it bills 1.14%.
        q = rating.quote(consignment(declared_value_minor=6_220_000), self.tariff)
        self.assertEqual(q.charge("INSURANCE").amount_minor, 71_530)

    def test_money_is_only_ever_whole_minor_units(self):
        q = rating.quote(consignment(declared_value_minor=123_457), self.tariff)
        for charge in q.charges:
            self.assertIsInstance(charge.amount_minor, int)


class Splitting(unittest.TestCase):
    def test_the_pieces_add_back_to_the_total(self):
        for total in (100, 101, 999, 1000, 1):
            self.assertEqual(sum(rating.split_evenly(total, 3)), total)

    def test_the_remainder_goes_to_the_earliest_parts(self):
        self.assertEqual(rating.split_evenly(100, 3), [34, 33, 33])

    def test_splitting_across_no_parts_is_an_error(self):
        with self.assertRaises(RatingError):
            rating.split_evenly(100, 0)


if __name__ == "__main__":
    unittest.main()
