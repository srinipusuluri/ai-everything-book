# 📄 Papers & Primary Sources — Generative AI

`bash ../_tools/fetch_papers.sh 05-genai` downloads the arXiv PDFs below into this folder.

## The canon (read in this order)

| # | Paper | Year | Why it matters | Link |
|---|---|---|---|---|
| 1 | **Denoising Diffusion Probabilistic Models (DDPM)** — Ho, Jain, Abbeel | 2020 | The paper `code/diffusion_from_scratch.py` implements. Forward/reverse process, the noise-prediction objective, the derivation behind every equation in notes/01. | [arXiv:2006.11239](https://arxiv.org/abs/2006.11239) |
| 2 | **Denoising Diffusion Implicit Models (DDIM)** — Song, Meng, Ermon | 2020 | Deterministic, non-Markovian sampling — the reason production tools sample in 20-50 steps instead of 1000. `code/guidance_and_sampling.py` measures exactly this trade-off. | [arXiv:2010.02502](https://arxiv.org/abs/2010.02502) |
| 3 | **Classifier-Free Diffusion Guidance** — Ho, Salimans | 2022 | The `w`-scaled guidance equation every text-to-image tool exposes as "CFG scale" / "guidance scale." No separate classifier needed — just condition dropout during training. | [arXiv:2207.12598](https://arxiv.org/abs/2207.12598) |
| 4 | **High-Resolution Image Synthesis with Latent Diffusion Models** — Rombach, Blattmann, Lorenz, Esser, Ommer | 2022 | This paper *is* Stable Diffusion: VAE-compressed latent space + diffusion U-Net + cross-attention text conditioning. | [arXiv:2112.10752](https://arxiv.org/abs/2112.10752) |
| 5 | **Scalable Diffusion Models with Transformers (DiT)** — Peebles, Xie | 2022 | Replaces the U-Net backbone with a Vision-Transformer-style architecture; the backbone behind Stable Diffusion 3, Flux, and Sora. | [arXiv:2212.09748](https://arxiv.org/abs/2212.09748) |
| 6 | **Learning Transferable Visual Models From Natural Language Supervision (CLIP)** — Radford et al. | 2021 | Contrastive text-image alignment. Powers the original Stable Diffusion text encoder, the CLIP-score metric (notes/02 §5), and every LLaVA-style vision encoder. Also the retrieval backbone in Module 08. | [arXiv:2103.00020](https://arxiv.org/abs/2103.00020) |
| 7 | **Visual Instruction Tuning (LLaVA)** — Liu, Li, Wu, Lee | 2023 | The recipe notes/02 §4.1 walks through: frozen CLIP encoder + small projection + off-the-shelf LLM. The template nearly every open vision-language model still follows. | [arXiv:2304.08485](https://arxiv.org/abs/2304.08485) |

## Going deeper

| Paper | Year | Takeaway | Link |
|---|---|---|---|
| Generative Adversarial Networks — Goodfellow et al. | 2014 | The original minimax generator-vs-discriminator paper. Read it to understand *why* mode collapse and training instability are structural, not implementation bugs. | [arXiv:1406.2661](https://arxiv.org/abs/1406.2661) |
| Auto-Encoding Variational Bayes (VAE) — Kingma, Welling | 2013 | The direct ancestor of latent diffusion's compression stage. Already in [Module 02's papers](../../02-deep-learning/papers/PAPERS.md) — read it there if you haven't. | [arXiv:1312.6114](https://arxiv.org/abs/1312.6114) |
| Improved Denoising Diffusion Probabilistic Models — Nichol, Dhariwal | 2021 | The cosine noise schedule (lab exercise 2) and learned variance — the paper that took DDPM from "works" to "competitive." | [arXiv:2102.09672](https://arxiv.org/abs/2102.09672) |
| Photorealistic Text-to-Image Diffusion Models with Deep Language Understanding (Imagen) — Saharia et al. | 2022 | Google's case for a large frozen T5 text encoder over CLIP — directly informs why notes/02 §1 says newer systems add an LLM/T5 encoder alongside CLIP. | [arXiv:2205.11487](https://arxiv.org/abs/2205.11487) |
| Video generation models as world simulators (Sora technical report) — OpenAI | 2024 | Spacetime-patch tokenization for video diffusion — the "extra axis on DiT" story in notes/02 §2. No peer-reviewed paper exists; this is the primary source. | [openai.com/research/video-generation-models-as-world-simulators](https://openai.com/research/video-generation-models-as-world-simulators) |
| Adding Conditional Control to Text-to-Image Diffusion Models (ControlNet) — Zhang, Rao, Agrawala | 2023 | Structural conditioning (edge/depth/pose) alongside a frozen base model — decouples *what* from *where*, the production unlock covered in notes/02 §1. | [arXiv:2302.05543](https://arxiv.org/abs/2302.05543) |
| Scaling Rectified Flow Transformers for High-Resolution Image Synthesis (SD3) — Esser et al. | 2024 | Flow matching as diffusion's generalization — what trained Stable Diffusion 3 and Flux; explains the "close cousin" hedge in notes/01 §1. | [arXiv:2403.03206](https://arxiv.org/abs/2403.03206) |
| Consistency Models — Song, Dhariwal, Chen, Sutskever | 2023 | Distill a diffusion model into a 1-4 step sampler — the frontier of attacking diffusion's one real weakness, sampling cost. | [arXiv:2303.01469](https://arxiv.org/abs/2303.01469) |

## How to read a diffusion paper (30 minutes, 3 passes)

1. **Pass 1 (5 min):** what's being diffused (pixels? a VAE latent? spacetime patches?), and what's the
   conditioning signal (text, class label, control map, nothing)?
2. **Pass 2 (15 min):** the sampler. Stochastic or deterministic? How many steps does the paper actually
   report needing, and against what baseline?
3. **Pass 3 (10 min):** the evaluation section. Which of FID / CLIP score / human preference did they use,
   and what does notes/02 §5 say that metric can't tell you? Papers rarely volunteer their metric's blind
   spot — you have to bring it yourself.

Keep a one-paragraph note per paper. In six months the note is worth more than the PDF.
