# 🔗 Resources — Generative AI

## Courses (free)
| Course | Who it's for | Link |
|---|---|---|
| **Hugging Face — Diffusion Models Course** | The direct sequel to this module: hands-on `diffusers` from DDPM basics through Stable Diffusion internals | https://huggingface.co/learn/diffusion-course |
| **Hugging Face — Computer Vision Course** | Broader CV grounding, including generative sections | https://huggingface.co/learn/computer-vision-course |
| **fast.ai — Practical Deep Learning, Part 2** | Builds Stable Diffusion from its components, top-down, code-first | https://course.fast.ai/Lessons/part2.html |
| **Stanford CS236 — Deep Generative Models** | The rigorous treatment: VAEs, GANs, flows, diffusion, with the math | https://deepgenerativemodels.github.io/ |
| **MIT 6.S183 — Generative AI with Diffusion Models** | Focused university course, lecture notes + labs | https://mit-6s183.github.io/ |
| **DeepLearning.AI — How Diffusion Models Work** | Short, practical, by the Hugging Face diffusers team | https://www.deeplearning.ai/short-courses/how-diffusion-models-work/ |
| **DeepLearning.AI — Building Systems with the ChatGPT API / Multimodal RAG** courses | Practical LLaVA-style multimodal pipelines | https://www.deeplearning.ai/short-courses/ |

## Repositories worth cloning
| Repo | What's inside |
|---|---|
| https://github.com/huggingface/diffusers | The production diffusion library — DDPM/DDIM/DPM-Solver schedulers, pipelines for SD/SDXL/SD3/Flux, ControlNet, all in readable Python |
| https://github.com/CompVis/stable-diffusion | The original Stable Diffusion (v1) research repo — read this to see notes/01's latent-diffusion equations as actual code |
| https://github.com/Stability-AI/stablediffusion | Stability AI's SD 2.x release repo |
| https://github.com/AUTOMATIC1111/stable-diffusion-webui | The most widely used community UI — samplers, ControlNet, LoRA, inpainting, all exposed as knobs |
| https://github.com/comfyanonymous/ComfyUI | Node-graph UI for diffusion pipelines — the best way to *see* the text-to-image pipeline diagram in notes/02 §1 as a literal graph you wire up |
| https://github.com/openai/CLIP | Reference CLIP implementation and pretrained checkpoints |
| https://github.com/haotian-liu/LLaVA | Reference LLaVA implementation — the recipe in notes/02 §4.1, in code |
| https://github.com/facebookresearch/DiT | Reference Diffusion Transformer implementation (Peebles & Xie) |
| https://github.com/lucidrains/denoising-diffusion-pytorch | A clean, minimal PyTorch DDPM/DDIM — the natural next step up from `code/diffusion_from_scratch.py` |
| https://github.com/facebookresearch/audiocraft | MusicGen and AudioGen — the audio generation family from notes/02 §3 |

## Datasets and pretrained checkpoints
| Resource | Why | Where |
|---|---|---|
| LAION / LAION-Aesthetics | The web-scale image-text dataset behind most open text-to-image models — read the licensing discussion in notes/02 §7 before assuming you can use it commercially | https://laion.ai/ |
| Hugging Face Hub — models | Pretrained diffusion, CLIP, and VLM checkpoints, one line to load | https://huggingface.co/models |
| Papers with Code — Image Generation | Leaderboards with FID numbers so you can see the metric from notes/02 §5 in the wild | https://paperswithcode.com/task/image-generation |

## Tools
| Tool | Use |
|---|---|
| Hugging Face `diffusers` | The library — build a pipeline in under 10 lines once you've done the labs here |
| ComfyUI / A1111 webui | Visual, no-code experimentation with samplers, guidance scale, ControlNet |
| `torchmetrics` (`FrechetInceptionDistance`, `CLIPScore`) | Compute the metrics notes/02 §5 critiques, so you can see their limits yourself |
| C2PA Content Credentials tools | Inspect/attach provenance metadata — https://c2pa.org/ |
| Google SynthID | The most widely deployed invisible watermark — https://deepmind.google/technologies/synthid/ |

## Communities
- Hugging Face forums (diffusion-models category) — https://discuss.huggingface.co/
- r/StableDiffusion — https://www.reddit.com/r/StableDiffusion/
- r/MachineLearning — https://www.reddit.com/r/MachineLearning/
- Papers with Code — https://paperswithcode.com/
- EleutherAI Discord (open generative-model research) — https://www.eleuther.ai/

## Cheat sheets
- Hugging Face `diffusers` scheduler comparison — https://huggingface.co/docs/diffusers/using-diffusers/schedulers
- Also see [../../_shared/cheatsheets/](../../_shared/cheatsheets/)
