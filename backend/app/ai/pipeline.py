try:
    import torch
    from diffusers import AutoPipelineForText2Image
    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False
from PIL import Image as _PILImage
from ..config import settings

_pipe = None

# Minimum generation size for acceptable image quality
_MIN_GEN_SIZE = 256

# Asset type → (width, height) per size tier
_ASSET_DIMENSIONS: dict[str, dict[str, tuple[int, int]]] = {
    "character":  {"small": (256, 256), "medium": (512, 512),  "large": (1024, 1024)},
    "item":       {"small": (256, 256), "medium": (256, 256),  "large": (512, 512)},
    "icon":       {"small": (256, 256), "medium": (256, 256),  "large": (512, 512)},
    "background": {"small": (512, 256), "medium": (1024, 512), "large": (1024, 1024)},
    "ui_element": {"small": (256, 128), "medium": (512, 256),  "large": (1024, 512)},
}

# Asset type → descriptive prompt prefix for game context
_ASSET_PROMPT_PREFIXES: dict[str, str] = {
    "character":  "2D mobile game character sprite, isolated on white background,",
    "item":       "2D mobile game item sprite, isolated on white background,",
    "icon":       "mobile game icon, flat design, isolated on white background,",
    "background": "mobile game background scene, seamless parallax-ready,",
    "ui_element": "mobile game UI element, flat design, clean edges,",
}


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


def generate_spritesheet(
    prompt: str,
    rows: int,
    cols: int,
    frame_width: int,
    frame_height: int,
    steps: int,
    guidance: float,
    out_path: str,
) -> str:
    """Generate a sprite sheet by creating rows*cols frames and stitching them into a grid.

    Each frame is generated at max(_MIN_GEN_SIZE, frame_width) for quality then
    resized to the requested frame dimensions before being placed in the sheet.
    """
    pipe = get_pipe()
    gen_w = max(_MIN_GEN_SIZE, frame_width)
    gen_h = max(_MIN_GEN_SIZE, frame_height)

    sheet = _PILImage.new("RGBA", (cols * frame_width, rows * frame_height))

    for row in range(rows):
        for col in range(cols):
            raw = pipe(
                prompt,
                num_inference_steps=steps,
                guidance_scale=guidance,
                width=gen_w,
                height=gen_h,
            ).images[0].convert("RGBA")

            if raw.size != (frame_width, frame_height):
                raw = raw.resize((frame_width, frame_height), _PILImage.LANCZOS)

            sheet.paste(raw, (col * frame_width, row * frame_height))

    sheet.save(out_path, format="PNG")
    return out_path


def generate_game_asset(
    prompt: str,
    asset_type: str,
    size: str,
    style: str,
    steps: int,
    guidance: float,
    out_path: str,
) -> str:
    """Generate a mobile game asset with type-specific prompt engineering.

    Prepends a context prefix and appends the requested style to the user's
    prompt so the model produces output that fits common mobile game workflows.
    """
    prefix = _ASSET_PROMPT_PREFIXES.get(asset_type, "2D mobile game asset,")
    full_prompt = f"{prefix} {style}, {prompt}"

    dims = _ASSET_DIMENSIONS.get(asset_type, {}).get(size, (512, 512))
    width, height = dims

    return generate_image(
        prompt=full_prompt,
        width=width,
        height=height,
        steps=steps,
        guidance=guidance,
        out_path=out_path,
    )


# Apply torch.inference_mode() only when torch is available
if _TORCH_AVAILABLE:
    generate_image = torch.inference_mode()(generate_image)  # type: ignore[assignment]
    generate_spritesheet = torch.inference_mode()(generate_spritesheet)  # type: ignore[assignment]
    generate_game_asset = torch.inference_mode()(generate_game_asset)  # type: ignore[assignment]
