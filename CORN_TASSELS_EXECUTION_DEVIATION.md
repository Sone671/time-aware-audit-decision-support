# Corn Tassels formal-execution deviation

Date: 2026-08-12 (Asia/Shanghai).

The pre-private design and hashes were successfully frozen after a truth-free
public run.  A no-unlock invocation was rejected as required.  On the first
explicitly unlocked invocation, the byte projector completed but the formal
loader stopped immediately after decoding the projected CSV header: the
requested `FORMAL_FIELDS` tuple listed expert fields after all public fields,
whereas the byte projector correctly preserved source-column order.  The
loader compared these two different header orders and raised
`projected Corn Tassels header mismatch` before iterating any data row.

The correction changes only that assertion: the expected projected header is
now the source header filtered to the requested field set.  It does not change
the source, eligible rows, action unit, public score, consensus, cost model,
route, loss, targets, sentinel, seeds, certificate, or operating gates.  A
unit test fixes the projection order.

Because the correction followed an explicit private unlock, all results from
the corrected runner are conservatively classified as **post-unlock corrected
independent historical bundle validation**.  They are not a strict untouched
confirmation and not a live prospective expert-timing experiment.  The
original `design_pre_private.json` and lock hashes remain preserved rather
than silently rewritten.
