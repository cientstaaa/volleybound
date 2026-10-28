import random
import pygame

# ---------------------------------------------------------------------------
# Configuração das animações
# ---------------------------------------------------------------------------
# Quantos frames cada animação tem (apenas as que têm múltiplos arquivos)
FRAMES_IDLE = 12
FRAMES_RUN  = 8

# Tamanho de cada frame das novas animações
FRAME_LARGURA = 96
FRAME_ALTURA  = 96

# Hitbox de colisão com a bola — o sprite tem espaço transparente ao redor do personagem;
# usar o frame inteiro faz a bola "bater no ar". Esses fatores definem a área visível real.
HITBOX_FATOR_W = 0.50   # ~50 % da largura do frame
HITBOX_FATOR_H = 0.72   # ~72 % da altura do frame (ancorado na base)

# Velocidade de troca de frame (em ticks de jogo)
# Menor = animação mais rápida
ANIM_IDLE_TICKS = 6   # ~10 fps  (60/6)
ANIM_RUN_TICKS  = 4   # ~15 fps  (60/4)

# ---------------------------------------------------------------------------

_fonte_rotulo = None

def _obter_fonte():
    global _fonte_rotulo
    if _fonte_rotulo is None:
        _fonte_rotulo = pygame.font.SysFont(None, 24)
    return _fonte_rotulo

def _prever_pouso_x(bola, altura_chao, max_frames=200):
    """Simula a física da bola pra frente (sem colisões) e retorna o x aproximado
    de onde ela vai tocar o chão. Dá pra IA se antecipar em vez de só perseguir
    a posição atual (que já está sempre um pouco 'atrasada' numa bola rápida)."""
    x, y = bola.x, bola.y
    vx, vy = bola.vel_x, bola.vel_y
    for _ in range(max_frames):
        vy += bola.gravidade
        x += vx
        y += vy
        vx *= 0.995
        if y + bola.raio >= altura_chao:
            return x
    return x

def _carregar_e_escalar(caminho, largura, altura):
    """Carrega uma imagem, converte com alpha e escala para as dimensões dadas."""
    return pygame.transform.scale(
        pygame.image.load(caminho).convert_alpha(),
        (largura, altura)
    )

def _flip(surface):
    """Retorna uma copia espelhada horizontalmente da surface."""
    return pygame.transform.flip(surface, True, False)


# ---------------------------------------------------------------------------
# Palette swap (troca de cor da camisa em runtime)
# ---------------------------------------------------------------------------

# Cor marcadora nos sprites base (magenta puro = camisa)
COR_MASCARA = (255, 0, 255)

# Mapeamento: nome da cor do time -> RGB da camisa
CORES_RGB = {
    "vermelho": (220,  40,  40),
    "azul":     ( 37,  70, 107),  
    "amarelo":  (220, 200,  20),
    "verde":    ( 30, 160,  50),
    "branco":   (230, 230, 230),
    "preto":    ( 40,  40,  40),
    "laranja":  (200, 100,  20),
    "roxo":     (120,  30, 180),
    "rosa":     (220,  80, 150),
    "ciano":    ( 30, 190, 190),
}


def _aplicar_cor_camisa(surface, cor_nova):
    """Substitui os pixels magenta (COR_MASCARA) pela cor do time.
    Usa pygame.PixelArray para operar diretamente na surface sem copiar.
    A surface deve estar no formato RGBA (convert_alpha)."""
    pa = pygame.PixelArray(surface)
    pa.replace(COR_MASCARA, cor_nova, distance=10/255)
    del pa  # libera o lock obrigatorio do PixelArray
    return surface


def _carregar_com_cor(caminho, largura, altura, cor_time):
    """Carrega, escala e aplica o palette swap em um unico passo."""
    surf = _carregar_e_escalar(caminho, largura, altura)
    cor_rgb = CORES_RGB.get(cor_time)
    if cor_rgb is not None:
        _aplicar_cor_camisa(surf, cor_rgb)
    return surf


