try:
    import torch
    from diffusers import AutoPipelineForText2Image
    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False
from PIL import Image as _PILImage, ImageEnhance as _PILEnhance
from ..config import settings

_pipe = None

# Minimum generation size for acceptable image quality
_MIN_GEN_SIZE = 256

# Default negative prompt applied to every generation for baseline quality
_DEFAULT_NEGATIVE_PROMPT = (
    "blurry, low quality, noise, grainy, deformed, ugly, distorted, artifacts, "
    "watermark, text, signature, poorly drawn, bad anatomy, duplicate, extra limbs"
)

# Asset type → (width, height) per size tier
_ASSET_DIMENSIONS: dict[str, dict[str, tuple[int, int]]] = {
    # Generic mobile-game assets (original)
    "character":  {"small": (256, 256), "medium": (512, 512),  "large": (1024, 1024)},
    "item":       {"small": (256, 256), "medium": (256, 256),  "large": (512, 512)},
    "icon":       {"small": (256, 256), "medium": (256, 256),  "large": (512, 512)},
    "background": {"small": (512, 256), "medium": (1024, 512), "large": (1024, 1024)},
    "ui_element": {"small": (256, 128), "medium": (512, 256),  "large": (1024, 512)},
    # RPG-specific asset types
    "hero":       {"small": (256, 256), "medium": (512, 512),  "large": (1024, 1024)},
    "enemy":      {"small": (256, 256), "medium": (512, 512),  "large": (1024, 1024)},
    "npc":        {"small": (256, 256), "medium": (512, 512),  "large": (512, 512)},
    "map_tile":   {"small": (256, 256), "medium": (512, 512),  "large": (1024, 1024)},
    "weapon":     {"small": (256, 256), "medium": (256, 256),  "large": (512, 512)},
    "armor":      {"small": (256, 256), "medium": (512, 512),  "large": (512, 512)},
    "boss":       {"small": (512, 512), "medium": (1024, 512), "large": (1024, 1024)},
    "portrait":   {"small": (256, 256), "medium": (512, 512),  "large": (512, 512)},
}

# Sprite-sheet style → descriptive prompt prefix injected before the user prompt.
# The key "dark_gothic_rpg" is the canonical preset for dark gothic fantasy games.
_SPRITESHEET_STYLE_PREFIXES: dict[str, str] = {
    "dark_gothic_rpg": (
        "dark gothic fantasy RPG sprite sheet, multiple consistent animation frames, "
        "gloomy atmosphere, dark medieval, shadowy silhouette, deep shadows, "
        "dark muted color palette, sinister aesthetic, isolated on black background,"
    ),
    "pixel_art": (
        "2D pixel art sprite sheet, multiple animation frames, retro game style, "
        "pixel perfect, clean edges, isolated on transparent background,"
    ),
    "cartoon": (
        "cartoon 2D sprite sheet, multiple animation frames, vibrant colors, "
        "clean outlines, mobile game style, isolated on white background,"
    ),
}

# Fallback sprite-sheet context prepended to every generation regardless of style
_SPRITESHEET_BASE_CONTEXT = (
    "sprite sheet animation frames, same character across all frames, "
    "consistent art style, game-ready,"
)

