#!/usr/bin/env python3
"""gigmath: true hourly rate for gig-work offers, after fees, costs, and unpaid time.

The number a gig app shows you is payout divided by on-task time. The number
you actually earn divides what is left after platform fees and out-of-pocket
costs by ALL the time the job takes, including the unpaid waiting, the
deadhead leg back, and the admin minutes. This tool computes both and ranks
a batch of offers by the real one.

Stdlib only. MIT license. No network access.
"""
import argparse
import json
import sys

VERSION = "0.1.0"


def compute_offer(payout, paid_min, unpaid_min, fee_pct=0.0, miles=0.0,
                  cost_per_mile=0.0, tolls=0.0, parking=0.0, other=0.0,
                  tax_pct=0.0):
    """Return the full receipt for one gig offer."""
    if payout < 0:
        raise ValueError("payout must be >= 0")
    if paid_min <= 0:
        raise ValueError("paid_min must be > 0")
    if unpaid_min < 0:
        raise ValueError("unpaid_min must be >= 0")
    if not 0 <= fee_pct <= 100:
        raise ValueError("fee_pct must be 0..100")
    if not 0 <= tax_pct <= 100:
        raise ValueError("tax_pct must be 0..100")

    fee_dollars = payout * fee_pct / 100.0
    cost_dollars = miles * cost_per_mile + tolls + parking + other
    pretax = payout - fee_dollars - cost_dollars
    tax_dollars = max(0.0, pretax) * tax_pct / 100.0
    net = pretax - tax_dollars
    total_min = paid_min + unpaid_min
    hours = total_min / 60.0
    paid_hours = paid_min / 60.0
    true_hourly = net / hours if hours > 0 else 0.0
    headline_hourly = payout / paid_hours
    haircut_pct = (1.0 - true_hourly / headline_hourly) * 100.0 if headline_hourly else 0.0
    unpaid_share = unpaid_min / total_min * 100.0 if total_min else 0.0
    return {
        "payout": round(payout, 2),
        "fee_dollars": round(fee_dollars, 2),
        "costs": round(cost_dollars, 2),
        "pretax_net": round(pretax, 2),
        "tax_estimate": round(tax_dollars, 2),
        "net": round(net, 2),
        "paid_minutes": paid_min,
        "unpaid_minutes": unpaid_min,
        "total_minutes": total_min,
        "unpaid_time_share_pct": round(unpaid_share, 1),
        "headline_hourly": round(headline_hourly, 2),
        "true_hourly": round(true_hourly, 2),
        "haircut_pct": round(haircut_pct, 1),
    }


def verdict(rec, floor):
    flags = []
    if rec["true_hourly"] < floor:
        flags.append("below $%.2f/hr floor" % floor)
    if rec["net"] <= 0:
        flags.append("negative net")
    if rec["unpaid_time_share_pct"] >= 40.0:
        flags.append("unpaid time is 40%+ of the job")
    if rec["haircut_pct"] >= 50.0:
        flags.append("true rate is less than half the headline rate")
    return flags


def render_table(recs, floor):
    rows = []
    for name, rec in recs:
        rows.append((name, rec))
    lines = []
    lines.append("%-22s %8s %8s %8s %8s  %s" % (
        "offer", "headline", "true/hr", "net $", "unpaid%", "flags"))
    for name, rec in rows:
        v = verdict(rec, floor)
        lines.append("%-22s %7.2f/hr %7.2f/hr %8.2f %7.1f%%  %s" % (
            name[:22], rec["headline_hourly"], rec["true_hourly"],
            rec["net"], rec["unpaid_time_share_pct"],
            ", ".join(v) if v else "ok"))
    lines.append("")
    lines.append("ranked by true hourly:")
    for i, (name, rec) in enumerate(sorted(rows, key=lambda x: -x[1]["true_hourly"]), 1):
        lines.append("  %d. %-22s $%.2f/hr true ($%.2f headline)"
                     % (i, name[:22], rec["true_hourly"], rec["headline_hourly"]))
    return "\n".join(lines)


def load_batch(path):
    offers = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit("batch line %d is not JSON: %s" % (ln, e))
            name = item.pop("name", "offer-%d" % ln)
            offers.append((name, compute_offer(**item)))
    return offers


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gigmath",
        description="True hourly rate for gig offers after fees, costs, and unpaid time.")
    ap.add_argument("--version", action="version", version="gigmath " + VERSION)
    sub = ap.add_subparsers(dest="cmd", required=True)

    po = sub.add_parser("offer", help="price one offer")
    po.add_argument("--payout", type=float, required=True,
                    help="dollars the app pays for the job")
    po.add_argument("--paid-min", type=float, required=True,
                    help="on-task minutes the payout covers")
    po.add_argument("--unpaid-min", type=float, default=0.0,
                    help="waiting, deadhead return, admin minutes")
    po.add_argument("--fee", type=float, default=0.0, help="platform fee percent")
    po.add_argument("--miles", type=float, default=0.0, help="job miles")
    po.add_argument("--cost-per-mile", type=float, default=0.0,
                    help="your real vehicle cost per mile in dollars")
    po.add_argument("--tolls", type=float, default=0.0)
    po.add_argument("--parking", type=float, default=0.0)
    po.add_argument("--other", type=float, default=0.0,
                    help="supplies, data, misc dollars")
    po.add_argument("--tax-rate", type=float, default=0.0,
                    help="self-employment tax estimate percent on pretax net")
    po.add_argument("--floor", type=float, default=15.0,
                    help="dollars/hour below which the offer is flagged")
    po.add_argument("--json", action="store_true", help="JSON output")

    pb = sub.add_parser("batch", help="rank a JSONL file of offers")
    pb.add_argument("file", help="JSONL, one offer object per line (same keys as offer flags)")
    pb.add_argument("--floor", type=float, default=15.0)
    pb.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "offer":
        rec = compute_offer(
            payout=args.payout, paid_min=args.paid_min, unpaid_min=args.unpaid_min,
            fee_pct=args.fee, miles=args.miles, cost_per_mile=args.cost_per_mile,
            tolls=args.tolls, parking=args.parking, other=args.other,
            tax_pct=args.tax_rate)
        if args.json:
            rec["flags"] = verdict(rec, args.floor)
            print(json.dumps(rec, indent=2))
        else:
            print(render_table([("offer", rec)], args.floor))
        return 0

    if args.cmd == "batch":
        offers = load_batch(args.file)
        if args.json:
            out = []
            for name, rec in offers:
                rec["name"] = name
                rec["flags"] = verdict(rec, args.floor)
                out.append(rec)
            print(json.dumps(out, indent=2))
            return 0
        if not offers:
            print("no offers in file")
            return 3
        print(render_table(offers, args.floor))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        print("gigmath: %s" % e, file=sys.stderr)
        sys.exit(3)
