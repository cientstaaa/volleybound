import sys
import math
import os
import random
import traceback

# ---------------------------------------------------------------------------
# CRITICO: detectar Android e setar SDL_AUDIODRIVER=dummy ANTES de importar
# pygame. O SDL2 pode inicializar o subsistema de audio no momento do import;
# se o driver de audio do Android nao estiver disponivel, ocorre SIGSEGV.
# ---------------------------------------------------------------------------
ANDROID = (
    'ANDROID_ARGUMENT' in os.environ or
    'ANDROID_DATA'     in os.environ or
    'ANDROID_ROOT'     in os.environ
)

if ANDROID:
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

# ---------------------------------------------------------------------------
# Log de diagnostico — escreve passo a passo num arquivo acessivel pelo
# gerenciador de arquivos do celular em:
#   /sdcard/Android/data/org.volleybound/files/vb_debug.txt
# Util para saber onde o crash nativo acontece (SIGSEGV nao e capturado pelo
# try/except do Python).
# ---------------------------------------------------------------------------
_LOG_PATH = None

def _dbg(msg):
    global _LOG_PATH
    if not ANDROID:
        return
    if _LOG_PATH is None:
        for _p in [
            "/sdcard/Android/data/org.volleybound/files/vb_debug.txt",
            "/data/data/org.volleybound/files/vb_debug.txt",
        ]:
            try:
                os.makedirs(os.path.dirname(_p), exist_ok=True)
                with open(_p, "w") as _f:
                    _f.write("=== VolleyBound Debug Log ===\n")
                _LOG_PATH = _p
                break
            except Exception:
                continue
    if _LOG_PATH:
        try:
            with open(_LOG_PATH, "a") as _f:
                _f.write(msg + "\n")
                _f.flush()
        except Exception:
            pass

_dbg(f"[1] imports basicos ok | ANDROID={ANDROID} | SDL_AUDIODRIVER={os.environ.get('SDL_AUDIODRIVER','?')}")

# Adiciona a raiz ao path APENAS no PC (no APK os modulos ficam na raiz do app)
if not ANDROID:
    _root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    if _root not in sys.path:
        sys.path.insert(0, _root)

_dbg("[2] sys.path ok")

import pygame

_dbg("[3] import pygame ok")

from constantes import LARGURA, ALTURA, BRANCO, FPS
from bola import Bola
from jogador import Jogador, _carregar_com_cor

_dbg("[4] imports do jogo ok")

from constantes import LARGURA, ALTURA, BRANCO, FPS
from bola import Bola
from jogador import Jogador, _carregar_com_cor

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

# ---------------------------------------------------------------------------
# Funcao de exibicao de erros na tela (essencial para debug no Android)
# ---------------------------------------------------------------------------
def _mostrar_erro_tela(msg):
    """Mostra o traceback/erro na tela pygame para debug sem ADB."""
    try:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            if ANDROID:
                scr = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                scr = pygame.display.set_mode((800, 480))
        else:
            scr = pygame.display.get_surface()
        scr.fill((20, 0, 0))
        fnt = pygame.font.Font(None, 22)
        linhas = msg.replace('\r','').split('\n')
        y = 10
        for linha in linhas:
            # quebrar linhas longas
            while len(linha) > 60:
                surf = fnt.render(linha[:60], True, (255, 100, 100))
                scr.blit(surf, (5, y))
                y += 24
                linha = '  ' + linha[60:]
                if y > scr.get_height() - 30:
                    break
            surf = fnt.render(linha, True, (255, 100, 100))
            scr.blit(surf, (5, y))
            y += 24
            if y > scr.get_height() - 30:
                break
        # instrucao
        hint = fnt.render("Toque para fechar", True, (200, 200, 200))
        scr.blit(hint, (5, scr.get_height() - 28))
        pygame.display.flip()
        # aguardar toque
        esperando = True
        while esperando:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.FINGERDOWN,
                               pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    esperando = False
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Inicializacao principal (dentro de try para capturar erros no Android)
# ---------------------------------------------------------------------------
try:
    _dbg("[5] iniciando pygame...")
    if ANDROID:
        # Usa pygame.init() completo — mais compativel com p4a do que inits individuais
        # SDL_AUDIODRIVER=dummy ja foi definido ANTES do import, entao audio nao crasha
        result = pygame.init()
        _dbg(f"[6] pygame.init() ok: {result}")
    else:
        try:
            pygame.mixer.pre_init(44100, -16, 1, 512)
        except Exception:
            pass
        pygame.init()

    _dbg("[7] chamando display.set_mode...")
    if ANDROID:
        # Tenta FULLSCREEN primeiro (retorna dimensoes reais da tela)
        try:
            tela = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            _dbg("[8] set_mode FULLSCREEN ok")
        except Exception as _e:
            _dbg(f"[8] FULLSCREEN falhou ({_e}), tentando sem flags")
            tela = pygame.display.set_mode((0, 0))
            _dbg("[8] set_mode sem flags ok")
    else:
        tela = pygame.display.set_mode((LARGURA, ALTURA))

    # Atualizar dimensoes com a tela real
    LARGURA, ALTURA = tela.get_size()
    _dbg(f"[9] tela: {LARGURA}x{ALTURA}")
    # Fallback: se set_mode(0,0) nao retornou dimensoes reais (raro em alguns dispositivos)
    if LARGURA == 0 or ALTURA == 0:
        LARGURA, ALTURA = 1280, 720
        tela = pygame.display.set_mode((LARGURA, ALTURA))
        _dbg(f"[9b] fallback: {LARGURA}x{ALTURA}")

    _dbg("[10] set_caption...")
    pygame.display.set_caption("VolleyBound")

    try:
        _icon = pygame.image.load("assets/bola_frame0.png").convert_alpha()
        pygame.display.set_icon(_icon)
    except Exception:
        pass

    _dbg("[11] fontes...")
    relogio = pygame.time.Clock()

    # Font(None, size) usa a fonte builtin do pygame - mais confiavel no Android
    # que SysFont(None, size) que depende de fontes do sistema
    fonte_titulo  = pygame.font.Font(None, 110)
    fonte_grande  = pygame.font.Font(None, 80)
    fonte_placar  = pygame.font.Font(None, 60)
    fonte_media   = pygame.font.Font(None, 40)
    fonte_pequena = pygame.font.Font(None, 28)

    _dbg("[12] sons...")
    try:
        som_ponto = pygame.mixer.Sound("assets/ponto.wav")
    except Exception:
        som_ponto = None

    try:
        som_bipe_menu = pygame.mixer.Sound("assets/bipe_menu.wav")
    except Exception:
        som_bipe_menu = None

    try:
        som_confirmar_menu = pygame.mixer.Sound("assets/confirmar_menu.wav")
    except Exception:
        som_confirmar_menu = None

    _dbg("[13] inicializacao CONCLUIDA com sucesso!")

except Exception:
    _tb = traceback.format_exc()
    _dbg(f"EXCECAO NA INICIALIZACAO:\n{_tb}")
    _mostrar_erro_tela("ERRO NA INICIALIZACAO:\n" + _tb)
    pygame.quit()
    sys.exit(1)


# ??? TOUCH CONTROLS ??????????????????????????????????????????????????????????
class FakeKeyboard:
    def __init__(self): self._s = {}
    def set(self, k, v):
        if k is not None: self._s[k] = v
    def __getitem__(self, k): return self._s.get(k, False)

