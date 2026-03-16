try:
    import torch
    from diffusers import AutoPipelineForText2Image
    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False
from ..config import settings

_pipe = None


def _get_device() -> str:
    if not _TORCH_AVAILABLE:  # pragma: no cover
        raise RuntimeError("torch is not installed; run the worker container for image generation")
    return "cuda" if torch.cuda.is_available() else "cpu"


def _get_dtype():
    if not _TORCH_AVAILABLE:  # pragma: no cover
        raise RuntimeError("torch is not installed; run the worker container for image generation")
    return torch.float16 if torch.cuda.is_available() else torch.float32


def get_pipe():
    global _pipe
    if not _TORCH_AVAILABLE:  # pragma: no cover
        raise RuntimeError("torch is not installed; run the worker container for image generation")
    if _pipe is None:
        device = _get_device()
        dtype = _get_dtype()
        _pipe = AutoPipelineForText2Image.from_pretrained(
            settings.MODEL_ID,
            torch_dtype=dtype,
        )
        _pipe.to(device)
        if device == "cuda":
            _pipe.enable_attention_slicing()
    return _pipe


def generate_image(prompt: str, width: int, height: int, steps: int, guidance: float, out_path: str) -> str:
    pipe = get_pipe()
    img = pipe(
        prompt,
        num_inference_steps=steps,
        guidance_scale=guidance,
        width=width,
        height=height
    ).images[0]
    img.save(out_path)
    return out_path


# Apply torch.inference_mode() only when torch is available
if _TORCH_AVAILABLE:
    generate_image = torch.inference_mode()(generate_image)  # type: ignore[assignment]
