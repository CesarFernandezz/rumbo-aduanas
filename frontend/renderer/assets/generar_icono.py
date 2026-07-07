# generar_icono.py — Genera el icono de la app "Rumbo" (badge ambar + isotipo de contenedor).
# Produce rumbo.ico (multi-tamano para Windows) y rumbo.png. Reejecutar: python generar_icono.py
import os                                             # rutas de salida
import numpy as np                                   # para construir el degradado por pixel
from PIL import Image, ImageDraw                     # dibujo del icono

S = 512                                              # tamano base de alta resolucion (se reduce para el .ico)
AQUI = os.path.dirname(__file__)                     # carpeta assets donde se guardan los archivos

# 1) Fondo con degradado ambar -> durazno en diagonal (mismos tonos que el tema).
c0 = (244, 199, 123)                                 # --ambar #F4C77B
c1 = (243, 168, 124)                                 # --durazno #F3A87C
yy, xx = np.mgrid[0:S, 0:S]                           # coordenadas de cada pixel
t = (xx + yy) / (2 * (S - 1))                         # factor 0..1 a lo largo de la diagonal
grad = np.zeros((S, S, 3), dtype=np.uint8)           # matriz RGB del degradado
for k in range(3):                                   # interpola cada canal de color
    grad[..., k] = (c0[k] * (1 - t) + c1[k] * t).astype(np.uint8)
img = Image.fromarray(grad, "RGB").convert("RGBA")   # imagen base con canal alfa

# 2) Mascara de esquinas redondeadas (forma de icono de app moderna).
mask = Image.new("L", (S, S), 0)                     # mascara en escala de grises
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.24), fill=255)
img.putalpha(mask)                                   # aplica las esquinas redondeadas (fondo transparente)

# 3) Isotipo: contenedor de carga en color oscuro, centrado (igual que el SVG del logo).
d = ImageDraw.Draw(img)                              # lienzo de dibujo
oscuro = (22, 19, 17, 255)                            # --bg-0 #161311
lw = max(2, int(S * 0.045))                          # grosor de linea proporcional
bx0, by0, bx1, by1 = int(S * 0.26), int(S * 0.38), int(S * 0.74), int(S * 0.62)  # cuerpo del contenedor
d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(S * 0.03), outline=oscuro, width=lw)  # contorno
bw = bx1 - bx0                                        # ancho del cuerpo
for rel in (0.28, 0.5, 0.72):                         # 3 estrias verticales (como en el SVG)
    x = int(bx0 + bw * rel)                           # posicion de cada estria
    d.line([(x, by0), (x, by1)], fill=oscuro, width=lw)  # dibuja la estria

# 4) Guardar como .ico multi-tamano (para ventana/taskbar de Windows) y como .png de respaldo.
img.save(os.path.join(AQUI, "rumbo.ico"),            # icono principal de Windows
         sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(os.path.join(AQUI, "rumbo.png"))            # version PNG por si se necesita
print("Icono generado: rumbo.ico y rumbo.png")       # confirmacion
