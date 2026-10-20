# gigmath

True hourly rate for gig-work offers, after platform fees, real costs, and
the unpaid time the app never counts.

The payout an app quotes divides by on-task time only. The waiting before an
order, the empty drive back, invoicing: none of it is in that number.
gigmath recomputes the offer the way the week actually plays out: platform
fee, mileage at your real cost per mile, tolls and parking, a
self-employment tax estimate, and every unpaid minute added to the clock.
Then it flags offers that fall under your floor, lose money outright, hide
40%+ of their time unpaid, or pay less than half the headline rate once the
unpaid work is priced.

One offer at a time, or a JSONL batch ranked by true hourly rate.

## Example

    $ gigmath offer --payout 23 --paid-min 40 --unpaid-min 25 \
        --fee 15 --miles 18 --cost-per-mile 0.30 --tax-rate 14 --floor 15
    offer                   headline  true/hr    net $  unpaid%  flags
    offer                   34.50/hr   11.23/hr    12.17    38.5%  below $15.00/hr floor, true rate is less than half the headline rate

A $23 job with a $34.50/hr headline is $11.23/hr once the fee, 18 miles,
and 25 unpaid minutes are priced in.

## Batch

    gigmath batch offers.jsonl --floor 15

Each line of the file is one offer object; `name` is optional, the rest are
the same keys as the `offer` flags. Output ranks every offer by true hourly
rate. `--json` gives machine-readable output for both commands.

## Notes

- No network access. No dependencies. Python 3 standard library only.
- MIT licensed.
- Homepage: https://extrahustles.com
