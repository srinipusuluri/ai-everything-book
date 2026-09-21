---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #6366F1; }
  section { font-size: 24px; }
---

# Deep Learning

### Stop choosing features. Start learning them.

**Module 02** · AI End-to-End Learning Track

---

## One neuron is logistic regression

- z = w.x + b, then a = phi(z) -- exactly Module 01
- Stack neurons into layers, layers into a network
- Without the nonlinearity, 50 layers collapse to one linear map
- Depth is an EFFICIENCY argument, not an expressiveness one
- Universal approximation says 'possible', not 'findable' or 'generalises'

<!-- speaker note: Kill the mystique in the first two minutes: they already built a neuron last module. -->

---

## Activation functions

| Function | Range | Use it |
|---|---|---|
| ReLU  max(0,z) | [0, inf) | default hidden layer |
| GELU  z*Phi(z) | R | transformers -- BERT, GPT |
| SwiGLU (gated) | R | Llama-class feed-forward blocks |
| Sigmoid | (0,1) | OUTPUT only, binary |
| Softmax | simplex | OUTPUT only, multi-class |
| Tanh | (-1,1) | LSTM gates |


<!-- speaker note: Sigmoid's gradient maxes at 0.25. Ten stacked layers gives 0.25^10 = 1e-6. That is the vanishing gradient problem in one number. -->

---

## Backprop is four equations

- delta_L = dJ/da * phi'(z_L)   at the output
- delta_l = (W_{l+1}^T delta_{l+1}) * phi'(z_l)   propagate back
- dJ/dW_l = delta_l a_{l-1}^T
- dJ/db_l = delta_l
- Forward caches; backward reuses the cache. That is all autograd does

<!-- speaker note: Write these on a board. Then show code/backprop_from_scratch.py implementing exactly them. -->

---

## Why softmax pairs with cross-entropy

> **dJ/dz = p - y. Every exponential and its derivative cancels.**

- Frameworks fuse the two ops for speed AND numerical stability
- cross_entropy() takes LOGITS, not probabilities
- Common bug: softmax applied twice -- trains, then plateaus early

<!-- speaker note: This is the single most common silent bug in a beginner's PyTorch model. -->

---

## Initialization breaks first

- All-zero weights: every neuron in a layer stays identical forever
- Symmetry must be broken -- that is the whole point of random init
- Xavier/Glorot: var = 2/(fan_in + fan_out), pair with tanh
- He/Kaiming: var = 2/fan_in, pair with ReLU -- PyTorch default
- Goal: keep activation variance stable across depth

---

## Pick the architecture the data's structure demands

| Structure in data | Architecture | Prior it encodes |
|---|---|---|
| none (tabular) | MLP | nothing -- and that's fine |
| spatial / local | CNN | locality + translation equivariance |
| sequential | RNN / LSTM | order, recurrence |
| sequential, parallelisable | Transformer | all-pairs attention (Module 03) |
| compress + reconstruct | Autoencoder / VAE | a usable latent space (Module 05) |


<!-- speaker note: The RNN's fatal flaw -- inherent sequentiality -- is exactly what the transformer removed. -->

---

## Embeddings: the idea that unlocks the rest of the track

- A learned dense vector for a discrete item
- 50,000 words -> a 50,000 x 768 lookup table
- Trained end-to-end, similar items land near each other
- Powers: LLM input layers, vector search, recsys, diffusion latents
- If you take ONE idea from this module, take this one

<!-- speaker note: Explicitly flag the forward links to Modules 03, 04 and 08. -->

---

## Residual connections

- output = F(x) + x
- The identity path is a gradient highway back to early layers
- ResNet 2015: ~20 usable layers became 152
- Every transformer block is two residual blocks
- You cannot read a transformer diagram without this

---

## BatchNorm vs LayerNorm vs RMSNorm

| Norm | Normalises across | Where used |
|---|---|---|
| BatchNorm | the batch, per feature | CNNs; breaks at tiny batch sizes |
| LayerNorm | features, per example | transformers -- batch independent |
| RMSNorm | features, no mean-centring | Llama-class LLMs -- cheaper |


