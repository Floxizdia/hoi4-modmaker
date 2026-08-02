"""A cheap "is this mod okay" check for the home screen's resume card - just
the structural error count from the Validate tab's own logic, no full icon
index (which needs a multi-second gfx scan across the base game and every
Workshop mod) so it stays fast enough to run automatically in the
background the moment the app opens.

Icon-existence checks are deliberately skipped here (they'd all show as
missing without a real gfx index) - this only surfaces the severity level
that's independent of that: broken references, duplicate ids, unbalanced
braces. The full Validate tab remains the source of truth for everything
else.
"""

from app import mod_loader as ml
from app import validator


def quick_check(mod_root):
    """{'errors': n, 'warnings': n} - open the Validate tab for the full picture."""
    loc = ml.load_localisation(mod_root)
    issues = validator.validate(mod_root, loc, {})
    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    return {"errors": errors, "warnings": warnings}
