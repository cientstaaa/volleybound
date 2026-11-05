"""
converter_sprites_base.py
=========================
Converte todos os sprites coloridos existentes em um unico conjunto 'base',
substituindo a cor da camisa por magenta (255, 0, 255) - a cor marcadora
que sera trocada em tempo real pelo palette swap no jogador.py.

Execute uma unica vez:
    python converter_sprites_base.py
"""

import os
import pygame

pygame.init()
pygame.display.set_mode((1, 1))

ASSETS = "assets"
COR_REFERENCIA = "vermelho"

# Cor da camisa do sprite de referencia (vermelho) -> sera substituida por magenta
COR_CAMISA_REFERENCIA = (255, 5, 5)
COR_MASCARA           = (255, 0, 255)   # magenta -- cor marcadora no sprite base

SPRITES_SINGLE = ["attack", "block", "jump", "slide"]
FRAMES_IDLE    = 12
FRAMES_RUN     = 8


def converter_sprite(caminho_entrada, caminho_saida):
    """Troca COR_CAMISA_REFERENCIA -> COR_MASCARA no sprite e salva."""
    img = pygame.image.load(caminho_entrada).convert_alpha()
    pa = pygame.PixelArray(img)
    # distance normalizado 0..1 para pygame-ce (10/255 ~= 0.039 tolera antialiasing leve)
    pa.replace(COR_CAMISA_REFERENCIA, COR_MASCARA, distance=10/255)
    del pa
    pygame.image.save(img, caminho_saida)
    print("  OK " + caminho_saida)


def main():
    converted = 0
    skipped   = 0

    for nome in SPRITES_SINGLE:
        entrada = os.path.join(ASSETS, f"jogador_{COR_REFERENCIA}_{nome}.png")
        saida   = os.path.join(ASSETS, f"jogador_base_{nome}.png")
        if os.path.exists(saida):
            skipped += 1
            continue
        if not os.path.exists(entrada):
            print("  AVISO: nao encontrado: " + entrada)
            continue
        converter_sprite(entrada, saida)
        converted += 1

    for i in range(1, FRAMES_IDLE + 1):
        entrada = os.path.join(ASSETS, f"jogador_{COR_REFERENCIA}_idle_{i}.png")
        saida   = os.path.join(ASSETS, f"jogador_base_idle_{i}.png")
        if os.path.exists(saida):
            skipped += 1
            continue
        if not os.path.exists(entrada):
            print("  AVISO: nao encontrado: " + entrada)
            continue
        converter_sprite(entrada, saida)
        converted += 1

    for i in range(1, FRAMES_RUN + 1):
        entrada = os.path.join(ASSETS, f"jogador_{COR_REFERENCIA}_run_{i}.png")
        saida   = os.path.join(ASSETS, f"jogador_base_run_{i}.png")
        if os.path.exists(saida):
            skipped += 1
            continue
        if not os.path.exists(entrada):
            print("  AVISO: nao encontrado: " + entrada)
            continue
        converter_sprite(entrada, saida)
        converted += 1

    print(f"\nPronto! {converted} sprites convertidos, {skipped} ja existiam.")
    pygame.quit()


if __name__ == "__main__":
    main()