<!-- speaker note: Pre-LN vs Post-LN placement is why modern transformers train without heroics. -->

---

## The training loop, stripped to essentials

- zero_grad -> forward -> loss -> backward -> clip -> step -> schedule
- Then: eval, checkpoint the BEST (not the last)
- Bug 1: no zero_grad -- gradients silently accumulate
- Bug 2: no model.eval() -- dropout on during validation, metrics are noise
- Bug 3: no torch.no_grad() at eval -- memory blows up for nothing

<!-- speaker note: These three account for most silent failures in student code. -->

---

## The 15-minute debugging checklist

- 1. Can you overfit 10 examples to ~zero loss? If not it's a CODE bug
- 2. Is loss at step 0 equal to ln(K)? If not, output layer or loss is wrong
- 3. Print shapes -- a silent (B,1) vs (B,) broadcast gives a (B,B) loss
- 4. Print 10 inputs AFTER the full transform pipeline
- 5. Print per-layer grad norms -- all-zero early layers = vanishing or frozen
- 6. LR sweep 1e-5..1e-2 for 100 steps; take the largest that decreases smoothly

<!-- speaker note: Stop at the first failure. Do not skip step 1; it catches four different bugs at once. -->

---

## Reading a broken run

| Symptom | Cause | Fix |
|---|---|---|
| loss -> NaN | exploding gradients, LR too high | clip to 1.0, lower LR, warmup |
| flat from step 0 | LR too low, broken labels | LR sweep, check label alignment |
| train down, val up | overfitting | dropout, augment, early stop |
| val metric is noise | forgot model.eval() | call .eval(), use no_grad |
| GPU at 30% | data pipeline bound | num_workers, pin_memory, prefetch |


<!-- speaker note: Check GPU utilisation BEFORE optimising the model. Most 'slow training' is a slow DataLoader. -->

---

## Hyperparameters, ranked by how much they matter

- 1. Learning rate -- order of magnitude beats exact value
- 2. Batch size -- set by memory, then scale LR linearly with warmup
- 3. Model size -- bigger wins if you regularise and have data
- 4. Weight decay -- 0.01-0.1 transformers, 1e-4 CNNs
- 5. Schedule -- warmup + cosine decay is the safe default
- Random search beats grid search: most dimensions don't matter

<!-- speaker note: Bergstra & Bengio 2012. Grid search wastes its budget on irrelevant axes. -->

---

## Making it fast and affordable

| Technique | Gain | Cost |
|---|---|---|
| Mixed precision (bf16) | 2-3x | tiny; bf16 safer than fp16 |
| Gradient checkpointing | -40% memory | +30% time |
| torch.compile | 1.3-2x | compile time, graph breaks |
| DataLoader tuning | often the biggest win | none |
| DDP / FSDP | scales across GPUs | complexity, comms |


---

## Transfer learning -- the workflow you reuse forever

- Take a pretrained backbone; replace the task head
- Freeze and train the head (little data), or fine-tune all (more data, small LR)
- Unfreeze gradually with discriminative learning rates
- Same mental model as LLM fine-tuning in Module 04
- LoRA and adapters are parameter-efficient versions of this

<!-- speaker note: Make the Module 04 link explicit -- it saves them a week later. -->

---

## When deep learning is the WRONG answer

- Tabular data under ~100k rows -> gradient boosting
- A regulator needs per-prediction explanations -> start interpretable
- Sub-10ms CPU latency budget -> small model or distillation
- The task is genuinely a rule or a lookup
- Choosing NOT to use deep learning is a senior move

<!-- speaker note: Say this out loud in front of stakeholders. It buys enormous credibility. -->

---

## Exit check

- Train a net on a new dataset and hit a target metric
- Explain every line of your training loop
- Debug a NaN without copying a notebook
- Run code/backprop_from_scratch.py and code/pytorch_training_loop.py
- Next: Module 03 -- Natural Language Processing

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
