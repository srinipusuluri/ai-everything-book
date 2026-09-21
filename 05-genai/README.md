# 🎨 Module 05 — Generative AI

> **Where you are:** Stop 5 of 16. **Time:** ~20–25 hours · **Prereq:** [Module 02](../02-deep-learning/) (VAEs, backprop), [Module 03](../03-nlp/) (attention/cross-attention).

Modules 03–04 taught you a generative model without calling it one — a language model samples from
`P(next token | context)`. This module widens the lens to pixels, video, and audio, and spends most of its
time on the family that now dominates all three: **diffusion**. You will train a real (tiny) diffusion model
from scratch, measure the DDPM-vs-DDIM speed/quality trade-off in numbers, and see classifier-free guidance
push fidelity against diversity on a toy dataset — not on faith, on printed output. The second half covers
what you actually ship with this: text-to-image pipelines, video and audio generation, vision-language
models, and the honest (unsatisfying) state of evaluating any of it.

---

## Learning objectives

By the end of this module you can:

1. Explain why diffusion displaced GANs/VAEs as the default generative architecture, and name each family's
   fatal-ish weakness.
2. Derive the forward (noising) and reverse (denoising) diffusion processes, and implement DDPM training and
   sampling from scratch in NumPy.
3. Explain DDIM sampling and the accuracy/speed trade-off of fewer reverse steps, with numbers, not vibes.
4. Implement classifier-free guidance and describe the fidelity-vs-diversity trade-off as the guidance scale
   increases — including where it breaks down.
5. Draw the U-Net-to-DiT architecture shift and connect it to the same scaling story that took over NLP.
6. Trace a text-to-image pipeline end to end: text encoder, cross-attention, scheduler, VAE decode, and where
   ControlNet/img2img/inpainting slot in.
7. Name generative AI's real failure modes and unresolved questions — hallucinated detail, deepfake misuse,
   watermarking limits, training-data licensing — and say which module owns each one.

## Suggested path

| # | Do this | File | Time |
|---|---------|------|------|
| 1 | Diffusion mechanism, GAN/VAE comparison, DiT | [notes/01-core-concepts.md](notes/01-core-concepts.md) | 3h |
| 2 | Pipelines, multimodality, evaluation, failure modes | [notes/02-multimodal-and-practice.md](notes/02-multimodal-and-practice.md) | 3h |
| 3 | Train + sample a DDPM from scratch | [code/diffusion_from_scratch.py](code/diffusion_from_scratch.py) | 2h |
| 4 | Measure DDPM vs. DDIM and the guidance-scale sweep | [code/guidance_and_sampling.py](code/guidance_and_sampling.py) | 2h |
| 5 | Present it back | [slides/](slides/) | 1h |
| 6 | Do the exercises | [lab/EXERCISES.md](lab/EXERCISES.md) | 8h |
| 7 | Read the papers | [papers/PAPERS.md](papers/PAPERS.md) | 5h |

## The 14 terms you must own

`diffusion` · `forward/reverse process` · `noise schedule` · `DDPM` · `DDIM` · `classifier-free guidance` ·
`latent diffusion` · `U-Net` · `DiT (diffusion transformer)` · `cross-attention` · `ControlNet` ·
`mode collapse` · `FID` · `CLIP score`

## Where this connects

| Topic here | Where it returns |
|---|---|
| VAEs, latent bottlenecks | [../02-deep-learning/](../02-deep-learning/) — latent diffusion's direct ancestor |
| Cross-attention, transformer blocks | [../03-nlp/](../03-nlp/) — the same mechanism doing double duty; DiT is the same architecture shift NLP already went through |
| Scaling laws, multimodal/vision-language models | [../04-llm/](../04-llm/) — LLaVA-style splicing of image tokens into an LLM |
| Deepfakes, voice cloning, watermark limits | [../13-ai-security/](../13-ai-security/) — social-engineering and synthetic-media threat models |
| Training-data licensing, output copyright | [../14-ai-compliance/](../14-ai-compliance/) — audit trails for model/data provenance |
| FID/CLIP score's limits as a metric | [../15-ai-evals/](../15-ai-evals/) — the image-generation flavor of "no single metric captures 'good'" |

## Exit check ✅

You can run `code/diffusion_from_scratch.py` and `code/guidance_and_sampling.py` unmodified, explain every
printed number (forward-process std, denoiser MSE floor, DDIM steps-vs-quality, guidance fidelity/diversity),
and then — without looking at the code — sketch the DDPM training loop and the classifier-free-guidance
sampling equation on a whiteboard.
