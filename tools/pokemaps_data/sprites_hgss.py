"""Sprites de terrain HGSS, palette normale explicite pour les accompagnateurs."""

from PIL import Image

from .maps_render_hgss import HgssRenderer
from .pret_gen4_textures import decode, read_nsbtx


def actor_frame(renderer: HgssRenderer, sprite: str) -> tuple[Image.Image, dict]:
    if not sprite.startswith("SPRITE_FOLLOWER_MON_STATIC_"):
        frame, source = renderer.actor_image(sprite)
        return frame, dict(source=source, palette="native", frame="face")
    model = renderer.sprite_models[sprite]
    source = f"files/data/mmodel/mmodel/mmodel_{model:08d}.NSBTX"
    textures = read_nsbtx((renderer.repo.root / source).read_bytes(), source)
    if set(textures.palettes) != {"tsure_poke0", "tsure_poke1"}:
        raise ValueError(f"HGSS : palettes d'accompagnateur inconnues : {sprite}")
    names = sorted(textures.textures, key=lambda name: int(name.rsplit(".", 1)[1]))
    texture = textures.textures[names[2]]
    pixels = decode(texture, textures.palettes["tsure_poke0"])
    data = bytes((component << 3) | (component >> 2) for pixel in pixels for component in pixel)
    return Image.frombytes("RGBA", (texture.width, texture.height), data), dict(
        source=source, palette="tsure_poke0", texture=names[2], frame="face"
    )
