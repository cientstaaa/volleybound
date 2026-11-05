import random
import pygame
from constantes import LARGURA

REDE_X_REF = LARGURA // 2 - 5
REDE_LARGURA_REF = 8

CHANCE_ERRO_CPU = 0.12
ATTACK_VX_MULT = 1.6
ATTACK_VY_MULT = 0.55

_cache_frames = None
_cache_sons = None

def _carregar_frames():
    global _cache_frames
    if _cache_frames is None:
        _cache_frames = [
            pygame.transform.scale(
                pygame.image.load(f"assets/bola_frame{i}.png").convert_alpha(),
                (30, 30)
            )
            for i in range(4)
        ]
    return _cache_frames

def _carregar_sons():
    global _cache_sons
    if _cache_sons is None:
        # Retorna None para cada som se o mixer nao estiver inicializado (ex: Android sem audio)
        if not pygame.mixer.get_init():
            _cache_sons = {
                "toque_jogador": None,
                "toque_rede": None,
                "quique_chao": None,
            }
        else:
            try:
                _cache_sons = {
                    "toque_jogador": pygame.mixer.Sound("assets/toque_bola.wav"),
                    "toque_rede": pygame.mixer.Sound("assets/toque_rede.wav"),
                    "quique_chao": pygame.mixer.Sound("assets/quique_chao.wav"),
                }
            except Exception:
                _cache_sons = {
                    "toque_jogador": None,
                    "toque_rede": None,
                    "quique_chao": None,
                }
    return _cache_sons