class Jogador:
    def __init__(self, x, y, tom, teclas, lado, rotulo="CPU"):
        self.x = x
        self.y = y
        self.largura = FRAME_LARGURA
        self.altura  = FRAME_ALTURA

        # Hitbox de colisão com a bola (menor que o frame, acompanha o corpo visível)
        self.hitbox_largura  = int(FRAME_LARGURA * HITBOX_FATOR_W)
        self.hitbox_altura   = int(FRAME_ALTURA  * HITBOX_FATOR_H)
        # Centralizado horizontalmente; ancorado na base do frame verticalmente
        self.hitbox_offset_x = (FRAME_LARGURA - self.hitbox_largura) // 2
        self.hitbox_offset_y = FRAME_ALTURA  - self.hitbox_altura
        self.tom = tom
        self.teclas = teclas
        self.lado = lado
        self.rotulo = rotulo

        # O personagem olha para a rede: time esquerda → olha direita; time direita → olha esquerda
        self._virado_direita = (lado == "esquerda")

        self.velocidade = 7
        self.vel_x = 0
        self.vel_y = 0
        self.gravidade = 0.6
        self.forca_pulo = -12
        self.no_chao = True

        self.timer_corte = 0
        self.timer_toque = 0   # mostra animacao de recepcao num toque normal
        self.atacando    = False  # True enquanto estiver num "pulo de ataque" (cortada)
        self.bloqueando  = False  # True enquanto estiver num "pulo de bloqueio"
        self.mergulhando = False  # True logo apos um peixinho
        self.tempo_recuperacao = 0
        self.deslizando  = False
        self.mergulho_direcao  = 0
        self.mergulho_restante = 0
        self.velocidade_deslize = 22
        self._pular_pressionado_antes    = False
        self._peixinho_pressionado_antes = False

        # --- Sistema de toque voluntario ---
        # A bola so colide se pode_tocar == True.
        # tipo_toque_ativo indica qual acao foi ativada:
        #   "recepcao"  : SPACE no chao  -> bola fica no proprio campo
        #   "toque_ar"  : SPACE no ar    -> bola sobe (levantamento)
        #   "ataque"    : W no ar (2x)   -> cortada
        #   "bloqueio"  : W perto da rede -> bloqueia e devolve
        self.pode_tocar       = False
        self.tipo_toque_ativo = None
        self.timer_pode_tocar = 0   # janela de frames em que o toque esta ativo
        # Distancia da rede a partir da qual o pulo vira bloqueio
        self.LIMIAR_REDE = 55

        # Contadores de frame para animações cíclicas
        self._anim_idle_frame = 0
        self._anim_idle_tick  = 0
        self._anim_run_frame  = 0
        self._anim_run_tick   = 0

        # Direção visual do peixinho (pode ir para qualquer lado independente do time)
        self.direcao_peixinho = "direita" if self._virado_direita else "esquerda"

        self._carregar_sprites()

    # -----------------------------------------------------------------------
    # Carregamento de sprites
    # -----------------------------------------------------------------------

    @property
    def hitbox_x(self):
        """X da hitbox de colisão (centralizada no frame horizontalmente)."""
        return self.x + self.hitbox_offset_x

    @property
    def hitbox_y(self):
        """Y da hitbox de colisão (ancorada na base do frame)."""
        return self.y + self.hitbox_offset_y

    def _carregar_sprites(self):
        tom = self.tom
        W, H = self.largura, self.altura

        # --- Animacoes com multiplos frames ---
        # Carrega o sprite BASE (camisa magenta) e aplica a cor do time em tempo de carga.
        # Esquerda e gerada por flip automatico.
        self._frames_idle_dir = [
            _carregar_com_cor(f"assets/jogador_base_idle_{i}.png", W, H, tom)
            for i in range(1, FRAMES_IDLE + 1)
        ]
        self._frames_idle_esq = [_flip(f) for f in self._frames_idle_dir]

        self._frames_run_dir = [
            _carregar_com_cor(f"assets/jogador_base_run_{i}.png", W, H, tom)
            for i in range(1, FRAMES_RUN + 1)
        ]
        self._frames_run_esq = [_flip(f) for f in self._frames_run_dir]

        # --- Sprites de frame unico ---
        self._sprite_jump_dir      = _carregar_com_cor("assets/jogador_base_jump.png",      W, H, tom)
        self._sprite_attack_dir    = _carregar_com_cor("assets/jogador_base_attack.png",    W, H, tom)
        self._sprite_block_dir     = _carregar_com_cor("assets/jogador_base_block.png",     W, H, tom)
        self._sprite_slide_dir     = _carregar_com_cor("assets/jogador_base_slide.png",     W, H, tom)
        self._sprite_recepcao_dir  = _carregar_com_cor("assets/jogador_base_recepcao.png",  W, H, tom)

        self._sprite_jump_esq      = _flip(self._sprite_jump_dir)
        self._sprite_attack_esq    = _flip(self._sprite_attack_dir)
        self._sprite_block_esq     = _flip(self._sprite_block_dir)
        self._sprite_slide_esq     = _flip(self._sprite_slide_dir)
        self._sprite_recepcao_esq  = _flip(self._sprite_recepcao_dir)

    # -----------------------------------------------------------------------
    # Avanço dos contadores de animação
    # -----------------------------------------------------------------------
    def _avancar_idle(self):
        self._anim_idle_tick += 1
        if self._anim_idle_tick >= ANIM_IDLE_TICKS:
            self._anim_idle_tick = 0
            self._anim_idle_frame = (self._anim_idle_frame + 1) % FRAMES_IDLE

    def _avancar_run(self):
        self._anim_run_tick += 1
        if self._anim_run_tick >= ANIM_RUN_TICKS:
            self._anim_run_tick = 0
            self._anim_run_frame = (self._anim_run_frame + 1) % FRAMES_RUN

    # -----------------------------------------------------------------------
    def iniciar_corte(self):
        self.timer_corte = 10

    def iniciar_toque(self):
        """Chamado num toque normal: exibe brevemente o sprite de recepcao."""
        if not self.atacando:
            self.timer_toque = 14

    def _perto_da_rede(self, largura_tela):
        """Retorna True se o jogador esta perto o suficiente da rede para bloquear."""
        meio = largura_tela // 2
        if self.lado == "esquerda":
            return (self.x + self.largura) >= meio - self.LIMIAR_REDE
        else:
            return self.x <= meio + self.LIMIAR_REDE

    def _ativar_toque(self, tipo, frames=12):
        """Ativa a janela de toque voluntario por 'frames' quadros."""
        self.pode_tocar       = True
        self.tipo_toque_ativo = tipo
        self.timer_pode_tocar = frames

    def _tick_toque(self):
        """Decrementa o timer de toque; desativa quando expira."""
        if self.pode_tocar:
            self.timer_pode_tocar -= 1
            if self.timer_pode_tocar <= 0:
                self.pode_tocar       = False
                self.tipo_toque_ativo = None

    def _sprite_atual(self):
        """Retorna o sprite correto para o estado e direcao atuais do personagem."""
        d = self._virado_direita

        # Peixinho / deslize
        if self.deslizando or self.tempo_recuperacao > 0:
            if self.direcao_peixinho == "direita":
                return self._sprite_slide_dir
            else:
                return self._sprite_slide_esq

        # Bloqueio no ar
        if self.bloqueando:
            return self._sprite_block_dir if d else self._sprite_block_esq

        # Cortada real
        if self.atacando or self.timer_corte > 0:
            return self._sprite_attack_dir if d else self._sprite_attack_esq

        # Toque no ar (levantamento no ar) - usa sprite de pulo com toque
        if self.tipo_toque_ativo == "toque_ar" and not self.no_chao:
            return self._sprite_block_dir if d else self._sprite_block_esq

        # Recepcao no chao ou toque com timer visivel
        if self.timer_toque > 0:
            self.timer_toque -= 1
            return self._sprite_recepcao_dir if d else self._sprite_recepcao_esq

        # Pulo normal (sem atacar)
        if not self.no_chao:
            return self._sprite_jump_dir if d else self._sprite_jump_esq

        # Correndo
        if abs(self.vel_x) > 1:
            self._avancar_run()
            frames = self._frames_run_dir if d else self._frames_run_esq
            return frames[self._anim_run_frame]

        # Parado (idle)
        self._avancar_idle()
        frames = self._frames_idle_dir if d else self._frames_idle_esq
        return frames[self._anim_idle_frame]

    # -----------------------------------------------------------------------
    # Atualização do jogador humano
    # -----------------------------------------------------------------------
    def atualizar(self, teclas_pressionadas, largura_tela, altura_chao, bola=None):
        meio = largura_tela // 2

        # --- Decrementa janela de toque voluntario ---
        self._tick_toque()

        # Enquanto esta deslizando pro peixinho, so se move na direcao do mergulho
        if self.deslizando:
            passo = min(self.velocidade_deslize, self.mergulho_restante)
            self.x += self.mergulho_direcao * passo
            self.mergulho_restante -= passo
            if self.mergulho_restante <= 0:
                self.deslizando = False
                self.tempo_recuperacao = 45
            if self.lado == "esquerda":
                self.x = max(0, min(self.x, meio - self.largura - 5))
            else:
                self.x = max(meio + 5, min(self.x, largura_tela - self.largura))
            if self.timer_corte > 0:
                self.timer_corte -= 1
            return

        # Enquanto esta "caido" (recuperacao do peixinho), nao pode fazer mais nada
        if self.tempo_recuperacao > 0:
            self.tempo_recuperacao -= 1
            if self.tempo_recuperacao <= 0:
                self.mergulhando = False
            self.vel_x = 0
            if self.lado == "esquerda":
                self.x = max(0, min(self.x, meio - self.largura - 5))
            else:
                self.x = max(meio + 5, min(self.x, largura_tela - self.largura))
            if self.timer_corte > 0:
                self.timer_corte -= 1
            return

        # --- Movimento horizontal ---
        self.vel_x = 0
        if teclas_pressionadas[self.teclas["esquerda"]]:
            self.x -= self.velocidade
            self.vel_x = -self.velocidade
        if teclas_pressionadas[self.teclas["direita"]]:
            self.x += self.velocidade
            self.vel_x = self.velocidade

        tecla_pular    = self.teclas["pular"]
        tecla_bloquear = self.teclas.get("bloquear")  # Space/RShift: toque_ar no ar
        tecla_recepcao = self.teclas.get("recepcao")  # S/Baixo: recepcao dedicada + peixinho

        pular_pressionado_agora      = teclas_pressionadas[tecla_pular]
        pular_apertado_este_frame    = pular_pressionado_agora and not self._pular_pressionado_antes

        # tecla recepcao (S/Baixo): rastreada em _peixinho_pressionado_antes
        recepcao_pressionada_agora   = tecla_recepcao is not None and teclas_pressionadas[tecla_recepcao]
        recepcao_apertada_este_frame = recepcao_pressionada_agora and not self._peixinho_pressionado_antes

        # tecla bloquear (Space/RShift): rastreada em _recepcao_pressionada_antes
        bloquear_pressionado_agora   = tecla_bloquear is not None and teclas_pressionadas[tecla_bloquear]
        bloquear_apertado_este_frame = bloquear_pressionado_agora and not (
            self._recepcao_pressionada_antes if hasattr(self, '_recepcao_pressionada_antes') else False
        )

        perto_rede = self._perto_da_rede(largura_tela)

        if self.no_chao:
            # --- ACOES NO CHAO ---

            # S/Baixo -> recepcao dedicada:
