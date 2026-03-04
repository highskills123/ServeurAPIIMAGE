import torch
from diffusers import AutoPipelineForText2Image
from ..config import settings

_pipe = None


def get_pipe():
    global _pipe
    if _pipe is None:
        _pipe = AutoPipelineForText2Image.from_pretrained(
            settings.MODEL_ID,
            torch_dtype=torch.float16
        )
        _pipe.to("cuda")
        _pipe.enable_attention_slicing()
    return _pipe


@torch.inference_mode()
def generate_image(prompt: str, width: int, height: int, steps: int, guidance: float, out_path: str):
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
