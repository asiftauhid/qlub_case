# POS Eligibility Reference

**Owner:** US Sales Ops · **Last updated:** 2026-06-22

Qlub sits on top of a restaurant's existing point-of-sale system. We can only sell to a
restaurant whose POS we can integrate with. This file is the authoritative list.

## Eligible — integration available

| Canonical POS | Surface forms seen in the wild |
|---|---|
| **Cadence** | Cadence, Cadence Station, Cadence Flex, Cadence Mini |
| Vellum | Vellum, Vellum POS, Vellum Restaurant |
| Northstar | Northstar, NorthStar, Northstar Restaurant |
| Orbit | Orbit, Orbit POS, Orbit Systems |
| Meridian Cloud | Meridian Cloud, Meridian Cloud POS |
| Quillpay | Quillpay, QuillPay |
| Tessera | Tessera, Tessera Express |
| Bluecrest | Bluecrest, BlueCrest |

> **Change log — 2026-06-22:** Cadence moved from *competitor* to *eligible* following the
> integration release. Cadence has one of the largest installed bases among independent
> full-service restaurants, so this materially expands the addressable pool. **Any artefact
> produced before this date encodes the old rule.**

## Ineligible — no integration

Ironclad · Fernpost · Saltbox · Rivet

## Ambiguous — flag, do not guess

**Meridian (legacy, on-premise)** is a different product from **Meridian Cloud**. Only
Meridian Cloud is eligible. A record that says only "Meridian" cannot be resolved to one or
the other from the string alone.

## Notes

- POS is discovered three ways: website fingerprinting, AI phone calls, human phone calls.
  No single source is complete.
- A restaurant's POS can change. Treat any signal older than ~6 months as soft.
- "unknown" is not "ineligible". Roughly half the market has no POS signal at all; those
  restaurants are unqualified, not disqualified.
