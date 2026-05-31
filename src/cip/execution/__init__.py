"""Execution plane — the ONLY layer that deploys.

Triggered by a signed, scoped, logged request from the control plane. The
control plane never opens SSH, never holds a key, never pushes a file.
"""
