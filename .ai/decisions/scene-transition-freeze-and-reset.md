# Scene transitions freeze the old frame and reuse each session

**2026-11-14 ・ status: standing ・ scope: switching to a new reference image; prompt-only morphs need none of this**

## What forced the choice

`set_image` has no effect mid-run, so a new scene needs a new run, and a new run shows no
picture for ~2 chunks. A live-to-live crossfade would need a second set of sessions.

## Decision

Capture each wall's last frame as a still, then `reset` → `set_image` → `set_prompt` →
`start` on the same session. Play a local transition effect on the still during warm-up;
crossfade each wall as its first new frame arrives. Peak stays at the normal session count.

## Why not the alternatives

| Alternative | Its case | Why not |
|---|---|---|
| 12 sessions, live crossfade | Both sides moving | Beyond the 8 sessions tested; new sessions hit the 10/min creation limit; 12 decodes |
| Prompt-only morph | Zero cost, native Orbis | Cannot land on a specific image |
| Wall-by-wall with 2 spare sessions (peak 8) | Live-to-live, "wave" effect | Takes 3 rounds (>10 s); keep as a set-piece, not the default |

## What this rests on

| Assumption | Status | Evidence, or the check that would settle it |
|---|---|---|
| `reset` keeps the session and does not count as a creation | verified by docs, not by measurement | Do 10 resets in a minute; expect no 429 |
| Warm-up is ~3–4 s | unverified | Time `start` → first frame on a live run |

## What would reverse this

Warm-up turns out > 8 s (the freeze reads as a hang), or spare-session crossfades prove
cheap enough to use every time.
