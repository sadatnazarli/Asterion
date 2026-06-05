"""Verifex compliance / entity-screening adapter.

Optional provider. Key + base URL come from env (config.settings) only; the key
is never logged or printed. With either missing — or on any network failure —
the adapter returns a ``provider_unavailable`` / ``error`` result and Asterion
keeps working. A "no match" is reported as such, never as "clean". See docs/30.
"""
