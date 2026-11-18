"""PNGs (uno por diapositiva, ordenados por nombre) -> PPTX con una imagen a pantalla completa por diapositiva."""
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

src, dst = Path(sys.argv[1]), sys.argv[2]
pngs = sorted(src.glob("*.png"))
assert pngs, f"no hay PNGs en {src}"
prs = Presentation()
prs.slide_width, prs.slide_height = Emu(1100 * 9525), Emu(700 * 9525)  # 1100x700 px, como el deck
for png in pngs:
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # en blanco
    slide.shapes.add_picture(str(png), 0, 0, prs.slide_width, prs.slide_height)
prs.save(dst)
print(f"{len(pngs)} diapositivas -> {dst}")
