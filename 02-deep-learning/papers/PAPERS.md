# 📄 Papers — Deep Learning

`bash ../_tools/fetch_papers.sh 02-deep-learning` downloads the arXiv PDFs below into this folder.

## The canon (read in this order)

| # | Paper | Year | Why it matters | Link |
|---|---|---|---|---|
| 1 | **ImageNet Classification with Deep CNNs (AlexNet)** — Krizhevsky, Sutskever, Hinton | 2012 | The paper that started the deep learning era. GPUs + ReLU + dropout + data. | [PDF](https://proceedings.neurips.cc/paper_files/paper/2012/file/c399862d3b9d6b76c8436e924a68c45b-Paper.pdf) |
| 2 | **Deep Residual Learning (ResNet)** — He et al. | 2015 | `F(x) + x`. Made 100+ layers trainable. Lives inside every transformer. | [arXiv:1512.03385](https://arxiv.org/abs/1512.03385) |
| 3 | **Batch Normalization** — Ioffe & Szegedy | 2015 | Normalisation as a training stabiliser; the "internal covariate shift" story was later disputed — read the critique too. | [arXiv:1502.03167](https://arxiv.org/abs/1502.03167) |
| 4 | **Layer Normalization** — Ba, Kiros, Hinton | 2016 | Batch-independent normalisation — what transformers actually use. | [arXiv:1607.06450](https://arxiv.org/abs/1607.06450) |
| 5 | **Adam: A Method for Stochastic Optimization** — Kingma & Ba | 2014 | The default optimizer. | [arXiv:1412.6980](https://arxiv.org/abs/1412.6980) |
| 6 | **Decoupled Weight Decay Regularization (AdamW)** — Loshchilov & Hutter | 2017 | The fix that trains every modern LLM. | [arXiv:1711.05101](https://arxiv.org/abs/1711.05101) |
| 7 | **Dropout** — Srivastava et al. | 2014 | Regularisation by random ablation. | [PDF](https://jmlr.org/papers/volume15/srivastava14a/srivastava14a.pdf) |

## Going deeper

| Paper | Year | Takeaway | Link |
|---|---|---|---|
| Long Short-Term Memory — Hochreiter & Schmidhuber | 1997 | Gating lets gradients survive long sequences | [PDF](https://www.bioinf.jku.at/publications/older/2604.pdf) |
| Sequence to Sequence Learning with Neural Networks — Sutskever et al. | 2014 | Encoder–decoder; the shape of machine translation | [arXiv:1409.3215](https://arxiv.org/abs/1409.3215) |
| Neural Machine Translation by Jointly Learning to Align and Translate — Bahdanau et al. | 2014 | **Attention is invented here**, three years before the transformer | [arXiv:1409.0473](https://arxiv.org/abs/1409.0473) |
| Understanding the difficulty of training deep feedforward networks — Glorot & Bengio | 2010 | Xavier initialization | [PDF](https://proceedings.mlr.press/v9/glorot10a/glorot10a.pdf) |
| Delving Deep into Rectifiers (He init, PReLU) — He et al. | 2015 | The ReLU-appropriate init | [arXiv:1502.01852](https://arxiv.org/abs/1502.01852) |
| Auto-Encoding Variational Bayes (VAE) — Kingma & Welling | 2013 | Probabilistic latent spaces → Module 05 | [arXiv:1312.6114](https://arxiv.org/abs/1312.6114) |
| Random Search for Hyper-Parameter Optimization — Bergstra & Bengio | 2012 | Why grid search wastes your budget | [PDF](https://jmlr.org/papers/volume13/bergstra12a/bergstra12a.pdf) |
| Mixed Precision Training — Micikevicius et al. | 2017 | bf16/fp16 training, loss scaling | [arXiv:1710.03740](https://arxiv.org/abs/1710.03740) |
| Bag of Tricks for Image Classification — He et al. | 2018 | The unglamorous tweaks that actually move accuracy | [arXiv:1812.01187](https://arxiv.org/abs/1812.01187) |
| A ConvNet for the 2020s (ConvNeXt) — Liu et al. | 2022 | CNNs modernised; a fair fight against transformers | [arXiv:2201.03545](https://arxiv.org/abs/2201.03545) |
| Deep Learning (Nature review) — LeCun, Bengio, Hinton | 2015 | The field's own summary of itself | [DOI](https://www.nature.com/articles/nature14539) |

## Free books
| Book | Link |
|---|---|
| **Dive into Deep Learning (D2L)** — interactive, PyTorch/JAX/TF | https://d2l.ai/ |
| **Deep Learning** — Goodfellow, Bengio, Courville | https://www.deeplearningbook.org/ |
| **Neural Networks and Deep Learning** — Michael Nielsen (best backprop chapter anywhere) | http://neuralnetworksanddeeplearning.com/ |
| **Understanding Deep Learning** — Simon Prince (2023, free PDF + notebooks) | https://udlbook.github.io/udlbook/ |
| **The Little Book of Deep Learning** — François Fleuret | https://fleuret.org/francois/lbdl.html |
| **Probabilistic ML: Advanced Topics** — Murphy | https://probml.github.io/pml-book/book2.html |
