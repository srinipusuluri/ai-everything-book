# Deep Dive — Pipelines, Multimodality, and Honest Evaluation

Note 01 covered the diffusion mechanism. This note covers what you actually build with it: the end-to-end
text-to-image pipeline, video and audio generation, vision-language models, how to evaluate any of this
(badly), and the failure modes and legal exposure you're signing up for.

---

## 1. Text-to-image, end to end

```
prompt: "a corgi astronaut, oil painting, dramatic lighting"
    |
    v
[text encoder]  (CLIP text tower, or a full LLM/T5 encoder in newer systems)
    |  a sequence of token embeddings, not one vector
    v
[diffusion model: U-Net or DiT]  <-- negative-prompt embedding also feeds in (CFG)
    |  cross-attention: every latent patch attends to every text token
    |  repeated for N sampler steps (the scheduler picks step sizes / noise schedule)
    v
latent z' (denoised) --[VAE decoder]--> pixels
```

- **Text encoder.** Original Stable Diffusion used CLIP's text tower — pretrained via contrastive
  text/image alignment (Module 08 covers CLIP in the retrieval context), so its representations already
  carry visual-semantic structure. Newer systems (SD3, DALL-E 3, Imagen) add a full T5/LLM encoder in
  parallel because CLIP's 77-token limit and bag-of-concepts style struggles with compositional prompts —
  "a red cube on a blue sphere, left of a green cylinder" routinely gets attributes bound to the wrong object.
- **Cross-attention** is where text meaning enters the image: text tokens as keys/values, image-latent
  patches as queries. Same mechanism as Module 03, different job.
- **The scheduler** governs the noise schedule and step-update rule (DDIM, DPM-Solver++, Euler...) — swappable
  independently of the model weights, which is why one checkpoint behaves differently under different
  schedulers in ComfyUI/A1111.
