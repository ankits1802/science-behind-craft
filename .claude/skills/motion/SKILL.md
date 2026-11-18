---
name: motion
description: Retired for KalaVigyan. Animation, transitions, reduced motion and the vat moment are governed by the Motion section of the kalavigyan-design skill; load kalavigyan-design before adding or changing any animation in the web client.
---

# Motion

This skill described the portal's motion vocabulary (springs, staggered rises, GSAP), which the
KalaVigyan design system retired on 18 November 2026 (decision 0092).

Load `kalavigyan-design` and read its section 6, Motion: the durations and easings, the four
named motions (dip, oxidise, press, vat), the two reduced-motion switches with their end states,
and the code rules (framer-motion through `useAppReducedMotion()`, no GSAP, no stagger or spring
entrances). The full specification is `kalavigyan-design/references/SYSTEM.md` section 2.13.
