# Aurika Visual ReID Tracker Upgrade Report
**Phase 18 TAPP Program**

## 1. Deprecated ImageNet Backbone
- **Identified Flaw:** The tracker previously loaded a default ResNet-18 trained on natural object categories, leading to poor visual differentiation of human identities.
- **Action Taken:** Integrated direct support for `torchreid` person ReID backbones (specifically the OSNet x1_0 architecture).

## 2. Real ReID Model Configuration
- **Model Architecture:** OSNet (Omni-Scale Network) designed for multi-scale feature learning on person re-identification.
- **Preprocessing:** Bounding box crops are normalized using standard person-identity dimensions (`256x128` pixels).
- **Embedding Normalization:** Features are L2 normalized, ensuring that cosine similarity is mapped mathematically as:
  $$d(a, b) = 1.0 - \langle a, b \rangle$$
- **GPU Acceleration:** Enabled automatic GPU inference falls-back to CPU execution if CUDA is absent.
- **Fallback Verification:** If the `torchreid` library fails to load or weights cannot be fetched locally, the system falls back to a standard model while explicitly marking the backbone as `[EXPERIMENTAL_BACKBONE]` to guarantee transparency.