- **Negative prompts** are not a separate mechanism — they're CFG (note 01 §2.4) where the "unconditional"
  branch is replaced by a second *conditional* branch on the negative text ("blurry, extra fingers,
  watermark"), and guidance pushes away from that instead of away from nothing. That's why negative prompts
  suppress specific defects so effectively: you're doing guidance twice, toward the wanted thing and away
  from a named unwanted one.
- **Seeds.** Initial noise `x_T` comes from a seeded RNG. With a deterministic sampler (DDIM), same seed +
  prompt + settings = same image — the basis of "seed hunting" as a real workflow.
- **img2img** starts from a real image partially noised to some intermediate `x_t` (via note 01's closed-form
  `q(x_t|x_0)`) instead of pure noise, then runs the reverse process from there. Lower starting `t` stays
  closer to the original; higher `t` gives more creative freedom.
- **Inpainting** is img2img where, at every reverse step, the *unmasked* pixels are reset to their correctly
  noised original values — the model can only "invent" inside the mask while staying consistent outside it.
- **ControlNet** (Zhang et al., 2023) adds an auxiliary network, trained alongside a frozen base model, that
  injects a structural signal (edge map, depth map, pose skeleton) into intermediate activations at every
  step. This decouples *what* (text controls content) from *where/how* (the control signal controls
  composition) — the single biggest unlock for production pipelines, because text alone is a poor interface
  for precise spatial control.

---

## 2. Video: same idea, harder substrate

Diffusing each frame independently fails immediately — independently sampled frames have no reason to agree
frame-to-frame, so you get flicker, morphing objects, swimming backgrounds. Fixes make **time** a modeled
dimension:

- **Temporal attention/convolution** layers interleaved with spatial ones, so the model looks across frames
  while denoising and keeps frame `t` and `t+1` in agreement.
- **Spatiotemporal transformers** (Sora's approach): tokenize the whole clip as spacetime patches — a small
  cube of `(height, width, time)` rather than just `(height, width)` — and let self-attention handle spatial
  and temporal consistency uniformly. The DiT idea from note 01, with an extra axis.
- **Compute cost scales badly.** A 5-second, 24fps clip is ~120 frames — naively 120x an equivalent image's
  pixels, plus long-range temporal attention on top. This is why, as of 2026, video generation remains an
  order of magnitude more expensive per second than an equivalent-quality image, and why most production
  tools cap clip length and resolution well below text-to-image defaults.
- **Consistency failures are the diagnostic.** Temporal flicker, an object subtly changing identity mid-clip,
  physically implausible motion (objects interpenetrating, water not conserving volume) are video's version
  of six-fingered hands (§4): the model has learned appearance far better than physics.

## 3. Audio: three problems wearing one name

- **Text-to-speech.** Two families: **autoregressive** token models (predict discrete audio-codec tokens one
  at a time — Module 04's next-token idea over an audio vocabulary from a neural codec like EnCodec) and
  **diffusion** models that denoise a mel-spectrogram or waveform conditioned on text and a voice embedding.
  Autoregressive TTS tends to sound more naturally prosodic but is slower and can drift/repeat; diffusion TTS
  is more controllable and parallel but needs careful conditioning to avoid a flat cadence.
- **Music generation.** Same two families (MusicGen: autoregressive over discrete tokens; early Riffusion
  literally ran image diffusion on spectrogram images). Music adds a harder long-range structure problem —
  a coherent verse-chorus-verse arc over minutes is a much longer dependency than a spoken sentence, and it's
  where current systems are weakest.
- **Voice cloning.** Condition TTS on a short reference clip (seconds, in modern few-shot systems) to extract
  a speaker embedding, then generate new speech in that voice. The misuse surface is immediate: a few seconds
  of anyone's voice — a voicemail, a video call — is enough for a usable clone. Direct line to
  `../../13-ai-security/` (voice-based social engineering at scale).

---

## 4. Multimodal models: understanding vs. generating

Everything above *generates*. A separate capability is a model that *understands* images/audio well enough
to reason about them — a different architecture problem. Conflating "can make pictures" with "can see" is a
common, consequential mistake.

### 4.1 The LLaVA-style recipe

```
image --[frozen/lightly-tuned vision encoder, e.g. CLIP ViT]--> patch embeddings
                                                                       |
                                                    [projection: linear or small MLP]
                                                                       |
                                                                       v
text tokens --[LLM token embeddings]--> concatenated sequence --[LLM, architecture unchanged]
```

The trick (LLaVA, Liu et al. 2023, and most 2023-era VLMs) is almost embarrassingly simple: run an image
through a pretrained vision encoder (usually a CLIP ViT, already aligned to language via contrastive
training) to get patch embeddings, learn a small **projection** into the LLM's own token-embedding space,
and splice those projected "tokens" into the input sequence next to text tokens. The frozen (or lightly
tuned) LLM's attention doesn't care what produced a token's embedding — it attends over the mixed sequence
either way. What looks like a breakthrough ("the LLM can see!") is architecturally a small addition on top
of work you already understand: a strong LLM (Modules 03-04) plus a strong aligned image encoder (CLIP).

### 4.2 Understanding and generation don't transfer

A model that accurately describes a photo (understanding, via an encoder feeding an LLM) has no built-in
ability to *produce* a photo — that needs a generative decoder (diffusion, or an autoregressive image-token
decoder) trained on a completely different objective. Historically these lived in separate products from the
same lab (GPT-4V understood; DALL-E generated). Ask "can it see what I upload" and "can it make me an image"
as two unrelated questions about any given system.

### 4.3 Where native multimodality is heading

The frontier direction (Gemini's natively multimodal training, GPT-4o's unified architecture, Chameleon)
collapses the encoder-plus-projection pattern into a **single model trained end-to-end** on interleaved
text/image/audio tokens from the start, rather than grafting vision onto a text-pretrained LLM. The bet:
cross-modal structure learned *during* pretraining generalizes better than structure bolted on after. As of
2026 the gap is closing but not closed — bolted-on VLMs still lead on raw language reasoning (they inherit a
mature text-only LLM); native multimodal models lead on tasks needing tight cross-modal binding (precise
visual grounding, images that respect a subtle textual constraint).

---

## 5. Evaluation — and why every metric here is unsatisfying

| Metric | Measures | Why it's not enough |
|---|---|---|
| **FID** | distance between real vs. generated feature distributions, via a pretrained Inception net | distributional similarity, not per-image quality or prompt fidelity; gameable; multiple incompatible "standard" implementations circulate |
| **CLIP score** | cosine similarity between image and prompt CLIP embeddings | rewards on-topic over correct — wrong object count or spatial relation can still score well if thematically close |
| **Human preference / Elo** | pairwise "which is better" votes, aggregated | expensive, slow, rater-pool bias; answers "which do people like," not "which is factually/physically correct" |
| **Inception Score** | class-confidence + diversity under an ImageNet classifier | mostly superseded by FID, still cited in older papers |

None of these are satisfying because "good" for a generative model is multi-dimensional — realism, prompt
fidelity, diversity, aesthetics, physical/factual correctness — and no scalar captures the mix a real product
needs. This is the same unsolved problem `../../15-ai-evals/` wrestles with for text: LLM-as-judge, human
preference, and benchmark suites are all imperfect proxies for "is this actually good." Generative
image/audio/video evaluation is arguably the harder version, because the space of "correct" outputs for a
creative prompt is legitimately not single-valued.

**The diagnostic that actually works: look at hands and text.** Diffusion models learn statistical
regularities from pixels; hands have high-degrees-of-freedom structure that's hard to learn robustly from 2D
projections, and rendered text requires exact discrete symbol sequences from a continuous generative
process with no notion of "spelling." Both remain reliable tells for "likely diffusion-generated" well into
2026, even as overall photorealism has become hard to distinguish from real photography otherwise.

---

## 6. Failure modes, provenance, misuse

- **Mode collapse (GANs).** The generator finds a small set of outputs that reliably fool the discriminator
  and stops exploring. Diagnostic: sample 100 seeds and look for near-duplicates. Diffusion is far more
  resistant by construction — no adversarial game to "win" by narrowing.
- **Hallucinated detail** is the image analogue of an LLM hallucination: confidently rendered detail that's
  locally plausible and globally wrong (garbled not-quite-text on a sign, a sixth finger, an architecturally
  impossible building). Same root cause as Module 04 §9: trained to produce *plausible* continuations of the
  noising process, not to verify correctness against ground truth.
- **Watermarking and provenance — C2PA.** The Coalition for Content Provenance and Authenticity standard
  embeds cryptographically signed metadata ("Content Credentials") recording how an image was created/edited.
  Invisible statistical watermarks (Google's SynthID is the most deployed) embed a signal in the
  pixel/token distribution that survives resize/compress/screenshot and is detectable without the original.
  **Neither is a complete solution**: C2PA metadata is trivially stripped by any tool that doesn't preserve
  it (a plain screenshot does), and no deployed watermark is provably robust against a motivated adversary
  who wants it gone — both are friction layers, not cryptographic guarantees.
- **Deepfakes and misuse.** Voice cloning (§3) and face/video synthesis push impersonation and
  non-consensual synthetic media to near-zero marginal cost. Direct line to `../../13-ai-security/`
  (synthetic-media fraud, cloned-voice social engineering) and `../../12-ai-governance/` (disclosure
  obligations, deployer responsibility, the emerging — in some jurisdictions regulatory — expectation that
  AI-generated content be labeled).

---

## 7. Licensing and copyright — two separate questions

1. **Was the training data licensed?** Most large image models trained on web-scraped datasets (LAION-style)
   whose images weren't individually licensed for this use — the subject of active, unresolved litigation
   across jurisdictions (artists and stock-image companies vs. model providers) as of 2026. The legal theory
   (fair use / text-and-data-mining exceptions vs. infringement) hasn't settled uniformly.
2. **Who owns the output, and is it infringing?** The US Copyright Office's current position: purely
   AI-generated output without sufficient human creative authorship is **not copyrightable** — you can't
   register a bare prompt-and-click image. Separately, an output can *infringe* an existing work (a
   recognizable protected character, a style tightly tied to one living artist, memorized training data)
   regardless of who or what generated it — generativeness isn't an infringement exemption on the output side.

**Do not assume "the model made it" resolves either question.** Check the license terms of the specific
model/API (many commercial APIs contractually grant you usage rights over outputs regardless of the
training-data question — that's the provider absorbing risk, not proof the underlying question is settled),
and treat outputs resembling a specific living artist's style or a copyrighted character as real legal
exposure. Ties directly to `../../14-ai-compliance/` for building an audit trail around model/data
provenance and usage terms.

---

## 8. Forward and backward links

| Idea here | Where it connects |
|---|---|
| CLIP-style contrastive alignment | Module 08 — the same text-image alignment powers multimodal RAG |
| Evaluation being unsatisfying | Module 15 — the text-generation version of the identical problem |
| Deepfakes, voice cloning misuse | Module 13 — AI security, social-engineering threat models |
| Disclosure, provenance obligations | Module 12 — AI governance |
| Training-data licensing, output copyright | Module 14 — AI compliance, audit-ready evidence |
| ControlNet-style external conditioning | Module 06/07 — agents/tools calling generation APIs with structured control inputs |
| Diffusion mechanism (forward/reverse/CFG/DiT) | [notes/01-core-concepts.md](01-core-concepts.md) |