class Bola:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.raio = 15
        self.vel_x = 3
        self.vel_y = 0
        self.gravidade = 0.5
        self.amortecimento = 0.75
        self.velocidade_maxima = 20
        self.contatos = {}
        self.ultimo_tocador_id = None
        self._imunidade_toque = {}

        self.frames = _carregar_frames()
        self.sons = _carregar_sons()
        self.frame_index = 0
        self.contador_anim = 0

    def limitar_velocidade(self):
        self.vel_x = max(-self.velocidade_maxima, min(self.velocidade_maxima, self.vel_x))
        self.vel_y = max(-self.velocidade_maxima, min(self.velocidade_maxima, self.vel_y))

    def _animar(self):
        velocidade_total = abs(self.vel_x) + abs(self.vel_y)
        self.contador_anim += max(1, velocidade_total)
        if self.contador_anim >= 15:
            self.contador_anim = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def atualizar(self, largura, altura_chao):
        self.vel_y += self.gravidade
        self.x += self.vel_x
        self.y += self.vel_y

        self.vel_x *= 0.995
        self.limitar_velocidade()
        self._animar()

        for k in list(self._imunidade_toque):
            self._imunidade_toque[k] -= 1
            if self._imunidade_toque[k] <= 0:
                del self._imunidade_toque[k]

        if self.y + self.raio >= altura_chao:
            self.y = altura_chao - self.raio
            self.vel_y = -self.vel_y * self.amortecimento
            if self.sons["quique_chao"]: self.sons["quique_chao"].play()

        if self.x - self.raio <= 0:
            self.x = self.raio
            self.vel_x = -self.vel_x
        elif self.x + self.raio >= largura:
            self.x = largura - self.raio
            self.vel_x = -self.vel_x

    def colidir_com_jogador(self, jogador, numero_toque=None):
        hx = jogador.hitbox_x
        hy = jogador.hitbox_y
        hw = jogador.hitbox_largura
        hh = jogador.hitbox_altura

        mais_perto_x = max(hx, min(self.x, hx + hw))
        mais_perto_y = max(hy, min(self.y, hy + hh))

        dist_x = self.x - mais_perto_x
        dist_y = self.y - mais_perto_y
        distancia = (dist_x ** 2 + dist_y ** 2) ** 0.5

        tocando_agora = distancia < self.raio
        tocando_antes = self.contatos.get(id(jogador), False)
        em_imunidade  = id(jogador) in self._imunidade_toque
        toque_novo = tocando_agora and not tocando_antes and not em_imunidade

        if toque_novo:
            # --- Toque voluntario: sem botao pressionado, bola passa pelo jogador ---
            # IMPORTANTE: nao atualiza contatos aqui — assim quando pode_tocar virar
            # True na proxima frame a deteccao ainda funcionara (tocando_antes=False).
            if not jogador.pode_tocar:
                return False

            if distancia == 0:
                distancia = 0.1
            nx = dist_x / distancia
            ny = dist_y / distancia

            self.x += nx * (self.raio - distancia)
            self.y += ny * (self.raio - distancia)

            # Duplo toque
            duplo_toque = (self.ultimo_tocador_id is not None and
                           id(jogador) == self.ultimo_tocador_id)

            if duplo_toque:
                self.contatos[id(jogador)] = tocando_agora
                self._imunidade_toque[id(jogador)] = 8
                jogador.pode_tocar = False
                jogador.tipo_toque_ativo = None
                return "duplo_toque"
            else:
                tipo = jogador.tipo_toque_ativo

                centro_hitbox_x = jogador.hitbox_x + jogador.hitbox_largura / 2
                metade_alcance  = jogador.hitbox_largura / 2 + self.raio
                offset = (self.x - centro_hitbox_x) / metade_alcance
                offset = max(-1, min(1, offset))

                direcao_time = 1 if jogador.lado == "esquerda" else -1

                # ============================================================
                # BLOQUEIO: devolve rapido e baixo para o outro lado
                # ============================================================
                if tipo == "bloqueio" or jogador.bloqueando:
                    vel_x = direcao_time * 14 + offset * 2
                    vel_y = 3  # levemente para baixo, quica rapido no chao adversario

                # ============================================================
                # ATAQUE / CORTADA: diagonal rapida cruzando a rede
                # vel_x alto, vel_y ligeiramente positivo ou zero -> cai rapido
                # ============================================================
                elif tipo == "ataque" or jogador.atacando:
                    # Quanto mais longe da rede, mais forca (saque viagem potente)
                    if jogador.lado == "esquerda":
                        dist_rede = max(0, REDE_X_REF - (jogador.x + jogador.largura))
                    else:
                        dist_rede = max(0, jogador.x - (REDE_X_REF + REDE_LARGURA_REF))
                    vel_x_base = min(22, 16 + dist_rede * 0.015)  # 16 na rede ate 22 no fundo
                    vel_x = direcao_time * vel_x_base + offset * 3 + jogador.vel_x * 0.3
                    vel_y = -6  # sobe ~36px para limpar rede, cai em diagonal

                # ============================================================
                # TOQUE NO AR (levantamento / passe para o atacante):
                # bola alta, cai perto da rede no proprio lado para o atacante
                # ============================================================
                elif tipo == "toque_ar":
                    # Calcula vel_x para a bola picar na ZONA DE ATAQUE (proprio lado)
                    # alvo_peak 220px da rede -> espaco para o atacante cortar
                    vel_y = -16   # reduzido de -20: pico em ~256px, mais alcancavel
                    t_pico = 16.0 / self.gravidade  # 32 frames ate o pico
                    if jogador.lado == "esquerda":
                        alvo_peak_x = REDE_X_REF - 220   # ~325px: zona de ataque esq
                    else:
                        alvo_peak_x = REDE_X_REF + REDE_LARGURA_REF + 220  # ~765px dir
                    vel_x_ideal = (alvo_peak_x - self.x) / t_pico
                    # Bola sobe quase verticalmente para nao cruzar rede
                    vel_x = max(-3, min(3, vel_x_ideal))
                    # Cap de seguranca: garante que o levantamento nao passe da rede
                    t_ar = abs(vel_y) / self.gravidade * 2  # ~64 frames no ar
                    if jogador.lado == "esquerda":
                        vel_x_max_seguro = (REDE_X_REF - 60 - self.x) / t_ar
                        vel_x = min(vel_x, max(-3, vel_x_max_seguro))
                    else:
                        vel_x_min_seguro = (REDE_X_REF + REDE_LARGURA_REF + 60 - self.x) / t_ar
                        vel_x = max(vel_x, min(3, vel_x_min_seguro))

                # ============================================================
                # RECEPCAO (1o toque) ou PEIXINHO:
                # medio-alta, vai ao centro da propria quadra (levantador se posiciona)
                # ============================================================
                elif tipo == "recepcao" or jogador.mergulhando:
                    # Aponta para a zona do levantador (180px da rede)
                    if jogador.lado == "esquerda":
                        alvo_x = REDE_X_REF - 180   # ~365px: zona do levantador esq
                    else:
                        alvo_x = REDE_X_REF + REDE_LARGURA_REF + 180  # ~735px dir
                    deriva = max(-5, min(5, (alvo_x - self.x) * 0.07))
                    vel_y = -16   # medio-alta: sobe ~256px
                    vel_x = deriva + offset * 0.6 + jogador.vel_x * 0.1
                    # Garante que a bola nao cruze a rede:
                    # calcula o vel_x maximo seguro para o tempo total no ar
                    t_ar = abs(vel_y) / self.gravidade * 2  # ~64 frames
                    if jogador.lado == "esquerda":
                        vel_x_max_seguro = (REDE_X_REF - 25 - self.x) / t_ar
                        vel_x = min(vel_x, max(-5, vel_x_max_seguro))
                    else:
                        vel_x_min_seguro = (REDE_X_REF + REDE_LARGURA_REF + 25 - self.x) / t_ar
                        vel_x = max(vel_x, min(5, vel_x_min_seguro))
                    # Peixinho: menos preciso
                    if jogador.mergulhando:
                        vel_x = vel_x * 0.65 + random.uniform(-2, 2)
                        vel_y *= 0.85

                # ============================================================
                # FALLBACK
                # ============================================================
                else:
                    if jogador.lado == "esquerda":
                        alvo_x = REDE_X_REF / 2
                    else:
                        alvo_x = (REDE_X_REF + REDE_LARGURA_REF + LARGURA) / 2
                    deriva = max(-3, min(3, (alvo_x - self.x) * 0.05))
                    vel_y = -13
                    vel_x = deriva + offset * 1 + jogador.vel_x * 0.15

                # CPUs erram de vez em quando
                if jogador.teclas is None and random.random() < CHANCE_ERRO_CPU:
                    if random.random() < 0.5:
                        vel_x *= random.uniform(0.3, 0.6)
                    else:
                        vel_y *= random.uniform(1.2, 1.6)

                self.vel_x = vel_x
                self.vel_y = vel_y
                self.ultimo_tocador_id = id(jogador)
                self._imunidade_toque[id(jogador)] = 8

                # Reseta o toque voluntario apos uso
                jogador.pode_tocar = False
                jogador.tipo_toque_ativo = None

            self.limitar_velocidade()
            if self.sons["toque_jogador"]: self.sons["toque_jogador"].play()

        self.contatos[id(jogador)] = tocando_agora
        return toque_novo


    def colidir_com_rede(self, x_rede, y_rede, largura_rede, altura_rede):
        mais_perto_x = max(x_rede, min(self.x, x_rede + largura_rede))
        mais_perto_y = max(y_rede, min(self.y, y_rede + altura_rede))

        dist_x = self.x - mais_perto_x
        dist_y = self.y - mais_perto_y
        distancia = (dist_x ** 2 + dist_y ** 2) ** 0.5

        if distancia < self.raio:
            if distancia == 0:
                distancia = 0.1
            nx = dist_x / distancia
            ny = dist_y / distancia

            self.x += nx * (self.raio - distancia)
            self.y += ny * (self.raio - distancia)

            if abs(nx) > abs(ny):
                self.vel_x = -self.vel_x * 0.6
            else:
                self.vel_y = -abs(self.vel_y) * 0.6

            self.limitar_velocidade()
            if self.sons["toque_rede"]: self.sons["toque_rede"].play()

    def desenhar(self, tela):
        sprite = self.frames[self.frame_index]
        tela.blit(sprite, (int(self.x - self.raio), int(self.y - self.raio)))