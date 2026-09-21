---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #14B8A6; }
  section { font-size: 24px; }
---

# Generative AI

### Diffusion, and everything built on top of it

**Module 05** · AI End-to-End Learning Track

---

## Why this module exists

- An LLM already IS a generative model: samples from P(next token)
- This module widens the lens to pixels, video, and audio
- One family now dominates all three: diffusion
- Target: train a real (tiny) diffusion model from scratch, no hand-waving

<!-- speaker note: Frame this as Module 03/04's generative idea, applied to a continuous signal instead of discrete tokens. -->

---

## The generative family tree

| Family | Core idea | Fatal-ish weakness |
|---|---|---|
| Autoregressive | factorise P(x), generate one unit at a time | sequential = slow at pixel scale |
| VAE | probabilistic bottleneck, decode back | blurry - ELBO averages away uncertainty |
| GAN | generator vs discriminator, adversarial | mode collapse, unstable, no likelihood |
| Diffusion | learn to reverse a noising process | slow sampling (many steps) |


<!-- speaker note: Normalizing flows exist too but haven't scaled - mention in passing if asked. -->

---

## Why diffusion won

- Diffusion training is plain regression: predict the noise you added
- No adversary, no minimax game, no mode collapse by construction
- That is exactly why it scaled to internet-size data with no babysitting
- Price: sampling needs tens-to-hundreds of network passes, not one
- Opinion: default to diffusion (or flow matching) unless you have a reason not to

<!-- speaker note: GANs still win a narrow set of real-time single-domain tasks - name one if asked, e.g. face reenactment. -->

---

## Forward process: destroy the image on a schedule

- x_t = sqrt(1-beta_t)*x_(t-1) + sqrt(beta_t)*eps, repeated T times
- No learning required here - it is arithmetic, governed by a schedule
- Closed form: x_t = sqrt(abar_t)*x0 + sqrt(1-abar_t)*eps
- This closed form is why training needs no simulation loop
- Pick a random x0, random t, one eps -> one training example, one line

<!-- speaker note: Emphasize the closed-form jump - it is the single most important equation in the whole module. -->

---

## Reverse process: learn to undo it

- Train a network eps_theta(x_t, t) to predict the noise that was added
- Loss: mean squared error between predicted and true noise
- Same supervised training loop as Module 01, extra input: a random timestep
- Sampling: start from pure noise, iteratively subtract predicted noise
- Small steps matter - one big leap produces a blurry average, not sharp detail

<!-- speaker note: Tie the 'blurry average' failure directly back to why VAEs blur - same underlying math. -->

---

## DDPM vs DDIM sampling

|  | DDPM | DDIM |
|---|---|---|
| Reverse step | stochastic | deterministic (tunable via eta) |
| Steps for good quality | ~1000 | 20-50 |
| Reproducible from seed | no | yes |
| Latent interpolation | not meaningful | meaningful |


<!-- speaker note: code/guidance_and_sampling.py measures this exact table numerically - show the printed output. -->

---

## Classifier-free guidance

- Conditioning directly, eps_theta(x_t,t,c), tends to be soft
- Fix: randomly drop the condition during training (~10% of examples)
- At sampling time, run the network twice: conditioned and unconditioned
- eps_guided = eps_u + w * (eps_c - eps_u), w is the guidance scale
- No separate classifier needed - the trick is in training, not sampling

<!-- speaker note: This is the CFG-scale slider in every text-to-image tool - name it explicitly. -->

---

## Guidance scale: fidelity up, diversity down

| Guidance scale w | Prompt fidelity | Diversity | Artifacts |
|---|---|---|---|
| ~1 | weak | high | soft, generic |
| ~5-8 (typical default) | good | moderate | rare |
| ~15-20 | very literal | low, samples converge | oversaturated |
| ~30+ | prompt-obsessed | collapsed | severe |


<!-- speaker note: code/guidance_and_sampling.py's Q2 sweep produces this table's numbers on a toy dataset - no free lunch. -->

---

## Latent diffusion: why Stable Diffusion is not pixel-space

- Diffusing 512x512x3 pixels directly: huge cost per reverse step
- Train a VAE to compress images into a small latent grid, e.g. 64x64x4
- Run the entire diffusion process in that latent space instead
- Only the final step decodes the latent back to pixels
- Roughly an order of magnitude in compute, small usually-imperceptible cost

<!-- speaker note: Draw the pipeline: image -> VAE encoder -> latent -> diffusion -> latent -> VAE decoder -> image. -->

