import unittest
from datetime import datetime

from meridian import routing, tariffs
from meridian.errors import RoutingError
from meridian.models import Consignment, Parcel, Party, Scope, Service


def consignment(origin="BOM", destination="GAU", service=Service.STANDARD,
                booked_at=datetime(2026, 3, 4, 9, 0, 0)):
    return Consignment(
        id="MF-9100",
        shipper=Party("Ashcroft Mills", origin),
        consignee=Party("Verity Labs", destination),
        parcels=[Parcel(30, 20, 15, 4000)],
        service=service,
        scope=Scope.DOMESTIC,
        booked_at=booked_at,
    )


class Routing(unittest.TestCase):
    def setUp(self):
        self.tariff = tariffs.load()

    def test_a_short_lane_goes_direct(self):
        legs = routing.route(consignment("BOM", "AMD"), self.tariff)
        self.assertEqual(len(legs), 1)
        self.assertEqual((legs[0].from_depot, legs[0].to_depot), ("BOM", "AMD"))

    def test_express_never_goes_through_a_hub(self):
        legs = routing.route(consignment("COK", "GAU", Service.EXPRESS), self.tariff)
        self.assertEqual(len(legs), 1)

    def test_a_long_economy_lane_goes_through_a_hub(self):
        legs = routing.route(consignment("COK", "GAU", Service.ECONOMY), self.tariff)
        self.assertEqual(len(legs), 2)
        self.assertEqual(legs[0].to_depot, legs[1].from_depot)

    def test_routing_does_not_mutate_the_consignment(self):
        c = consignment("COK", "GAU")
        routing.route(c, self.tariff)
        self.assertEqual(c.legs, [])

    def test_the_same_depot_twice_is_an_error(self):
        with self.assertRaises(RoutingError):
            routing.route(consignment("BOM", "BOM"), self.tariff)

    def test_booking_after_the_cutoff_departs_the_next_morning(self):
        late = consignment("BOM", "AMD", booked_at=datetime(2026, 3, 4, 19, 30, 0))
        legs = routing.route(late, self.tariff)
        self.assertEqual(legs[0].depart, datetime(2026, 3, 5, 6, 0, 0))

    def test_transit_hours_covers_time_on_the_ground(self):
        legs = routing.route(consignment("COK", "GAU", Service.ECONOMY), self.tariff)
        direct = tariffs.lane(self.tariff, "COK", "GAU")["transit_hours"]
        self.assertGreater(routing.transit_hours(legs), direct)

    def test_no_legs_is_zero_transit_not_an_error(self):
        self.assertEqual(routing.transit_hours([]), 0)


if __name__ == "__main__":
    unittest.main()