# Asset type → descriptive prompt prefix for game context
_ASSET_PROMPT_PREFIXES: dict[str, str] = {
    # Generic mobile-game assets (original)
    "character":  "2D mobile game character sprite, isolated on white background,",
    "item":       "2D mobile game item sprite, isolated on white background,",
    "icon":       "mobile game icon, flat design, isolated on white background,",
    "background": "mobile game background scene, seamless parallax-ready,",
    "ui_element": "mobile game UI element, flat design, clean edges,",
    # RPG-specific asset types
    "hero":       "RPG hero character sprite, 2D pixel art, high detail, isolated on transparent background,",
    "enemy":      "RPG enemy monster sprite, 2D pixel art, high detail, isolated on transparent background,",
    "npc":        "RPG NPC character sprite, 2D pixel art, isolated on transparent background,",
    "map_tile":   "RPG top-down map tile, seamless 2D pixel art tileset, clean edges,",
    "weapon":     "RPG weapon item sprite, 2D pixel art, isolated on white background,",
    "armor":      "RPG armor equipment sprite, 2D pixel art, isolated on white background,",
    "boss":       "RPG boss monster, large detailed sprite, 2D pixel art, epic design, isolated on transparent background,",
    "portrait":   "RPG character portrait, detailed face close-up, 2D illustration, painterly style,",
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
            # Prefer memory-efficient attention (xformers) for speed and quality;
            # fall back to attention slicing when xformers is not installed.
            try:
                _pipe.enable_xformers_memory_efficient_attention()
            except Exception:
                _pipe.enable_attention_slicing()
    return _pipe


def _enhance_quality(img: "_PILImage.Image") -> "_PILImage.Image":
    """Apply subtle post-processing to improve perceived sharpness and contrast.

    These lightweight PIL operations are applied after every AI inference to
    remove the slight softness that diffusion models commonly produce.
    """
    img = _PILEnhance.Sharpness(img).enhance(1.4)
    img = _PILEnhance.Contrast(img).enhance(1.05)
    return img


def generate_image(
    prompt: str,
    width: int,
    height: int,
    steps: int,
    guidance: float,
    out_path: str,
    negative_prompt: str = "",
) -> str:
    pipe = get_pipe()
    neg = negative_prompt or _DEFAULT_NEGATIVE_PROMPT
    img = pipe(
        prompt,
        negative_prompt=neg,
        num_inference_steps=steps,
        guidance_scale=guidance,
        width=width,
        height=height,
    ).images[0]
    img = _enhance_quality(img)
    img.save(out_path, optimize=True)
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
    negative_prompt: str = "",
    style: str = "",
) -> str:
    """Generate a sprite sheet by creating rows*cols frames and stitching them into a grid.

    Each frame is generated at max(_MIN_GEN_SIZE, frame_width) for quality then
    resized to the requested frame dimensions before being placed in the sheet.
    A style prefix and base sprite-sheet context are prepended to every frame
    prompt so the model produces game-ready animation frames.
    A negative prompt is applied to every frame to avoid common quality issues.
    """
    pipe = get_pipe()
    neg = negative_prompt or _DEFAULT_NEGATIVE_PROMPT

    # Build the full prompt: style prefix + base sprite-sheet context + user prompt
    style_prefix = _SPRITESHEET_STYLE_PREFIXES.get(style, f"{style}," if style else "")
    if style_prefix:
        full_prompt = f"{style_prefix} {_SPRITESHEET_BASE_CONTEXT} {prompt}"
    else:
        full_prompt = f"{_SPRITESHEET_BASE_CONTEXT} {prompt}"

    gen_w = max(_MIN_GEN_SIZE, frame_width)
    gen_h = max(_MIN_GEN_SIZE, frame_height)

    sheet = _PILImage.new("RGBA", (cols * frame_width, rows * frame_height))

    for row in range(rows):
        for col in range(cols):
            raw = pipe(
                full_prompt,
                negative_prompt=neg,
                num_inference_steps=steps,
                guidance_scale=guidance,
                width=gen_w,
                height=gen_h,
            ).images[0].convert("RGBA")

            raw = _enhance_quality(raw)

            if raw.size != (frame_width, frame_height):
                raw = raw.resize((frame_width, frame_height), _PILImage.LANCZOS)

            sheet.paste(raw, (col * frame_width, row * frame_height))

    sheet.save(out_path, format="PNG", optimize=True)
    return out_path


def generate_game_asset(
    prompt: str,
    asset_type: str,
    size: str,
    style: str,
    steps: int,
    guidance: float,
    out_path: str,
    negative_prompt: str = "",
) -> str:
    """Generate a mobile game or RPG asset with type-specific prompt engineering.

    Prepends a context prefix and appends the requested style to the user's
    prompt so the model produces output that fits common mobile/RPG game workflows.
    A negative prompt is applied to avoid low-quality or off-style output.
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
        negative_prompt=negative_prompt,
    )


# Apply torch.inference_mode() only when torch is available
if _TORCH_AVAILABLE:
    generate_image = torch.inference_mode()(generate_image)  # type: ignore[assignment]
    generate_spritesheet = torch.inference_mode()(generate_spritesheet)  # type: ignore[assignment]
    generate_game_asset = torch.inference_mode()(generate_game_asset)  # type: ignore[assignment]