class VirtualJoystick:
    RAIO_BASE = 70; RAIO_THUMB = 26; DEAD_ZONE = 20
    def __init__(self, cx, cy):
        self.cx=cx; self.cy=cy
        self.thumb_x=float(cx); self.thumb_y=float(cy)
        self.finger_id=None; self._ox=float(cx); self._oy=float(cy)
        self._img=None; self._loaded=False
    def _load(self):
        if self._loaded: return
        self._loaded=True
        try:
            img=pygame.image.load("assets/joystick_base.png").convert_alpha()
            d=self.RAIO_BASE*2+12; self._img=pygame.transform.scale(img,(d,d))
        except: self._img=None
    def handle_fingerdown(self,px,py,fid):
        if (px-self.cx)**2+(py-self.cy)**2<=(self.RAIO_BASE+40)**2:
            self.finger_id=fid; self._ox=px; self._oy=py
            self.thumb_x=px; self.thumb_y=py; return True
        return False
    def handle_fingermotion(self,px,py,fid):
        if fid!=self.finger_id: return
        import math
        dx=px-self._ox; dy=py-self._oy; dist=math.hypot(dx,dy)
        if dist>self.RAIO_BASE: s=self.RAIO_BASE/dist; dx*=s; dy*=s
        self.thumb_x=self.cx+dx; self.thumb_y=self.cy+dy
    def handle_fingerup(self,fid):
        if fid==self.finger_id:
            self.finger_id=None; self.thumb_x=float(self.cx); self.thumb_y=float(self.cy)
    def get_direction(self):
        if self.finger_id is None: return False,False
        dx=self.thumb_x-self.cx; return dx<-self.DEAD_ZONE, dx>self.DEAD_ZONE
    def draw(self,surface):
        self._load(); r=self.RAIO_BASE
        if self._img:
            surface.blit(self._img,(self.cx-self._img.get_width()//2,self.cy-self._img.get_height()//2))
        else:
            s=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(20,40,80,140),(r,r),r)
            pygame.draw.circle(s,(60,120,200,200),(r,r),r,3); surface.blit(s,(self.cx-r,self.cy-r))
        t=self.RAIO_THUMB; ts=pygame.Surface((t*2,t*2),pygame.SRCALPHA)
        pygame.draw.circle(ts,(80,160,255,220),(t,t),t)
        pygame.draw.circle(ts,(200,230,255,200),(t,t),t//2)
        surface.blit(ts,(int(self.thumb_x-t),int(self.thumb_y-t)))

class ActionButton:
    def __init__(self,key,rect,label,color,img_name):
        self.key=key; self.rect=rect; self.label=label
        self.color=color; self.img_name=img_name
        self._img=None; self._loaded=False; self.pressed=False; self._fonte=None
    def _load(self):
        if self._loaded: return
        self._loaded=True
        try:
            img=pygame.image.load(f"assets/{self.img_name}.png").convert_alpha()
            inner=min(self.rect.w-10,self.rect.h-22)
            self._img=pygame.transform.scale(img,(inner,inner))
        except: self._img=None
    def hit(self,px,py): return self.rect.collidepoint(px,py)
    def draw(self,surface):
        self._load()
        if self._fonte is None:
            try:
                self._fonte = pygame.font.SysFont(None, 22)
            except Exception:
                self._fonte = pygame.font.Font(None, 22)
        r,g,b=self.color; bg=pygame.Surface((self.rect.w,self.rect.h),pygame.SRCALPHA)
        if self.pressed: bg.fill((r,g,b,190))
        else: bg.fill((r//4,g//4,b//4,150))
        pygame.draw.rect(bg,(*self.color,230),(0,0,self.rect.w,self.rect.h),2,border_radius=12)
        surface.blit(bg,self.rect.topleft)
        if self._img:
            ix=self.rect.x+(self.rect.w-self._img.get_width())//2
            surface.blit(self._img,(ix,self.rect.y+3))
        t=self._fonte.render(self.label,True,(255,255,255))
        surface.blit(t,(self.rect.x+(self.rect.w-t.get_width())//2,self.rect.bottom-16))

class TouchControls:
    def __init__(self,teclas):
        self.teclas=teclas; self.fake_keys=FakeKeyboard()
        self.joystick=VirtualJoystick(cx=90,cy=ALTURA-78)
        Y2=ALTURA-82; Y1=ALTURA-152
        Kp=teclas.get("pular"); Kr=teclas.get("recepcao"); Ks=teclas.get("bloquear")
        self.buttons=[
            ActionButton(Kr,pygame.Rect(LARGURA-318,Y2,82,70),"REC"  ,(40,200,80) ,"receive_button"),
            ActionButton(Kp,pygame.Rect(LARGURA-228,Y2,82,70),"PULAR",(255,140,0) ,"jump_button"),
            ActionButton(Ks,pygame.Rect(LARGURA-138,Y2,82,70),"SET"  ,(80,80,255) ,"block_button"),
            ActionButton(Kr,pygame.Rect(LARGURA-318,Y1,82,60),"DIVE" ,(0,180,220) ,"dive_button"),
            ActionButton(Kp,pygame.Rect(LARGURA-228,Y1,82,60),"SPIKE",(220,60,60) ,"spike_button"),
        ]
        self._finger_btn={}
    def handle_fingerdown(self,px,py,fid):
        if px<LARGURA//2: self.joystick.handle_fingerdown(px,py,fid); return
        for btn in self.buttons:
            if btn.hit(px,py): btn.pressed=True; self._finger_btn[fid]=btn; self.fake_keys.set(btn.key,True); return
    def handle_fingermotion(self,px,py,fid): self.joystick.handle_fingermotion(px,py,fid)
    def handle_fingerup(self,fid):
        self.joystick.handle_fingerup(fid)
        btn=self._finger_btn.pop(fid,None)
        if btn:
            btn.pressed=False
            if not any(b.key==btn.key for b in self._finger_btn.values()): self.fake_keys.set(btn.key,False)
    def update(self):
        left,right=self.joystick.get_direction()
        self.fake_keys.set(self.teclas.get("esquerda"),left)
        self.fake_keys.set(self.teclas.get("direita"),right)
    def get_fake_keys(self): return self.fake_keys
    def draw(self,surface):
        self.joystick.draw(surface)
        for btn in self.buttons: btn.draw(surface)

class PauseButton:
    def __init__(self): self.rect=pygame.Rect(LARGURA-52,8,44,44)
    def hit(self,pos): return self.rect.collidepoint(pos)
    def draw(self,surface):
        s=pygame.Surface((self.rect.w,self.rect.h),pygame.SRCALPHA); s.fill((20,30,60,180))
        pygame.draw.rect(s,(80,150,255,220),(0,0,self.rect.w,self.rect.h),2,border_radius=8)
        pygame.draw.rect(s,(255,255,255),(10,11,8,22)); pygame.draw.rect(s,(255,255,255),(26,11,8,22))
        surface.blit(s,self.rect.topleft)



PONTOS_POR_SET = 15

SETS_PARA_VENCER = 2



CARGA_SAQUE_PASSO = 0.025

ANGULO_SAQUE_PASSO = 0.02

ANGULO_SAQUE_MAX = 0.6

SAQUE_CPU_DELAY = 50  # frames de espera antes do CPU sacar

CHANCE_SAQUE_VIAGEM_CPU = 0.3  # 30% de chance do CPU optar pelo saque de viagem

PAUSA_PONTO_FRAMES = 45  # ~0.75s de pausa depois de marcar ponto, antes do proximo saque

CARGA_MINIMA_EFETIVA = 0.35  # piso de forca: mesmo soltando rapido, o saque sempre cruza a rede

SAQUE_VIAGEM_LIMIAR = 35  # frames segurando o botao pra virar saque de viagem (em vez do padrao)

SAQUE_VIAGEM_TOSS_VEL_Y = -15  # forca do "toss" da bola pra cima, no saque de viagem



teclas_j1 = {"esquerda": pygame.K_a, "direita": pygame.K_d, "pular": pygame.K_w, "bloquear": pygame.K_SPACE, "recepcao": pygame.K_s}

teclas_j2 = {"esquerda": pygame.K_LEFT, "direita": pygame.K_RIGHT, "pular": pygame.K_UP, "bloquear": pygame.K_RSHIFT, "recepcao": pygame.K_DOWN}



REDE_X = LARGURA // 2 - 5

REDE_Y = ALTURA - 200

REDE_LARGURA = 10

REDE_ALTURA = 100



CAMPO_MARGEM = 40  # distancia das paredes ate a linha de fundo da quadra

CAMPO_X_MIN = CAMPO_MARGEM

CAMPO_X_MAX = LARGURA - CAMPO_MARGEM



config_slots = [

    {"time": "esquerda", "posicao": 0, "ocupante": "Player 1"},

    {"time": "esquerda", "posicao": 1, "ocupante": "CPU"},

    {"time": "direita", "posicao": 0, "ocupante": "CPU"},

    {"time": "direita", "posicao": 1, "ocupante": "CPU"},

]

slot_selecionado = 0

OPCOES_OCUPANTE = ["CPU", "Player 1"]  # Sem Player 2 (mobile)



CORES_DISPONIVEIS = ["vermelho", "azul", "amarelo", "verde", "branco", "preto", "laranja", "roxo", "rosa", "ciano"]

NOMES_CORES = {

    "vermelho": "Vermelho", "azul": "Azul", "amarelo": "Amarelo",

    "verde": "Verde", "branco": "Branco", "preto": "Preto",

    "laranja": "Laranja", "roxo": "Roxo", "rosa": "Rosa", "ciano": "Ciano",

}

cor_time_esquerda_idx = 0  # vermelho

cor_time_direita_idx = 1   # azul



QUADRAS_DISPONIVEIS = ["ginasio_dia", "ginasio_noite", "aeroporto_dia", "aeroporto_noite", "praca_dia", "praca_noite", "praia_dia", "praia_noite"]

NOMES_QUADRAS = {

    "ginasio_dia": "Ginasio de Escola (Dia)",

    "ginasio_noite": "Ginasio de Escola (Noite)",

    "aeroporto_dia": "Aeroporto (Dia)",

    "aeroporto_noite": "Aeroporto (Noite)",

    "praca_dia": "Praca (Dia)",

    "praca_noite": "Praca (Noite)",

    "praia_dia": "Praia (Dia)",

    "praia_noite": "Praia (Noite)",

}

quadra_idx = 0



def ciclar_quadra(direcao):

    global quadra_idx

    quadra_idx = (quadra_idx + direcao) % len(QUADRAS_DISPONIVEIS)



# --- Modo Torneio ---

DIFICULDADE_IA_PADRAO = 1.0

dificuldade_ia_atual = DIFICULDADE_IA_PADRAO



NOMES_TIMES = {

    "vermelho": "Furia Vermelha",

    "azul": "Tsunami Azul",

    "amarelo": "Raio Amarelo",

    "verde": "Furacao Verde",

    "branco": "Fantasmas Brancos",

    "preto": "Sombra Negra",

    "laranja": "Chama Laranja",

    "roxo": "Tornado Roxo",

    "rosa": "Tempestade Rosa",

    "ciano": "Ceu Ciano",

}

DIFICULDADES_RODADA = [0.55, 0.8, 1.0]  # facil -> dificil, uma por rodada



roster_torneio_atual = []  # preenchido por sortear_torneio() a cada novo torneio



# Indices de rotacao de posicao frente/fundo por time (atualizados a cada side-out)

rotacao_formacao_esquerda = 0

rotacao_formacao_direita  = 0



modo_torneio = False

torneio_rodada = 0



def sortear_torneio():

    """Sorteia 3 adversarios diferentes entre si e diferentes da cor do jogador."""

    global roster_torneio_atual

    cor_jogador = CORES_DISPONIVEIS[cor_time_esquerda_idx]

    candidatas = [c for c in CORES_DISPONIVEIS if c != cor_jogador]

    escolhidas = random.sample(candidatas, 3)

    roster_torneio_atual = [

        {"nome": NOMES_TIMES[cor], "cor": cor, "dificuldade": dificuldade}

        for cor, dificuldade in zip(escolhidas, DIFICULDADES_RODADA)

    ]



def corrigir_conflitos_torneio():

    """Chamada depois que o jogador confirma sua propria cor: se ele tiver trocado

    a cor durante a tela de selecao e isso colidir com algum adversario ja sorteado,

    troca a cor daquela rodada por outra ainda nao usada."""

    global roster_torneio_atual

    cor_jogador = CORES_DISPONIVEIS[cor_time_esquerda_idx]

    usadas = {cor_jogador}

    for entrada in roster_torneio_atual:

        if entrada["cor"] in usadas:

            outras_em_uso = {e["cor"] for e in roster_torneio_atual}

            disponiveis = [c for c in CORES_DISPONIVEIS if c not in usadas and c not in outras_em_uso]

            if disponiveis:

                nova_cor = random.choice(disponiveis)

                entrada["cor"] = nova_cor

                entrada["nome"] = NOMES_TIMES[nova_cor]

        usadas.add(entrada["cor"])

    preparar_rodada_torneio()



def preparar_rodada_torneio():

    """Configura a cor, dificuldade e ocupantes do time adversario pra rodada atual do torneio."""

    global cor_time_direita_idx, dificuldade_ia_atual

    adversario = roster_torneio_atual[torneio_rodada]

    cor_time_direita_idx = CORES_DISPONIVEIS.index(adversario["cor"])

    dificuldade_ia_atual = adversario["dificuldade"]

    for slot in config_slots:

        if slot["time"] == "direita":

            slot["ocupante"] = "CPU"



def slots_navegaveis():

    """Indices de config_slots que podem ser editados na tela atual (no torneio, so o proprio time)."""

    if modo_torneio:

        return [i for i, s in enumerate(config_slots) if s["time"] == "esquerda"]

    return list(range(len(config_slots)))



_cache_previews = {}



def obter_preview(cor):

    if cor not in _cache_previews:

        # Carrega o sprite base e aplica a cor do time via palette swap

        img = _carregar_com_cor("assets/jogador_base_idle_1.png", 160, 160, cor)

        _cache_previews[cor] = img

    return _cache_previews[cor]



def ciclar_ocupante(indice_slot, direcao):

    slot = config_slots[indice_slot]

    opcao_atual = OPCOES_OCUPANTE.index(slot["ocupante"])

    nova_opcao = OPCOES_OCUPANTE[(opcao_atual + direcao) % len(OPCOES_OCUPANTE)]



    if nova_opcao in ("Player 1", "Player 2"):

        for i, outro_slot in enumerate(config_slots):

            if i != indice_slot and outro_slot["ocupante"] == nova_opcao:

                outro_slot["ocupante"] = "CPU"



    slot["ocupante"] = nova_opcao



def ciclar_cor(time_que_muda, direcao):

    """Troca a cor de um time, pulando qualquer cor que o outro time ja esteja usando."""

    global cor_time_esquerda_idx, cor_time_direita_idx

    if time_que_muda == "esquerda":

        nova = (cor_time_esquerda_idx + direcao) % len(CORES_DISPONIVEIS)

        if nova == cor_time_direita_idx:

            nova = (nova + direcao) % len(CORES_DISPONIVEIS)

        cor_time_esquerda_idx = nova

    else:

        nova = (cor_time_direita_idx + direcao) % len(CORES_DISPONIVEIS)

        if nova == cor_time_esquerda_idx:

            nova = (nova + direcao) % len(CORES_DISPONIVEIS)

        cor_time_direita_idx = nova



def novo_jogo():

    global time_esquerda, time_direita

    global placar_esquerda, placar_direita, sets_esquerda, sets_direita

    global lado_atual, toques_lado_atual

    global servidor_idx_esquerda, servidor_idx_direita, lado_sacando_atual

    global posicoes_x_esquerda_base, posicoes_x_direita_base



    posicoes_x_esquerda = [100, 300]

    posicoes_x_direita = [LARGURA - 380, LARGURA - 100]  # frente perto rede, fundo longe (280px gap)

    # Salva as posicoes base para reposicionar corretamente apos rotacoes

    posicoes_x_esquerda_base = posicoes_x_esquerda[:]

    posicoes_x_direita_base  = posicoes_x_direita[:]



    cor_esquerda = CORES_DISPONIVEIS[cor_time_esquerda_idx]

    cor_direita = CORES_DISPONIVEIS[cor_time_direita_idx]



    time_esquerda = []

    time_direita = []



    # y inicial: base do sprite encostada no chao (ALTURA - 100)

    Y_INICIAL = (ALTURA - 100) - 96  # 96 = FRAME_ALTURA



    for slot in config_slots:

        teclas = None

        if slot["ocupante"] == "Player 1":

            teclas = teclas_j1

        elif slot["ocupante"] == "Player 2":

            teclas = teclas_j2



        rotulo = "P1" if slot["ocupante"] == "Player 1" else "P2" if slot["ocupante"] == "Player 2" else "CPU"



        if slot["time"] == "esquerda":

            x = posicoes_x_esquerda[slot["posicao"]]

            jogador = Jogador(x, Y_INICIAL, cor_esquerda, teclas, "esquerda", rotulo)

            jogador.x_inicial = x

            jogador.y_inicial = Y_INICIAL

            time_esquerda.append(jogador)

        else:

            x = posicoes_x_direita[slot["posicao"]]

            jogador = Jogador(x, Y_INICIAL, cor_direita, teclas, "direita", rotulo)

            jogador.x_inicial = x

            jogador.y_inicial = Y_INICIAL

            time_direita.append(jogador)



    placar_esquerda = 0

    placar_direita = 0

    sets_esquerda = 0

    sets_direita = 0

    lado_atual = None

    toques_lado_atual = 0

    servidor_idx_esquerda = 0

    servidor_idx_direita = 0

    lado_sacando_atual = None  # nenhum time sacando ainda (inicio de jogo)



    # Indice de rotacao de posicao (0 = formacao inicial; avanca a cada side-out)

    # Para esquerda: idx 0 -> jogador[0]=fundo, jogador[1]=frente

    #               idx 1 -> jogador[0]=frente, jogador[1]=fundo

    # Para direita: espelhado (posicao 0 = frente, posicao 1 = fundo)

    rotacao_formacao_esquerda = 0

    rotacao_formacao_direita  = 0



    # Marca o indice de posicao de cada jogador no time (0 ou 1)

    for i, j in enumerate(time_esquerda):

        j.posicao_idx = i

    for i, j in enumerate(time_direita):

        j.posicao_idx = i



def iniciar_saque(lado_do_saque):

    """Prepara o proximo saque: reposiciona todos os jogadores nas posicoes iniciais

    e coloca a bola na mao do sacador atual do time que ganhou o ponto.

    Quando um time GANHA o saque (side-out), avanca o indice ? o proximo jogador

    da fila passa a sacar, igual a rotacao do volei de verdade."""

    global bola, servidor, carga_saque, angulo_saque, timer_saque_cpu, estado, tempo_segurando_saque

    global lado_atual, toques_lado_atual, ultimo_toque_lado, jogador_primeiro_toque, juiz_pose

    global servidor_idx_esquerda, servidor_idx_direita, lado_sacando_atual

    global rotacao_formacao_esquerda, rotacao_formacao_direita

    global posicoes_x_esquerda_base, posicoes_x_direita_base



    # Rotacao: se o time que vai sacar e DIFERENTE do que estava sacando antes

    # (side-out), avanca o indice ? o proximo jogador da fila passa a sacar

    # E as posicoes de frente/fundo tambem rotacionam

    if lado_sacando_atual is not None and lado_sacando_atual != lado_do_saque:

        if lado_do_saque == "esquerda":

            servidor_idx_esquerda = (servidor_idx_esquerda + 1) % len(time_esquerda)

            rotacao_formacao_esquerda = (rotacao_formacao_esquerda + 1) % len(time_esquerda)

            # Atualiza posicao_idx de cada jogador do time esquerda

            for i, j in enumerate(time_esquerda):

                j.posicao_idx = (i + rotacao_formacao_esquerda) % len(time_esquerda)

            # Atualiza x_inicial com base no novo papel (frente/fundo)

            # Esquerda: posicao_idx 1 = frente (pos base [1]=300), 0 = fundo (pos base [0]=100)

            for j in time_esquerda:

                j.x_inicial = posicoes_x_esquerda_base[j.posicao_idx % 2]

        else:

            servidor_idx_direita = (servidor_idx_direita + 1) % len(time_direita)

            rotacao_formacao_direita = (rotacao_formacao_direita + 1) % len(time_direita)

            for i, j in enumerate(time_direita):

                j.posicao_idx = (i + rotacao_formacao_direita) % len(time_direita)

            # Direita: posicao_idx 0 = frente (pos base [0]=LARGURA-340), 1 = fundo (pos base [1]=LARGURA-140)

            for j in time_direita:

                j.x_inicial = posicoes_x_direita_base[j.posicao_idx % 2]

    lado_sacando_atual = lado_do_saque



    # Todos os jogadores voltam pra posicao inicial, nao so quem vai sacar

    for jogador in time_esquerda + time_direita:

        jogador.x = jogador.x_inicial

        jogador.y = jogador.y_inicial

        jogador.vel_x = 0

        jogador.vel_y = 0

        jogador.no_chao = True

        jogador.atacando = False

        jogador.timer_corte = 0



    time = time_esquerda if lado_do_saque == "esquerda" else time_direita

    idx = servidor_idx_esquerda if lado_do_saque == "esquerda" else servidor_idx_direita

    servidor = time[idx]



    # Posiciona o sacador na ponta de tras da propria quadra (longe da rede)

    MARGEM_FUNDO = 20

    if lado_do_saque == "esquerda":

        servidor.x = MARGEM_FUNDO

    else:

        servidor.x = LARGURA - MARGEM_FUNDO - servidor.largura

    servidor.y = (ALTURA - 100) - servidor.altura

    servidor.vel_x = 0

    servidor.vel_y = 0

    servidor.no_chao = True



    # Bola comeca na altura da mao do sacador (topo da hitbox visivel)

    bola = Bola(servidor.x + servidor.largura // 2, servidor.hitbox_y)

    bola.vel_x = 0

    bola.vel_y = 0



    carga_saque = 0.0

    angulo_saque = 0.0

    timer_saque_cpu = 0

    tempo_segurando_saque = 0



    lado_atual = None

    toques_lado_atual = 0

    ultimo_toque_lado = lado_do_saque  # o saque conta como o "toque" inicial, pra fins de falta por bola fora

    jogador_primeiro_toque = None

    juiz_pose = "neutro"



    estado = "saque"



def executar_saque():

    """Lanca a bola a partir da posicao atual de carga/angulo do saque.

    Usa um piso de forca minima pra garantir que o saque sempre cruze a rede,

    mesmo se a tecla for solta quase imediatamente."""

    global bola, estado

    direcao_base = 1 if servidor.lado == "esquerda" else -1

    carga_efetiva = CARGA_MINIMA_EFETIVA + carga_saque * (1 - CARGA_MINIMA_EFETIVA)

    magnitude_x = 15 + carga_efetiva * 3 + angulo_saque * 3

    bola.vel_x = direcao_base * magnitude_x

    bola.vel_y = -(11 + carga_efetiva * 2)

    # Empurra a bola pra cima do sprite do sacador para evitar colisao imediata

    bola.y = servidor.hitbox_y - bola.raio - 5

    # Registra o sacador como ultimo tocador (evita duplo toque imediato)

    bola.ultimo_tocador_id = id(servidor)

    estado = "jogando"



def iniciar_saque_viagem():

    """Saque de viagem: em vez de lancar a bola direto, ela sobe ('toss') e o

    sacador espera no chao ate a bola atingir a altura ideal, ai pula pra cortar.

    Reaproveita a mesma fisica de ataque do jogo normal."""

    global bola, estado, saque_viagem_tecla_liberada

    # Leve vel_x na direcao da rede para combinar com o pulo para frente do sacador

    bola.vel_x = 2 if servidor.lado == "esquerda" else -2

    bola.vel_y = SAQUE_VIAGEM_TOSS_VEL_Y

    # O jogador FICA no chao ? ele vai pular no estado "saque_viagem"

    servidor.no_chao = True

    servidor.vel_y = 0

    servidor.atacando = False

    servidor.bloqueando = False

    servidor._pular_pressionado_antes = False

    # A tecla de pulo pode ainda estar pressionada (segurava pra carregar o saque);

    # so aceita pulo manual depois que ela for solta pelo menos uma vez.

    saque_viagem_tecla_liberada = False

    estado = "saque_viagem"



_cache_fundos = {}



def obter_fundo(nome_quadra):

    if nome_quadra not in _cache_fundos:

        img = pygame.image.load(f"assets/fundo_{nome_quadra}.png").convert()

        if img.get_size() != (LARGURA, ALTURA):

            img = pygame.transform.scale(img, (LARGURA, ALTURA))

        _cache_fundos[nome_quadra] = img

    return _cache_fundos[nome_quadra]



def desenhar_quadra():

    fundo = obter_fundo(QUADRAS_DISPONIVEIS[quadra_idx])

    tela.blit(fundo, (0, 0))



def texto_centralizado(texto, fonte, cor, y):

    render = fonte.render(texto, True, cor)

    tela.blit(render, (LARGURA // 2 - render.get_width() // 2, y))



def texto_com_fundo(texto, fonte, y, cor_texto=BRANCO, padding_x=10, padding_y=5):

    """Texto centralizado com uma faixa escura semi-transparente atras, pra ficar

    legivel em qualquer cenario de fundo (claro ou escuro)."""

    render = fonte.render(texto, True, cor_texto)

    largura_fundo = render.get_width() + padding_x * 2

    altura_fundo = render.get_height() + padding_y * 2

    x_fundo = LARGURA // 2 - largura_fundo // 2



    fundo = pygame.Surface((largura_fundo, altura_fundo))

    fundo.set_alpha(140)

    fundo.fill((0, 0, 0))

    tela.blit(fundo, (x_fundo, y - padding_y))

    tela.blit(render, (LARGURA // 2 - render.get_width() // 2, y))



def atualizar_time_cpu(cpus, bola, largura_tela, altura_chao, numero_toque_estimado=None, todos_time=None):

    if len(cpus) == 0:

        return



    # Time misto (humano + CPU) ou time com 1 CPU sozinho

    if len(cpus) == 1:

        # Verifica se ha companheiro humano no time

        companheiros_humanos = [j for j in (todos_time or []) if j.teclas is not None]

        if not companheiros_humanos:

            # CPU sozinho no time: sempre ativo

            cpus[0].atualizar_ia(bola, largura_tela, altura_chao, e_o_ativo=True,

                                  dificuldade=dificuldade_ia_atual, numero_toque_estimado=numero_toque_estimado)

            return



        # Time misto: determina papeis entre TODOS os jogadores do time

        meio = largura_tela // 2

        lado = cpus[0].lado

        time_completo = todos_time  # humanos + CPU

        if lado == "esquerda":

            frente_list = [j for j in time_completo if j.posicao_idx % 2 == 1]

            fundo_list  = [j for j in time_completo if j.posicao_idx % 2 == 0]

        else:

            frente_list = [j for j in time_completo if j.posicao_idx % 2 == 0]

            fundo_list  = [j for j in time_completo if j.posicao_idx % 2 == 1]

        frente = frente_list[0] if frente_list else time_completo[0]

        fundo  = fundo_list[0]  if fundo_list  else time_completo[-1]



        # Suprime toque estimado se bola esta voando rapido para fora do lado

        # APENAS no toque 1 (pos-saque): evita que o bot chase a bola indo embora

        # Nao suprime no toque 2/3 para o fundo poder atacar normalmente

        bola_indo_embora = (

            numero_toque_estimado == 1 and (

                (lado == "esquerda" and bola.vel_x > 6) or

                (lado == "direita"  and bola.vel_x < -6)

            )

        )

        if bola_indo_embora:

            numero_toque_estimado = None



        cpu = cpus[0]



        # Determina quem e o ativo, levando em conta quem fez o 1o toque

        # para inverter roles corretamente quando o humano esta perto da rede

        if numero_toque_estimado is None or numero_toque_estimado == 1:

            ativo = fundo

        elif numero_toque_estimado == 2:

            # Quem nao fez o 1o toque faz o 2o (levantamento)

            if jogador_primeiro_toque is not None and jogador_primeiro_toque in time_completo:

                ativo = cpu if (jogador_primeiro_toque is not cpu) else frente

            else:

                ativo = frente  # padrao: frente levanta

        else:

            ativo = jogador_primeiro_toque if jogador_primeiro_toque in time_completo else fundo



        if ativo is cpu:

            # E a vez do CPU: ativo normal

            cpu.atualizar_ia(bola, largura_tela, altura_chao, e_o_ativo=True,

                             dificuldade=dificuldade_ia_atual, numero_toque_estimado=numero_toque_estimado)

        else:

            # Vez do humano: CPU vai para cobertura

            if numero_toque_estimado is None:

                # Bola no lado adversario: CPU volta para sua posicao base

                # (evita ficar colado ao sacador ou ao companheiro)

                x_cob = cpu.x_inicial

            elif cpu is frente:

                x_cob = (meio - 180) if lado == "esquerda" else (meio + 180)

            else:

                if numero_toque_estimado == 2:

                    x_cob = (meio - 220) if lado == "esquerda" else (meio + 220)

                else:

                    x_cob = (meio // 2) if lado == "esquerda" else (meio + (largura_tela - meio) // 2)

            cpu.atualizar_ia(bola, largura_tela, altura_chao, e_o_ativo=False, x_cobertura=x_cob)

        return



    meio = largura_tela // 2

    lado = cpus[0].lado



    # Usa posicao_idx para determinar frente/fundo de forma estavel (nao pelo x dinamico)

    # Para esquerda: posicao_idx 0 = fundo (x menor), posicao_idx 1 = frente (x maior)

    # Para direita:  posicao_idx 0 = frente (x menor), posicao_idx 1 = fundo (x maior)

    if len(cpus) >= 2:

        if lado == "esquerda":

            # posicao_idx 1 e frente (mais perto da rede)

            frente_list = [j for j in cpus if j.posicao_idx % 2 == 1]

            fundo_list  = [j for j in cpus if j.posicao_idx % 2 == 0]

        else:

            # posicao_idx 0 e frente (mais perto da rede, x menor)

            frente_list = [j for j in cpus if j.posicao_idx % 2 == 0]

            fundo_list  = [j for j in cpus if j.posicao_idx % 2 == 1]

        frente = frente_list[0] if frente_list else cpus[0]

        fundo  = fundo_list[0]  if fundo_list  else cpus[1]

    else:

        frente = cpus[0]

        fundo  = cpus[0]



    # Posicao relativa da bola na quadra (0=fundo, 1=rede)

    if lado == "esquerda":

        bola_relativa = bola.x / meio

    else:

        bola_relativa = (largura_tela - bola.x) / (largura_tela - meio)

    bola_relativa = max(0.0, min(1.0, bola_relativa))



    # Suprime toque estimado se bola esta voando rapido para fora do lado

    # APENAS no toque 1 (pos-saque): evita que bots percam o ataque (toque 3)

    bola_indo_embora_2cpu = (

        numero_toque_estimado == 1 and (

            (lado == "esquerda" and bola.vel_x > 6) or

            (lado == "direita"  and bola.vel_x < -6)

        )

    )

    if bola_indo_embora_2cpu:

        numero_toque_estimado = None



    # --- Escolhe quem e o ativo baseado no toque ---

    if numero_toque_estimado is None or numero_toque_estimado == 1:

        # 1o toque: SEMPRE o jogador de fundo recebe.

        # O frente nunca vai buscar a bola no 1o toque.

        ativo = fundo

    elif numero_toque_estimado == 2:

        # 2o toque: frente levanta (setter)

        ativo = frente

    else:

        # 3o toque: quem fez o 1o toque ataca; senao, fundo

        if jogador_primeiro_toque in cpus:

            ativo = jogador_primeiro_toque

        else:

            ativo = fundo



    # --- Atualiza cada jogador ---

    for j in cpus:

        if j is ativo:

            j.atualizar_ia(bola, largura_tela, altura_chao, e_o_ativo=True,

                           dificuldade=dificuldade_ia_atual, numero_toque_estimado=numero_toque_estimado)

        else:

            # Cobertura baseada no papel do jogador e no numero do toque

            if j is frente:

                if numero_toque_estimado is None or numero_toque_estimado == 1:

                    # 1o toque: setter se posiciona na zona de levantamento (180px da rede)

                    # para estar perto de onde o passe do fundo vai chegar

                    if lado == "esquerda":

                        x_cob = meio - 180  # ~365px

                    else:

                        x_cob = meio + 180  # ~725px

                else:

                    # 2o/3o toque: setter perto da rede para levantar / bloquear

                    if lado == "esquerda":

                        x_cob = meio - j.largura - 55  # ~430px

                    else:

                        x_cob = meio + 55  # ~600px

            else:

                # Fundo

                if numero_toque_estimado == 2:

                    # Durante o levantamento: fundo se aproxima da zona de ataque

                    # para estar pronto para cortar assim que o setter bater

                    if lado == "esquerda":

                        x_cob = meio - 220  # ~325px: zona de ataque

                    else:

                        x_cob = meio + 220  # ~765px

                else:

                    # Cobertura padrao: centro do proprio campo

                    if lado == "esquerda":

                        x_cob = meio // 2  # ~272px

                    else:

                        x_cob = meio + (largura_tela - meio) // 2  # ~822px

            j.atualizar_ia(bola, largura_tela, altura_chao, e_o_ativo=False, x_cobertura=x_cob)



novo_jogo()

estado = "titulo"

jogador_primeiro_toque = None

tempo_segurando_saque = 0

saque_viagem_tecla_liberada = False

saque_em_andamento = False   # True somente durante o frame do saque de viagem

menu_opcao = 0        # 0 = Partida Rapida, 1 = Torneio

menu_frame = 0        # contador de frames para animacoes de menu

# servidor_idx e lado_sacando_atual ja foram inicializados dentro de novo_jogo()

ultimo_ponto_foi_duplo_toque = False

ultimo_ponto_foi_fora = False

timer_pausa_ponto = 0

proximo_saque_lado = "esquerda"



estado_antes_pausa = "jogando"
touch_controls = TouchControls(teclas_j1)
pause_btn = PauseButton()

rodando = True
while rodando:

    for evento in pygame.event.get():

        if evento.type == pygame.QUIT:

            rodando = False



        if evento.type == pygame.FINGERDOWN:
            px = int(evento.x * LARGURA); py = int(evento.y * ALTURA)
            if estado in ("jogando", "saque", "saque_viagem", "ponto_marcado"):
                if pause_btn.hit((px, py)):
                    estado_antes_pausa = estado; estado = "pausado"
                elif estado == "jogando":
                    touch_controls.handle_fingerdown(px, py, evento.finger_id)
            else:
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                    {"pos": (px, py), "button": 1}))

        elif evento.type == pygame.FINGERMOTION:
            touch_controls.handle_fingermotion(
                int(evento.x * LARGURA), int(evento.y * ALTURA), evento.finger_id)

        elif evento.type == pygame.FINGERUP:
            touch_controls.handle_fingerup(evento.finger_id)

        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            mx, my = evento.pos
            if estado == "titulo":
                (som_confirmar_menu.play() if som_confirmar_menu else None); menu_opcao = 0; estado = "menu_principal"
            elif estado == "menu_principal":
                for i in range(2):
                    if pygame.Rect(LARGURA//2-230, 200+i*130, 460, 100).collidepoint(mx, my):
                        menu_opcao = i; (som_confirmar_menu.play() if som_confirmar_menu else None); slot_selecionado = 0
                        if i == 0: modo_torneio=False; dificuldade_ia_atual=DIFICULDADE_IA_PADRAO; estado="config_jogadores"
                        else: modo_torneio=True; torneio_rodada=0; sortear_torneio(); preparar_rodada_torneio(); estado="config_jogadores"
                        break
            elif estado == "config_jogadores":
                nav = slots_navegaveis()
                for pos, isl in enumerate(nav):
                    if pygame.Rect(LARGURA//2-260, 145+pos*72, 520, 55).collidepoint(mx, my):
                        ciclar_ocupante(isl, 1); (som_bipe_menu.play() if som_bipe_menu else None); break
                if my > ALTURA-80: (som_confirmar_menu.play() if som_confirmar_menu else None); slot_selecionado=0; estado="config_cores"
            elif estado == "config_cores":
                cx_e=LARGURA//2-200; cx_d=LARGURA//2+200
                if abs(mx-cx_e)<130 and not modo_torneio: ciclar_cor("esquerda",1); (som_bipe_menu.play() if som_bipe_menu else None)
                elif abs(mx-cx_d)<130 and not modo_torneio: ciclar_cor("direita",1); (som_bipe_menu.play() if som_bipe_menu else None)
                if my > ALTURA-80:
                    (som_confirmar_menu.play() if som_confirmar_menu else None)
                    if modo_torneio: corrigir_conflitos_torneio()
                    estado="config_quadra"
            elif estado == "config_quadra":
                if my < ALTURA-78:
                    if mx < LARGURA//2: ciclar_quadra(-1); (som_bipe_menu.play() if som_bipe_menu else None)
                    else: ciclar_quadra(1); (som_bipe_menu.play() if som_bipe_menu else None)
                else:
                    (som_confirmar_menu.play() if som_confirmar_menu else None)
                    if modo_torneio: estado="torneio_apresentacao"
                    else: novo_jogo(); iniciar_saque("esquerda")
            elif estado == "torneio_apresentacao":
                (som_confirmar_menu.play() if som_confirmar_menu else None); novo_jogo(); iniciar_saque("esquerda")
            elif estado == "pausado":
                if my < ALTURA//2: estado=estado_antes_pausa
                else: modo_torneio=False; estado="titulo"
            elif estado == "fim_set":
                (som_confirmar_menu.play() if som_confirmar_menu else None)
                ls="esquerda" if placar_esquerda<placar_direita else "direita"
                placar_esquerda=placar_direita=0; iniciar_saque(ls)
            elif estado == "fim_jogo":
                (som_confirmar_menu.play() if som_confirmar_menu else None)
                if modo_torneio:
                    if sets_esquerda > sets_direita:
                        torneio_rodada+=1
                        if torneio_rodada>=len(roster_torneio_atual): estado="torneio_campeao"
                        else: preparar_rodada_torneio(); estado="torneio_apresentacao"
                    else: estado="torneio_eliminado"
                else: estado="titulo"
            elif estado in ("torneio_campeao","torneio_eliminado"):
                (som_confirmar_menu.play() if som_confirmar_menu else None); modo_torneio=False; dificuldade_ia_atual=DIFICULDADE_IA_PADRAO; estado="titulo"

        if evento.type == pygame.KEYDOWN:

            if estado == "titulo":

                if evento.key in (pygame.K_SPACE, pygame.K_RETURN):

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    menu_opcao = 0

                    estado = "menu_principal"



            elif estado == "menu_principal":

                if evento.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):

                    menu_opcao = 1 - menu_opcao

                    (som_bipe_menu.play() if som_bipe_menu else None)

                elif evento.key == pygame.K_ESCAPE:

                    estado = "titulo"

                elif evento.key in (pygame.K_SPACE, pygame.K_RETURN):

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    slot_selecionado = 0

                    if menu_opcao == 0:  # Partida Rapida

                        modo_torneio = False

                        dificuldade_ia_atual = DIFICULDADE_IA_PADRAO

                        estado = "config_jogadores"

                    else:               # Torneio

                        modo_torneio = True

                        torneio_rodada = 0

                        sortear_torneio()

                        preparar_rodada_torneio()

                        estado = "config_jogadores"



            elif estado == "config_jogadores":

                navegaveis = slots_navegaveis()

                if evento.key in (pygame.K_UP, pygame.K_w):

                    slot_selecionado = (slot_selecionado - 1) % len(navegaveis)

                    (som_bipe_menu.play() if som_bipe_menu else None)

                elif evento.key in (pygame.K_DOWN, pygame.K_s):

                    slot_selecionado = (slot_selecionado + 1) % len(navegaveis)

                    (som_bipe_menu.play() if som_bipe_menu else None)

                elif evento.key == pygame.K_LEFT:

                    ciclar_ocupante(navegaveis[slot_selecionado], -1)

                    (som_bipe_menu.play() if som_bipe_menu else None)

                elif evento.key == pygame.K_RIGHT:

                    ciclar_ocupante(navegaveis[slot_selecionado], 1)

                    (som_bipe_menu.play() if som_bipe_menu else None)

                elif evento.key == pygame.K_ESCAPE:

                    estado = "titulo"

                elif evento.key in (pygame.K_SPACE, pygame.K_RETURN):

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    slot_selecionado = 0

                    estado = "config_cores"



            elif estado == "config_cores":

                if modo_torneio:

                    # No torneio so da pra escolher a cor do proprio time; a do adversario e fixa

                    if evento.key == pygame.K_LEFT:

                        ciclar_cor("esquerda", -1)

                        (som_bipe_menu.play() if som_bipe_menu else None)

                    elif evento.key == pygame.K_RIGHT:

                        ciclar_cor("esquerda", 1)

                        (som_bipe_menu.play() if som_bipe_menu else None)

                    elif evento.key == pygame.K_ESCAPE:

                        estado = "config_jogadores"

                    elif evento.key in (pygame.K_SPACE, pygame.K_RETURN):

                        (som_confirmar_menu.play() if som_confirmar_menu else None)

                        corrigir_conflitos_torneio()

                        estado = "config_quadra"

                else:

                    if evento.key in (pygame.K_LEFT, pygame.K_a):

                        slot_selecionado = 0  # seleciona time esquerda

                        (som_bipe_menu.play() if som_bipe_menu else None)

                    elif evento.key in (pygame.K_RIGHT, pygame.K_d):

                        slot_selecionado = 1  # seleciona time direita

                        (som_bipe_menu.play() if som_bipe_menu else None)

                    elif evento.key in (pygame.K_UP, pygame.K_w):

                        ciclar_cor("esquerda" if slot_selecionado == 0 else "direita", -1)

                        (som_bipe_menu.play() if som_bipe_menu else None)

                    elif evento.key in (pygame.K_DOWN, pygame.K_s):

                        ciclar_cor("esquerda" if slot_selecionado == 0 else "direita", 1)

                        (som_bipe_menu.play() if som_bipe_menu else None)

                    elif evento.key == pygame.K_ESCAPE:

                        slot_selecionado = 0

                        estado = "config_jogadores"

                    elif evento.key in (pygame.K_SPACE, pygame.K_RETURN):

                        (som_confirmar_menu.play() if som_confirmar_menu else None)

                        estado = "config_quadra"



            elif estado == "config_quadra":

                if evento.key == pygame.K_LEFT:

                    ciclar_quadra(-1)

                    (som_bipe_menu.play() if som_bipe_menu else None)

                elif evento.key == pygame.K_RIGHT:

                    ciclar_quadra(1)

                    (som_bipe_menu.play() if som_bipe_menu else None)

                elif evento.key == pygame.K_ESCAPE:

                    estado = "config_cores"

                elif evento.key in (pygame.K_SPACE, pygame.K_RETURN):

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    if modo_torneio:

                        estado = "torneio_apresentacao"

                    else:

                        novo_jogo()

                        iniciar_saque("esquerda")



            elif estado == "torneio_apresentacao":

                if evento.key in (pygame.K_SPACE, pygame.K_RETURN):

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    novo_jogo()

                    iniciar_saque("esquerda")



            elif estado in ("jogando", "saque", "saque_viagem"):

                if evento.key in (pygame.K_ESCAPE, pygame.K_p):

                    estado_antes_pausa = estado

                    estado = "pausado"



            elif estado == "pausado":

                if evento.key in (pygame.K_ESCAPE, pygame.K_p):

                    estado = estado_antes_pausa

                elif evento.key == pygame.K_m:

                    modo_torneio = False

                    estado = "titulo"



            elif estado == "fim_set":

                if evento.key == pygame.K_SPACE:

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    lado_saque = "esquerda" if placar_esquerda < placar_direita else "direita"

                    placar_esquerda = 0

                    placar_direita = 0

                    iniciar_saque(lado_saque)



            elif estado == "fim_jogo":

                if evento.key == pygame.K_SPACE:

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    if modo_torneio:

                        if sets_esquerda > sets_direita:

                            torneio_rodada += 1

                            if torneio_rodada >= len(roster_torneio_atual):

                                estado = "torneio_campeao"

                            else:

                                preparar_rodada_torneio()

                                estado = "torneio_apresentacao"

                        else:

                            estado = "torneio_eliminado"

                    else:

                        estado = "titulo"



            elif estado in ("torneio_campeao", "torneio_eliminado"):

                if evento.key == pygame.K_SPACE:

                    (som_confirmar_menu.play() if som_confirmar_menu else None)

                    modo_torneio = False

                    dificuldade_ia_atual = DIFICULDADE_IA_PADRAO

                    estado = "titulo"



    # ============ ESTADO: TITULO ============

    touch_controls.update()
    menu_frame += 1



    if estado == "titulo":

        desenhar_quadra()



        # Gradiente escuro sobre a quadra

        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(170)

        overlay.fill((0, 0, 20))

        tela.blit(overlay, (0, 0))



        # Sombra do titulo

        sombra = fonte_titulo.render("VOLLEYBOUND", True, (20, 80, 160))

        tela.blit(sombra, (LARGURA // 2 - sombra.get_width() // 2 + 4, ALTURA // 2 - 110 + 4))

        # Titulo principal

        titulo_surf = fonte_titulo.render("VOLLEYBOUND", True, (255, 255, 255))

        tela.blit(titulo_surf, (LARGURA // 2 - titulo_surf.get_width() // 2, ALTURA // 2 - 110))



        # Linha decorativa

        larg_linha = 320

        pygame.draw.line(tela, (80, 160, 255),

                         (LARGURA // 2 - larg_linha // 2, ALTURA // 2 - 20),

                         (LARGURA // 2 + larg_linha // 2, ALTURA // 2 - 20), 2)



        # Texto piscante "Toque para jogar"

        if (menu_frame // 30) % 2 == 0:

            press_surf = fonte_media.render("Toque para jogar", True, (200, 230, 255))

            tela.blit(press_surf, (LARGURA // 2 - press_surf.get_width() // 2, ALTURA // 2 + 20))



    # ============ ESTADO: MENU PRINCIPAL ============

    elif estado == "menu_principal":

        desenhar_quadra()



        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(165)

        overlay.fill((0, 0, 20))

        tela.blit(overlay, (0, 0))



        # Titulo menor no topo

        t = fonte_grande.render("VOLLEYBOUND", True, (255, 255, 255))

        tela.blit(t, (LARGURA // 2 - t.get_width() // 2, 60))

        pygame.draw.line(tela, (80, 160, 255),

                         (LARGURA // 2 - 200, 130), (LARGURA // 2 + 200, 130), 2)



        opcoes = ["  Partida Rapida  ", "     Torneio     "]

        descricoes = ["Jogo livre contra amigos ou bots", "Campeonato com multiplas rodadas"]

        y_base = 200

        for i, (label, desc) in enumerate(zip(opcoes, descricoes)):

            selecionado = (i == menu_opcao)

            y = y_base + i * 130



            # Cartao de fundo

            card = pygame.Surface((460, 100), pygame.SRCALPHA)

            if selecionado:

                card.fill((40, 100, 220, 180))

            else:

                card.fill((20, 30, 60, 150))

            tela.blit(card, (LARGURA // 2 - 230, y))



            # Borda do cartao

            borda_cor = (80, 180, 255) if selecionado else (60, 80, 120)

            pygame.draw.rect(tela, borda_cor,

                             (LARGURA // 2 - 230, y, 460, 100), 2, border_radius=4)



            # Seta indicadora

            if selecionado:

                seta = fonte_media.render(">", True, (255, 220, 60))

                tela.blit(seta, (LARGURA // 2 - 210, y + 30))



            # Texto da opcao

            cor_label = (255, 255, 255) if selecionado else (160, 180, 210)

            label_surf = fonte_media.render(label, True, cor_label)

            tela.blit(label_surf, (LARGURA // 2 - label_surf.get_width() // 2, y + 18))



            # Descricao

            cor_desc = (180, 210, 255) if selecionado else (100, 120, 160)

            desc_surf = fonte_pequena.render(desc, True, cor_desc)

            tela.blit(desc_surf, (LARGURA // 2 - desc_surf.get_width() // 2, y + 62))



        texto_centralizado("Toque em uma opcao para confirmar",

                           fonte_pequena, (100, 130, 170), ALTURA - 40)



    # ============ ESTADO: CONFIG JOGADORES ============

    elif estado == "config_jogadores":

        desenhar_quadra()



        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(165)

        overlay.fill((0, 0, 20))

        tela.blit(overlay, (0, 0))



        if modo_torneio:

            titulo_txt = f"TORNEIO  -  RODADA {torneio_rodada + 1} DE {len(roster_torneio_atual)}"

            t_title = fonte_grande.render(titulo_txt, True, (255, 255, 255))

            tela.blit(t_title, (LARGURA // 2 - t_title.get_width() // 2, 35))

            adv_surf = fonte_pequena.render(f"Proximo adversario:  {roster_torneio_atual[torneio_rodada]['nome']}", True, (255, 220, 80))

            tela.blit(adv_surf, (LARGURA // 2 - adv_surf.get_width() // 2, 108))

        else:

            t_title = fonte_grande.render("ESCOLHA OS JOGADORES", True, (255, 255, 255))

            tela.blit(t_title, (LARGURA // 2 - t_title.get_width() // 2, 35))

        pygame.draw.line(tela, (80, 160, 255),

                         (LARGURA // 2 - 280, 115), (LARGURA // 2 + 280, 115), 2)



        navegaveis = slots_navegaveis()

        y_base = 145

        for pos, indice_slot in enumerate(navegaveis):

            slot = config_slots[indice_slot]

            selecionado = (pos == slot_selecionado)

            y = y_base + pos * 72



            card = pygame.Surface((520, 55), pygame.SRCALPHA)

            card.fill((40, 100, 220, 180) if selecionado else (20, 30, 60, 150))

            tela.blit(card, (LARGURA // 2 - 260, y))

            borda_cor = (80, 180, 255) if selecionado else (60, 80, 120)

            pygame.draw.rect(tela, borda_cor,

                             (LARGURA // 2 - 260, y, 520, 55), 2, border_radius=4)



            nome_time = "Esquerda" if slot["time"] == "esquerda" else "Direita"

            texto = f"Time {nome_time}  -  Posicao {slot['posicao'] + 1}:   {slot['ocupante']}"

            cor_t = (255, 255, 255) if selecionado else (160, 180, 210)

            t_surf = fonte_media.render(texto, True, cor_t)

            tela.blit(t_surf, (LARGURA // 2 - t_surf.get_width() // 2, y + 14))

            if selecionado:

                seta = fonte_media.render(">", True, (255, 220, 60))

                tela.blit(seta, (LARGURA // 2 - 245, y + 14))



        texto_centralizado("Toque no slot para mudar | Continuar",

                           fonte_pequena, (100, 130, 170), ALTURA - 30)



    # ============ ESTADO: CONFIG CORES ============

    elif estado == "config_cores":

        desenhar_quadra()



        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(165)

        overlay.fill((0, 0, 20))

        tela.blit(overlay, (0, 0))



        t_title = fonte_grande.render("ESCOLHA AS CORES", True, (255, 255, 255))

        tela.blit(t_title, (LARGURA // 2 - t_title.get_width() // 2, 35))

        pygame.draw.line(tela, (80, 160, 255),

                         (LARGURA // 2 - 240, 108), (LARGURA // 2 + 240, 108), 2)



        preview_esq = obter_preview(CORES_DISPONIVEIS[cor_time_esquerda_idx])

        preview_dir = obter_preview(CORES_DISPONIVEIS[cor_time_direita_idx])

        centro_esq_x = LARGURA // 2 - 200

        centro_dir_x = LARGURA // 2 + 200



        for cx, label, locked in [

            (centro_esq_x, "Time Esquerda", False),

            (centro_dir_x, "Time Direita" + (" (adversario)" if modo_torneio else ""), modo_torneio)

        ]:

            cor_lbl = (140, 160, 190) if locked else (180, 210, 255)

            s = fonte_pequena.render(label, True, cor_lbl)

            tela.blit(s, (cx - s.get_width() // 2, 122))



        tela.blit(preview_esq, (centro_esq_x - preview_esq.get_width() // 2, 148))

        tela.blit(preview_dir, (centro_dir_x - preview_dir.get_width() // 2, 148))



        for i, (cx, cidx, sel) in enumerate([

            (centro_esq_x, cor_time_esquerda_idx, slot_selecionado == 0),

            (centro_dir_x, cor_time_direita_idx, slot_selecionado == 1)

        ]):

            locked = (modo_torneio and i == 1)

            yc = 305

            card = pygame.Surface((220, 45), pygame.SRCALPHA)

            card.fill((40, 100, 220, 180) if (sel and not locked) else (20, 30, 60, 150))

            tela.blit(card, (cx - 110, yc))

            borda = (80, 180, 255) if (sel and not locked) else (60, 80, 120)

            pygame.draw.rect(tela, borda, (cx - 110, yc, 220, 45), 2, border_radius=4)

            prefix = "> " if (sel and not locked) else "  "

            cor_nome = NOMES_CORES[CORES_DISPONIVEIS[cidx]]

            cor_t = (255, 255, 255) if (sel and not locked) else (130, 150, 180)

            ns = fonte_media.render(f"{prefix}{cor_nome}", True, cor_t)

            tela.blit(ns, (cx - ns.get_width() // 2, yc + 10))



        if modo_torneio:

            texto_centralizado("Esq/Dir: trocar sua cor   (cor do adversario e fixa)",

                               fonte_pequena, (100, 130, 170), ALTURA - 50)

        else:

            texto_centralizado("Cima/Baixo: trocar time   Esq/Dir: trocar cor",

                               fonte_pequena, (100, 130, 170), ALTURA - 50)

        texto_centralizado("ESC: voltar   ESPACO: continuar", fonte_pequena, (100, 130, 170), ALTURA - 28)



    # ============ ESTADO: CONFIG QUADRA ============

    elif estado == "config_quadra":

        desenhar_quadra()



        bar_topo = pygame.Surface((LARGURA, 88))

        bar_topo.set_alpha(185)

        bar_topo.fill((0, 0, 20))

        tela.blit(bar_topo, (0, 0))

        t_title = fonte_grande.render("ESCOLHA A QUADRA", True, (255, 255, 255))

        tela.blit(t_title, (LARGURA // 2 - t_title.get_width() // 2, 18))

        pygame.draw.line(tela, (80, 160, 255),

                         (LARGURA // 2 - 240, 80), (LARGURA // 2 + 240, 80), 2)



        bar_baixo = pygame.Surface((LARGURA, 78))

        bar_baixo.set_alpha(185)

        bar_baixo.fill((0, 0, 20))

        tela.blit(bar_baixo, (0, ALTURA - 78))

        nome_atual = NOMES_QUADRAS[QUADRAS_DISPONIVEIS[quadra_idx]]

        t_nome = fonte_media.render(f"<  {nome_atual}  >", True, (255, 255, 255))

        tela.blit(t_nome, (LARGURA // 2 - t_nome.get_width() // 2, ALTURA - 62))

        hint = "Esq/Dir: trocar   ESC: voltar   ESPACO: " + ("continuar" if modo_torneio else "comecar partida")

        h_surf = fonte_pequena.render(hint, True, (100, 130, 170))

        tela.blit(h_surf, (LARGURA // 2 - h_surf.get_width() // 2, ALTURA - 30))



    # ============ ESTADO: TORNEIO - APRESENTACAO DA RODADA ============

    elif estado == "torneio_apresentacao":

        desenhar_quadra()



        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(165)

        overlay.fill((0, 0, 20))

        tela.blit(overlay, (0, 0))



        adversario = roster_torneio_atual[torneio_rodada]



        t_title = fonte_grande.render("TORNEIO", True, (255, 255, 255))

        tela.blit(t_title, (LARGURA // 2 - t_title.get_width() // 2, 35))

        pygame.draw.line(tela, (80, 160, 255),

                         (LARGURA // 2 - 160, 108), (LARGURA // 2 + 160, 108), 2)

        rodada_surf = fonte_media.render(

            f"Rodada {torneio_rodada + 1} de {len(roster_torneio_atual)}", True, (255, 220, 80))

        tela.blit(rodada_surf, (LARGURA // 2 - rodada_surf.get_width() // 2, 120))



        card = pygame.Surface((360, 210), pygame.SRCALPHA)

        card.fill((20, 30, 60, 185))

        tela.blit(card, (LARGURA // 2 - 180, 175))

        pygame.draw.rect(tela, (80, 180, 255),

                         (LARGURA // 2 - 180, 175, 360, 210), 2, border_radius=4)



        adv_lbl = fonte_pequena.render("ADVERSARIO", True, (100, 130, 170))

        tela.blit(adv_lbl, (LARGURA // 2 - adv_lbl.get_width() // 2, 183))

        preview_adv = obter_preview(adversario["cor"])

        tela.blit(preview_adv, (LARGURA // 2 - preview_adv.get_width() // 2, 202))

        nome_surf = fonte_media.render(adversario['nome'], True, (255, 255, 255))

        tela.blit(nome_surf, (LARGURA // 2 - nome_surf.get_width() // 2, 358))



        if (menu_frame // 30) % 2 == 0:

            press = fonte_pequena.render("Toque para comecar", True, (200, 230, 255))

            tela.blit(press, (LARGURA // 2 - press.get_width() // 2, ALTURA - 48))



    # ============ ESTADO: TORNEIO - CAMPEAO ============

    elif estado == "torneio_campeao":

        desenhar_quadra()



        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(165)

        overlay.fill((0, 0, 20))

        tela.blit(overlay, (0, 0))



        sombra = fonte_grande.render("CAMPEAO DO TORNEIO!", True, (100, 70, 0))

        tela.blit(sombra, (LARGURA // 2 - sombra.get_width() // 2 + 3, ALTURA // 2 - 95 + 3))

        t_champ = fonte_grande.render("CAMPEAO DO TORNEIO!", True, (255, 215, 60))

        tela.blit(t_champ, (LARGURA // 2 - t_champ.get_width() // 2, ALTURA // 2 - 95))

        pygame.draw.line(tela, (220, 180, 0),

                         (LARGURA // 2 - 240, ALTURA // 2 - 22), (LARGURA // 2 + 240, ALTURA // 2 - 22), 2)

        txt = fonte_media.render("Voce venceu todos os adversarios!", True, (200, 220, 255))

        tela.blit(txt, (LARGURA // 2 - txt.get_width() // 2, ALTURA // 2 + 5))

        if (menu_frame // 30) % 2 == 0:

            press = fonte_pequena.render("Toque para voltar ao titulo", True, (180, 210, 255))

            tela.blit(press, (LARGURA // 2 - press.get_width() // 2, ALTURA // 2 + 65))



    # ============ ESTADO: TORNEIO - ELIMINADO ============

    elif estado == "torneio_eliminado":

        desenhar_quadra()



        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(165)

        overlay.fill((0, 0, 20))

        tela.blit(overlay, (0, 0))



        sombra = fonte_grande.render("ELIMINADO", True, (70, 15, 15))

        tela.blit(sombra, (LARGURA // 2 - sombra.get_width() // 2 + 3, ALTURA // 2 - 95 + 3))

        t_elim = fonte_grande.render("ELIMINADO", True, (220, 70, 70))

        tela.blit(t_elim, (LARGURA // 2 - t_elim.get_width() // 2, ALTURA // 2 - 95))

        pygame.draw.line(tela, (160, 50, 50),

                         (LARGURA // 2 - 160, ALTURA // 2 - 22), (LARGURA // 2 + 160, ALTURA // 2 - 22), 2)

        txt = fonte_media.render(f"Voce chegou ate a rodada {torneio_rodada + 1}", True, (200, 220, 255))

        tela.blit(txt, (LARGURA // 2 - txt.get_width() // 2, ALTURA // 2 + 5))

        if (menu_frame // 30) % 2 == 0:

            press = fonte_pequena.render("Toque para voltar ao titulo", True, (180, 210, 255))

            tela.blit(press, (LARGURA // 2 - press.get_width() // 2, ALTURA // 2 + 65))



    # ============ ESTADO: SAQUE ============

    elif estado == "saque":

        # A bola segue a mao do sacador (topo do corpo visivel)

        bola.x = servidor.x + servidor.largura // 2

        bola.y = servidor.hitbox_y

        bola.vel_x = 0

        bola.vel_y = 0



        if servidor.teclas is not None:

            teclas_pressionadas = touch_controls.get_fake_keys()



            if teclas_pressionadas[servidor.teclas["esquerda"]]:

                angulo_saque = max(-ANGULO_SAQUE_MAX, angulo_saque - ANGULO_SAQUE_PASSO)

            if teclas_pressionadas[servidor.teclas["direita"]]:

                angulo_saque = min(ANGULO_SAQUE_MAX, angulo_saque + ANGULO_SAQUE_PASSO)



            if teclas_pressionadas[servidor.teclas["pular"]]:

                carga_saque = min(1.0, carga_saque + CARGA_SAQUE_PASSO)

                tempo_segurando_saque += 1

                if tempo_segurando_saque >= SAQUE_VIAGEM_LIMIAR:

                    iniciar_saque_viagem()

            else:

                if carga_saque > 0:

                    executar_saque()

                tempo_segurando_saque = 0

        else:

            timer_saque_cpu += 1

            if timer_saque_cpu >= SAQUE_CPU_DELAY:

                if random.random() < CHANCE_SAQUE_VIAGEM_CPU:

                    iniciar_saque_viagem()  # CPU escolheu o saque de viagem

                else:

                    angulo_saque = random.uniform(-0.3, 0.3)

                    carga_saque = random.uniform(0.5, 0.85)

                    executar_saque()



        desenhar_quadra()

        for jogador in time_esquerda + time_direita:

            jogador.desenhar(tela)

        bola.desenhar(tela)



        if estado == "saque":  # ainda nao sacou neste frame

            # Indicador de forca, flutuando acima da cabeca do sacador (acima do rotulo H1/H2/CPU)

            largura_barra = 60

            x_barra = int(servidor.x + servidor.largura / 2 - largura_barra / 2)

            y_barra = int(servidor.y - 45)

            pygame.draw.rect(tela, BRANCO, (x_barra, y_barra, largura_barra, 10), 2)

            pygame.draw.rect(tela, (200, 50, 50), (x_barra + 2, y_barra + 2, int((largura_barra - 4) * carga_saque), 6))



            if servidor.teclas is not None:

                texto_com_fundo("Segure PULAR p/ carregar | Solte p/ sacar", fonte_pequena, ALTURA - 45)



        texto_com_fundo(f"{placar_esquerda}  -  {placar_direita}", fonte_placar, 15)

        texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_pequena, 155)
        if servidor.teclas is not None:
            touch_controls.draw(tela)
        pause_btn.draw(tela)



    # ============ ESTADO: SAQUE DE VIAGEM (toss no ar, jogador espera pra pular) ============

    elif estado == "saque_viagem":

        teclas_pressionadas = touch_controls.get_fake_keys()



        # Atualiza a fisica da bola normalmente durante o toss

        bola.atualizar(LARGURA, ALTURA - 100)



        # Detecta quando a tecla de pulo e solta (ela pode estar pressionada ainda

        # do carregamento do saque ? so aceita novo pulo depois de soltar uma vez)

        tecla_pulo_agora = servidor.teclas is not None and teclas_pressionadas[servidor.teclas["pular"]]

        if not tecla_pulo_agora:

            saque_viagem_tecla_liberada = True



        # A bola esta subindo: vel_y < 0. Quando ela comeca a descer (vel_y >= 0)

        # o jogador pula automaticamente. Ou o jogador pode pular manualmente,

        # mas so DEPOIS de ter soltado a tecla pelo menos uma vez.

        bola_no_apice = bola.vel_y >= 0

        pular_manual = saque_viagem_tecla_liberada and tecla_pulo_agora



        if bola_no_apice or pular_manual:

            servidor.vel_y = servidor.forca_pulo

            servidor.no_chao = False

            servidor.atacando = True

            servidor.bloqueando = False

            servidor._pular_pressionado_antes = False  # permite que W seja detectado como novo press

            # Ativa o toque de ataque imediatamente para CPU e humano

            servidor._ativar_toque("ataque", frames=60)

            saque_em_andamento = True  # saque nao conta como 1o toque do rally

            estado = "jogando"



        # Desenha a cena durante o toss

        todos_jogadores = time_esquerda + time_direita

        desenhar_quadra()

        for jogador in todos_jogadores:

            jogador.desenhar(tela)

        bola.desenhar(tela)

        texto_com_fundo(f"{placar_esquerda}  -  {placar_direita}", fonte_placar, 15)

        texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_pequena, 70)
        touch_controls.draw(tela)
        pause_btn.draw(tela)

        if servidor.teclas is not None:

            texto_com_fundo("Saque de Viagem! Pressione PULAR para atacar", fonte_pequena, ALTURA - 45)
            touch_controls.draw(tela)
        pause_btn.draw(tela)



    # ============ ESTADO: JOGANDO ============

    elif estado == "jogando":

        teclas_pressionadas = touch_controls.get_fake_keys()



        for time in (time_esquerda, time_direita):

            humanos = [j for j in time if j.teclas is not None]

            cpus = [j for j in time if j.teclas is None]

            for jogador in humanos:

                jogador.atualizar(teclas_pressionadas, LARGURA, ALTURA - 100, bola=bola)

            lado_do_time = time[0].lado if time else None

            numero_toque_estimado = (toques_lado_atual + 1) if lado_do_time == lado_atual else None

            atualizar_time_cpu(cpus, bola, LARGURA, ALTURA - 100, numero_toque_estimado, todos_time=time)



        bola.atualizar(LARGURA, ALTURA - 100)



        lado_da_bola = "esquerda" if bola.x < LARGURA // 2 else "direita"

        if lado_da_bola != lado_atual:

            lado_atual = lado_da_bola

            toques_lado_atual = 0

            jogador_primeiro_toque = None



        todos_jogadores = time_esquerda + time_direita

        ultimo_duplo_toque_lado = None  # lado do jogador que cometeu duplo toque neste frame

        for jogador in todos_jogadores:

            estava_bloqueando = jogador.bloqueando

            numero_toque = toques_lado_atual + 1 if jogador.lado == lado_atual else None

            toque = bola.colidir_com_jogador(jogador, numero_toque=numero_toque)

            if toque == "toque_duplo":

                # Falta: mesmo jogador tocou a bola duas vezes seguidas ? ponto pro adversario

                ultimo_duplo_toque_lado = jogador.lado

            elif toque:

                if jogador.atacando:

                    jogador.iniciar_corte()   # attack apenas para cortadas

                else:

                    jogador.iniciar_toque()   # apenas para toques normais (nao ataques)

                ultimo_toque_lado = jogador.lado

                # Toque de bloqueio nao conta como um dos 3 toques do time (regra real do volei)

                if jogador.lado == lado_atual and not estava_bloqueando:

                    if saque_em_andamento:

                        # Saque de viagem nao conta como 1o toque do rally

                        saque_em_andamento = False

                    else:

                        if numero_toque == 1:

                            jogador_primeiro_toque = jogador

                        toques_lado_atual += 1



        bola.colidir_com_rede(REDE_X, REDE_Y, REDE_LARGURA, REDE_ALTURA)



        ponto_para = None

        ultimo_ponto_foi_fora = False      # reseta a cada frame dentro do estado jogando

        ultimo_ponto_foi_duplo_toque = False  # idem

        if ultimo_duplo_toque_lado is not None:

            # Falta por duplo toque: ponto para o time adversario

            ponto_para = "direita" if ultimo_duplo_toque_lado == "esquerda" else "esquerda"

            ultimo_ponto_foi_duplo_toque = True

        elif toques_lado_atual > 3:

            ponto_para = "direita" if lado_atual == "esquerda" else "esquerda"

        elif bola.y + bola.raio >= ALTURA - 100:

            dentro_da_quadra = CAMPO_X_MIN <= bola.x <= CAMPO_X_MAX

            if dentro_da_quadra:

                ponto_para = "direita" if bola.x < LARGURA // 2 else "esquerda"

            else:

                # Bola caiu fora da linha: falta de quem bateu por ultimo, ponto pro outro time

                ponto_para = "direita" if ultimo_toque_lado == "esquerda" else "esquerda"

                ultimo_ponto_foi_fora = True



        if ponto_para in ("esquerda", "direita"):

            if ponto_para == "esquerda":

                placar_esquerda += 1

            else:

                placar_direita += 1

            (som_ponto.play() if som_ponto else None)

            juiz_pose = "aponta_esquerda" if ponto_para == "esquerda" else "aponta_direita"



            diferenca = abs(placar_esquerda - placar_direita)

            if (placar_esquerda >= PONTOS_POR_SET or placar_direita >= PONTOS_POR_SET) and diferenca >= 2:

                if placar_esquerda > placar_direita:

                    sets_esquerda += 1

                else:

                    sets_direita += 1

                estado = "fim_set"

            else:

                proximo_saque_lado = ponto_para

                timer_pausa_ponto = PAUSA_PONTO_FRAMES

                estado = "ponto_marcado"



        if estado == "jogando":

            desenhar_quadra()

            for jogador in todos_jogadores:

                jogador.desenhar(tela)

            bola.desenhar(tela)



            texto_com_fundo(f"{placar_esquerda}  -  {placar_direita}", fonte_placar, 15)

            texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_pequena, 70)
            touch_controls.draw(tela)
            pause_btn.draw(tela)

        elif estado == "fim_set":

            desenhar_quadra()

            texto_com_fundo("FIM DO SET!", fonte_grande, 150)

            texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_media, 255)

            if not (sets_esquerda >= SETS_PARA_VENCER or sets_direita >= SETS_PARA_VENCER):

                texto_com_fundo("Toque para o proximo set", fonte_pequena, 315)

        elif estado == "ponto_marcado":

            desenhar_quadra()

            for jogador in todos_jogadores:

                jogador.desenhar(tela)

            bola.desenhar(tela)

            texto_com_fundo(f"{placar_esquerda}  -  {placar_direita}", fonte_placar, 15)

            texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_pequena, 70)
            touch_controls.draw(tela)
            pause_btn.draw(tela)

            _msg_ponto = ("PONTO! (DUPLO TOQUE)" if ultimo_ponto_foi_duplo_toque

                          else "PONTO! (BOLA FORA)" if ultimo_ponto_foi_fora

                          else "PONTO!")

            texto_com_fundo(_msg_ponto, fonte_grande, 140)



    # ============ ESTADO: PONTO MARCADO (pausa curta antes do proximo saque) ============

    elif estado == "ponto_marcado":

        timer_pausa_ponto -= 1

        desenhar_quadra()

        for jogador in time_esquerda + time_direita:

            jogador.desenhar(tela)

        bola.desenhar(tela)

        texto_com_fundo(f"{placar_esquerda}  -  {placar_direita}", fonte_placar, 15)

        texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_pequena, 70)
        touch_controls.draw(tela)
        pause_btn.draw(tela)

        _msg_ponto = ("PONTO! (DUPLO TOQUE)" if ultimo_ponto_foi_duplo_toque

                      else "PONTO! (BOLA FORA)" if ultimo_ponto_foi_fora

                      else "PONTO!")

        texto_com_fundo(_msg_ponto, fonte_grande, 140)



        if timer_pausa_ponto <= 0:

            iniciar_saque(proximo_saque_lado)



    # ============ ESTADO: PAUSADO ============

    elif estado == "pausado":

        desenhar_quadra()

        for jogador in time_esquerda + time_direita:

            jogador.desenhar(tela)

        bola.desenhar(tela)



        overlay = pygame.Surface((LARGURA, ALTURA))

        overlay.set_alpha(150)

        overlay.fill((0, 0, 0))

        tela.blit(overlay, (0, 0))



        texto_centralizado(f"{placar_esquerda}  -  {placar_direita}", fonte_placar, BRANCO, 20)

        texto_centralizado("PAUSADO", fonte_grande, BRANCO, 220)

        texto_centralizado("Toque para continuar", fonte_pequena, BRANCO, 310)

        texto_centralizado("Toque na metade inferior para voltar ao menu", fonte_pequena, BRANCO, 340)



    # ============ ESTADO: FIM DE SET (chegou aqui direto, fora do estado "jogando") ============

    elif estado == "fim_set":

        desenhar_quadra()

        texto_com_fundo("FIM DO SET!", fonte_grande, 150)

        texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_media, 255)



        if sets_esquerda >= SETS_PARA_VENCER or sets_direita >= SETS_PARA_VENCER:

            estado = "fim_jogo"

        else:

            texto_com_fundo("Toque para o proximo set", fonte_pequena, 315)



    # ============ ESTADO: FIM DE JOGO ============

    elif estado == "fim_jogo":

        desenhar_quadra()

        vencedor = "ESQUERDA" if sets_esquerda > sets_direita else "DIREITA"

        texto_com_fundo("FIM DE JOGO!", fonte_grande, 150)

        texto_com_fundo(f"Vencedor: {vencedor}", fonte_media, 255)

        texto_com_fundo(f"Sets: {sets_esquerda} - {sets_direita}", fonte_media, 305)

        if modo_torneio:

            texto_com_fundo("Toque para continuar", fonte_pequena, 365)

        else:

            texto_com_fundo("Toque para voltar ao menu", fonte_pequena, 365)



    pygame.display.flip()
    relogio.tick(FPS)



try:
    pygame.quit()
except Exception:
    pass
