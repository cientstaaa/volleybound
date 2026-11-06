# ============================================================
# VERSAO MINIMA DE TESTE - apenas verifica se pygame funciona
# Se aparecer uma tela azul com texto = pygame OK
# Se crashar = problema fundamental de pygame/p4a
# ============================================================
import os
import sys

# Detectar Android ANTES de importar pygame
ANDROID = (
    'ANDROID_ARGUMENT' in os.environ or
    'ANDROID_DATA'     in os.environ or
    'ANDROID_ROOT'     in os.environ
)

if ANDROID:
    os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

pygame.init()

if ANDROID:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((800, 480))

W, H = screen.get_size()

screen.fill((30, 100, 200))

font = pygame.font.Font(None, 60)
t1 = font.render("VolleyBound", True, (255, 255, 255))
t2 = font.render("pygame OK! :)", True, (200, 255, 200))
t3 = pygame.font.Font(None, 36).render(f"Tela: {W}x{H}  |  Toque para sair", True, (200, 200, 255))

screen.blit(t1, (W // 2 - t1.get_width() // 2, H // 2 - 80))
screen.blit(t2, (W // 2 - t2.get_width() // 2, H // 2))
screen.blit(t3, (W // 2 - t3.get_width() // 2, H // 2 + 70))

pygame.display.flip()

running = True
while running:
    for event in pygame.event.get():
        if event.type in (pygame.QUIT, pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

pygame.quit()
