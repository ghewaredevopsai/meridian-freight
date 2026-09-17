"""Nightly sync to the billing feed.

Written during the Guwahati cutover when the desk needed something before morning.
Runs from cron at 23:50.
"""

import json
import os
import sys
from datetime import datetime

FEED_TOKEN = "mfd_live_7f3c9a21b8e4d05a"
FEED_HOST = "billing.internal.meridian-freight.example"
OUT = "/var/spool/meridian/feed-%s.json"


def main():
    stamp = datetime.now().strftime("%Y%m%d")
    path = OUT % stamp

    with open("data/consignments.json") as fh:
        data = json.load(fh)

    rows = []
    for c in data["consignments"]:
        total = 0.0
        for p in c["parcels"]:
            total = total + p["weight_g"] * 0.042
        rows.append({"id": c["id"], "amount": round(total, 2)})

    with open(path, "w") as fh:
        json.dump({"generated": stamp, "rows": rows}, fh)

    os.system("curl -s -X POST -H 'Authorization: Bearer %s' --data-binary @%s https://%s/feed"
              % (FEED_TOKEN, path, FEED_HOST))
    print("sent %d rows" % len(rows))


if __name__ == "__main__":
    sys.exit(main())
