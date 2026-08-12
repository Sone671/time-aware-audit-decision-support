# Corn Tassels image-bundle validation result

Date: 2026-08-12 (Asia/Shanghai).  Decision:
**STRUCTURAL_INVALIDATION**.  No reportable simultaneous-v3 method episode.

## Public bundle result before truth

The frozen truth-isolating parser retained 10,080 complete participant-image
actions over 80 images and 126 users.  Nineteen zero-area user-coordinate rows
were excluded under the pre-lock public rule; no action was emptied.  One image
was one bundle action and one expert box-set opening was intended to resolve all
126 linked participant annotations.  Five-fold public cost prediction had CV
0.1161 and minimum opportunity -14.49%, so the frozen router retained
score-time before any expert coordinate was decoded.

## Exact-truth coverage failure

After the public score, cost model, route, loss, targets, sentinel, seeds, code,
and hashes were locked, the expert columns were opened.  Every public image
name aligned, and every image had one internally consistent declared expert-box
count.  However, the released coordinate rows did not reconstruct that declared
set for three images:

- one image declared six expert boxes but exposed five distinct coordinates;
- one declared four but exposed three;
- one declared five but exposed four.

Thus three expert boxes are absent from the coordinate space needed by the
frozen IoU matching loss.  The missing boxes appear to be expert boxes unmatched
by every crowd box, but inferring their geometry from counts, images, published
precision/recall, or a different loss would be a post-truth design change.
The formal runner now checks declared count versus coordinate coverage before
constructing any certificate and records zero method episodes.

## Execution note and evidence boundary

The first explicit private invocation stopped at a projected-header order
assertion before iterating expert data rows.  The mechanical assertion was
corrected and documented in `CORN_TASSELS_EXECUTION_DEVIATION.md`; the corrected
run then exposed the structural failure above.  Because both events followed
the private unlock, this candidate cannot be retried as an untouched
confirmation.  Its public score-time routing is retained only as a truth-free
diagnostic, and earlier calculations that treated the incomplete coordinate
union as complete are invalid and not method results.

Source: Zhou et al., Figshare DOI `10.6084/m9.figshare.6360236.v2`, CC BY 4.0.
