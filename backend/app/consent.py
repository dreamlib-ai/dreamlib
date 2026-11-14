"""R1: per-dream consent tiers (docs/kararlar/0007-riza-kademeleri.md).

A dream's `visibility` is its tier; it changes only through the store's set_tier, which also writes the `consents`
ledger in the same transaction. The client shows the consent text of CONSENT_VERSION and sends that version back;
when the text changes the version changes, and an old consent no longer covers the new wording."""

TIERS = ("private", "collective", "public")
CONSENT_VERSION = "consent@1"  # the wording shown when a dream is opened up (frontend strings: tr.consent)
ONBOARDING_VERSION = "onboarding@1"  # the privacy choice made in onboarding, applied to new dreams as they are saved