---

## The architecture shift: U-Net to DiT

|  | U-Net | DiT (Diffusion Transformer) |
|---|---|---|
| Core op | convolution + skip connections | self-attention over patch tokens |
| Inductive bias | strong | weak - learns structure from data |
| Scaling behaviour | plateaus | follows transformer scaling laws |
| Used by | SD 1.x/2.x | Sora, SD3, Flux, most 2024+ systems |


<!-- speaker note: Same story as CNN-to-transformer in vision classification - the field has seen this shift before. -->

---

## Text-to-image, end to end

- Text encoder (CLIP, or a full LLM/T5 encoder in newer systems)
- Cross-attention: image latent patches query the text token embeddings
- Scheduler: picks the noise schedule and step-update rule, swappable
- Negative prompts are CFG again - guided away from a named unwanted thing
- Seed + deterministic sampler = reproducible image, the basis of seed hunting

<!-- speaker note: CLIP's 77-token limit and bag-of-concepts style is why newer systems add a T5/LLM encoder. -->

---

## img2img, inpainting, ControlNet

- img2img: start from a real image partially noised, not from pure noise
- Inpainting: reset unmasked pixels to their correct noise level each step
- ControlNet: a trained side-network injects a structural signal per step
- Structural signal examples: edge map, depth map, pose skeleton
- Decouples what (text controls content) from where (control signal controls layout)

<!-- speaker note: ControlNet is arguably the single biggest production unlock - text alone is a poor spatial interface. -->

---

## Video and audio: same idea, harder substrate

- Independent per-frame diffusion fails: flicker, morphing, no agreement
- Fix: temporal attention, or spacetime patches (Sora's approach)
- A 5-second clip at 24fps is roughly 120x an image's worth of pixels
- Audio: autoregressive codec tokens vs diffusion over a mel-spectrogram
- Voice cloning needs only seconds of reference audio in modern systems

<!-- speaker note: Consistency failures - flicker, an object changing identity - are video's version of six-fingered hands. -->

---

## Multimodal models: understanding vs generating

- LLaVA recipe: frozen CLIP vision encoder + small projection + an LLM
- Projected image patches become extra tokens in the LLM's input sequence
- The LLM's attention does not care what produced a token's embedding
- Seeing and generating are separate capabilities - do not conflate them
- Frontier direction: native multimodal training on interleaved tokens from scratch

<!-- speaker note: Ask two separate questions about any system: can it see what I upload, and can it make me an image. -->

---

## Evaluation: every metric here is unsatisfying

| Metric | Measures | Why it is not enough |
|---|---|---|
| FID | distance between real/generated feature distributions | gameable, multiple incompatible implementations |
| CLIP score | image-prompt cosine similarity | rewards on-topic over correct |
| Human preference / Elo | pairwise which-is-better votes | expensive, slow, rater-pool bias |
| Inception Score | class-confidence + diversity | mostly superseded by FID |


<!-- speaker note: Same unsolved problem as Module 15 for text - no scalar captures realism, fidelity, diversity, and correctness at once. -->

---

## The diagnostic that still works

> **Look at hands and text - both remain reliable tells for diffusion-generated content.**

- Hands: high-degrees-of-freedom structure, hard to learn from 2D projections
- Rendered text: exact discrete symbols from a continuous process, no notion of spelling
- Hallucinated detail is the image analogue of an LLM hallucination

<!-- speaker note: Overall photorealism is hard to distinguish from real photos - hands and text still give it away. -->

---

## Failure modes, provenance, and the law

- Mode collapse (GANs): sample 100 seeds, look for near-duplicates
- C2PA metadata and invisible watermarks (SynthID) are friction, not guarantees
- Deepfakes and voice cloning push impersonation to near-zero marginal cost
- Training data licensing and output copyright are two separate open questions
- US Copyright Office: bare prompt-and-click output is not copyrightable

<!-- speaker note: C2PA metadata is stripped by any tool that does not preserve it, including a plain screenshot. -->

---

## Your exit check

- Run code/diffusion_from_scratch.py and code/guidance_and_sampling.py unmodified
- Explain every printed number: forward std, denoiser MSE floor, DDIM steps, guidance sweep
- Sketch the DDPM training loop and the CFG sampling equation on a whiteboard, unaided
- Then: Module 06 - AI Agents

<!-- speaker note: The whiteboard sketch is the real test - if the equation only lives in the code, you are not done yet. -->

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
