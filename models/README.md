# Pretrained image models

## Current retrieval model

`clip-vit-base-patch32-vision-int8.onnx` is the quantized vision encoder from
OpenAI CLIP ViT-B/32. It produces a 512-dimensional semantic image embedding.
The ONNX conversion is published by Xenova for Transformers.js; the original
OpenAI CLIP model is distributed under MIT.

- Conversion: https://huggingface.co/Xenova/clip-vit-base-patch32
- Original model: https://huggingface.co/openai/clip-vit-base-patch32
- Download: https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/main/onnx/vision_model_quantized.onnx
- SHA-256: `583fd1110a514667812fee7d684952aaf82a99b959760c8d7dca7e0ab9839299`

The application center-crops RGB input to 224×224, applies the documented CLIP
mean and standard deviation, runs local CPU inference, L2-normalizes the image
embedding, and compares it with catalog embeddings using cosine similarity.
Uploaded images are processed in memory and are not written to disk.

## Retained baseline model

`mobilenetv2-12.onnx` is retained only so
`scripts/evaluate_image_models.py` can reproduce the before/after comparison.
It is no longer used by the application. The model comes from the official ONNX
Model Zoo under Apache 2.0.

- Source: https://github.com/onnx/models/tree/main/validated/vision/classification/mobilenet
- SHA-256: `c0c3f76d93fa3fd6580652a45618618a220fced18babf65774ed169de0432ad5`