#   COM direcao (A/D ou Esq/Dir) -> peixinho/mergulho
#   SEM direcao                  -> recepcao em pe (janela de 40 frames)
            if recepcao_apertada_este_frame:
                segura_esquerda = teclas_pressionadas[self.teclas["esquerda"]]
                segura_direita  = teclas_pressionadas[self.teclas["direita"]]

                if segura_esquerda or segura_direita:
                    # --- PEIXINHO ---
                    ALCANCE_MERGULHO = 150
                    if segura_esquerda and not segura_direita:
                        self.mergulho_direcao  = -1
                        self.mergulho_restante = ALCANCE_MERGULHO
                    elif segura_direita and not segura_esquerda:
                        self.mergulho_direcao  = 1
                        self.mergulho_restante = ALCANCE_MERGULHO
                    elif bola is not None:
                        self.mergulho_direcao  = 1 if bola.x > self.x else -1
                        self.mergulho_restante = min(ALCANCE_MERGULHO,
                                                     abs(bola.x - (self.x + self.largura / 2)))
                    else:
                        self.mergulho_direcao  = 1 if self.lado == "esquerda" else -1
                        self.mergulho_restante = ALCANCE_MERGULHO

                    self.deslizando  = True
                    self.mergulhando = True
                    self.direcao_peixinho = "direita" if self.mergulho_direcao == 1 else "esquerda"
                    self.atacando   = False
                    self.bloqueando = False
                    self._ativar_toque("recepcao", frames=20)

                    self._pular_pressionado_antes    = pular_pressionado_agora
                    self._peixinho_pressionado_antes = recepcao_pressionada_agora
                    self._recepcao_pressionada_antes = bloquear_pressionado_agora
                    return
                else:
                    # --- RECEPCAO EM PE ---
                    self._ativar_toque("recepcao", frames=40)
                    self.timer_toque = 14

            # W/Cima -> pulo; perto da rede -> bloqueio
            if pular_apertado_este_frame:
                self.vel_y = self.forca_pulo
                self.no_chao = False
                self.atacando   = False
                if perto_rede:
                    self.bloqueando = True
                    self._ativar_toque("bloqueio", frames=30)
                else:
                    self.bloqueando = False

        else:
            # --- ACOES NO AR ---

            # W/Cima no ar (segunda vez) -> cortada/ataque
            if pular_apertado_este_frame and not self.atacando and not self.bloqueando:
                self.atacando   = True
                self.bloqueando = False
                self._ativar_toque("ataque", frames=40)

            # Space/RShift no ar -> toque no ar (levantamento)
            if bloquear_apertado_este_frame and not self.atacando and not self.bloqueando:
                self._ativar_toque("toque_ar", frames=40)

        self._pular_pressionado_antes    = pular_pressionado_agora
        self._peixinho_pressionado_antes = recepcao_pressionada_agora
        self._recepcao_pressionada_antes = bloquear_pressionado_agora

        self.vel_y += self.gravidade
        self.y += self.vel_y

        if self.y + self.altura >= altura_chao:
            estava_no_ar = not self.no_chao  # True se estava pulando
            self.y = altura_chao - self.altura
            self.vel_y = 0
            self.no_chao = True
            self.atacando   = False
            self.bloqueando = False
            # Reseta toque so na aterrissagem (ar -> chao).
            # Se ja estava no chao, mantem pode_tocar ativo para a recepcao funcionar.
            if estava_no_ar:
                self.pode_tocar       = False
                self.tipo_toque_ativo = None

        if self.lado == "esquerda":
            self.x = max(0, min(self.x, meio - self.largura - 5))
        else:
            self.x = max(meio + 5, min(self.x, largura_tela - self.largura))

        if self.timer_corte > 0:
            self.timer_corte -= 1

        if self.vel_x > 1:
            self._virado_direita = True
        elif self.vel_x < -1:
            self._virado_direita = False
        else:
            self._virado_direita = (self.lado == "esquerda")

    # -----------------------------------------------------------------------
    # Atualização da IA (CPU)
    # -----------------------------------------------------------------------
    def atualizar_ia(self, bola, largura_tela, altura_chao, e_o_ativo=True, x_cobertura=None,
                      dificuldade=0.7, numero_toque_estimado=None):
        self.vel_x = 0
        meio = largura_tela // 2

        # Decrementa janela de toque voluntario da IA
        self._tick_toque()

        if e_o_ativo:
            centro_jogador = self.hitbox_x + self.hitbox_largura // 2

            # Determina lado da bola primeiro para poder redirecionar o alvo
            bola_no_meu_lado = (
                (self.lado == "esquerda" and bola.x < meio) or
                (self.lado == "direita"  and bola.x > meio)
            )

            if not bola_no_meu_lado:
                # Bola no lado adversario: posicao de espera no centro do proprio campo
                # Evita que o fundo corra ate a rede apos atacar
                if self.lado == "esquerda":
                    alvo_x = meio // 2
                else:
                    alvo_x = meio + (largura_tela - meio) // 2
            else:
                alvo_x = _prever_pouso_x(bola, altura_chao)
                # Levantador (frente, posicao_idx==0): limita ao setor frontal da quadra
                # para nao perseguir bola no fundo e abandonar o ponto de levantamento
                if getattr(self, 'posicao_idx', 1) == 0:
                    if self.lado == "esquerda":
                        alvo_x = max(min(alvo_x, meio - 55), meio - 290)
                    else:
                        alvo_x = min(max(alvo_x, meio + 55), meio + 290)

            distancia = alvo_x - centro_jogador

            if abs(distancia) > 10:
                direcao   = 1 if distancia > 0 else -1
                # No chao: velocidade total. No ar: deriva (60%) para
                # acompanhar a bola — suficiente para saque_viagem e ataque
                fator_mov = 1.0 if self.no_chao else 0.6
                movimento = self.velocidade * dificuldade * direcao * fator_mov
                self.x   += movimento
                self.vel_x = movimento

            perto_o_suficiente = abs(distancia) < self.hitbox_largura // 2 + 40
            bola_na_altura_de_pulo = bola.y > self.hitbox_y - 30
            # bola_no_meu_lado ja calculado acima

            saque_viagem_incoming = (
                abs(bola.vel_x) > 8 and abs(bola.vel_y) < 6 and
                bola_no_meu_lado
            )
            if saque_viagem_incoming:
                dist_atual = bola.x - centro_jogador
                if abs(dist_atual) < self.hitbox_largura // 2 + 50:
                    perto_o_suficiente = True
                    distancia = dist_atual

            perto_rede = self._perto_da_rede(largura_tela)
            pode_atacar = numero_toque_estimado is not None and numero_toque_estimado >= 2

            bola_descendo      = bola.vel_y > 1          # bola claramente caindo
            bola_baixa         = bola.y > altura_chao * 0.40  # bola abaixo de 40% da altura
            bola_na_altura_pulo = bola.y > self.hitbox_y - 40  # bola proxima ao topo da hitbox

            if perto_o_suficiente and bola_no_meu_lado:
                if self.no_chao:
                    # Bloqueio desativado: bots nao bloqueiam, usam toque_ar/recepcao.
                    if pode_atacar:
                        bola_muito_baixa = bola.y > altura_chao * 0.78
                        if bola_descendo and not bola_muito_baixa:
                            self.vel_y = self.forca_pulo
                            self.no_chao = False
                            self.atacando   = False
                            self.bloqueando = False
                            # 3o toque: sempre ataca. 2o toque: sempre levanta
                            if numero_toque_estimado == 3:
                                self.atacando = True
                                self._ativar_toque("ataque", frames=30)
                            else:
                                self._ativar_toque("toque_ar", frames=30)
                        elif bola_muito_baixa:
                            self._ativar_toque("recepcao", frames=20)
                            self.timer_toque = 8
                        # else: bola ainda subindo -> apenas se posiciona
                    else:
                        # 1o toque: recepcao no chao
                        self._ativar_toque("recepcao", frames=45)
                        self.timer_toque = 14
                else:
                    # No ar: ativa toque se ainda nao ativou
                    if not self.pode_tocar:
                        # 3o toque: sempre ataca; 2o toque: sempre levanta
                        if numero_toque_estimado == 3:
                            self.atacando = True
                            self.bloqueando = False
                            self._ativar_toque("ataque", frames=30)
                        elif not self.atacando and not self.bloqueando:
                            self._ativar_toque("toque_ar", frames=30)
        else:
            # Em cobertura: nao toca a bola.
            # Reseta pode_tocar enquanto no chao para limpar residuos de ativacoes anteriores.
            if self.no_chao:
                self.pode_tocar       = False
                self.tipo_toque_ativo = None
            if x_cobertura is not None:
                centro_jogador = self.x + self.largura // 2
                distancia = x_cobertura - centro_jogador
                if abs(distancia) > 15:
                    direcao   = 1 if distancia > 0 else -1
                    movimento = self.velocidade * 0.5 * direcao
                    self.x   += movimento
                    self.vel_x = movimento

        self.vel_y += self.gravidade
        self.y += self.vel_y

        if self.y + self.altura >= altura_chao:
            estava_no_ar = not self.no_chao
            self.y = altura_chao - self.altura
            self.vel_y = 0
            self.no_chao  = True
            self.atacando = False
            self.bloqueando = False
            # Reseta toque so na aterrissagem (ar -> chao).
            # Se ja estava no chao, mantem pode_tocar para recepcao funcionar.
            if estava_no_ar:
                self.pode_tocar = False
                self.tipo_toque_ativo = None

        if self.lado == "esquerda":
            self.x = max(0, min(self.x, meio - self.largura - 5))
        else:
            self.x = max(meio + 5, min(self.x, largura_tela - self.largura))

        if self.timer_corte > 0:
            self.timer_corte -= 1

        if self.vel_x > 1:
            self._virado_direita = True
        elif self.vel_x < -1:
            self._virado_direita = False
        else:
            self._virado_direita = (self.lado == "esquerda")

    # -----------------------------------------------------------------------
    # Desenho
    # -----------------------------------------------------------------------
    def desenhar(self, tela):
        sprite = self._sprite_atual()
        tela.blit(sprite, (self.x, self.y))

        fonte = _obter_fonte()
        cor_rotulo = (255, 255, 255) if self.rotulo == "CPU" else (255, 255, 0)
        texto = fonte.render(self.rotulo, True, cor_rotulo)
        fundo = pygame.Surface((texto.get_width() + 6, texto.get_height() + 2))
        fundo.set_alpha(140)
        fundo.fill((0, 0, 0))
        pos_x = self.x + self.largura // 2 - texto.get_width() // 2
        pos_y = self.y - 22
        tela.blit(fundo, (pos_x - 3, pos_y - 1))
        tela.blit(texto, (pos_x, pos_y))