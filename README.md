# 🏐 VolleyBound

**Jogo de vôlei 2D** feito em Python com Pygame — disponível para **PC (Windows)** e **Android**!

---

## 📥 Download

| Plataforma | Download | Requisitos |
|------------|----------|------------|
| 🖥️ **Windows** | [Baixar ZIP](https://github.com/cientstaaa/volleybound/releases/latest) | Windows 10/11 (64-bit) |
| 📱 **Android** | [Baixar APK](https://github.com/cientstaaa/volleybound/releases/latest) | Android 5.0+ (arm64) |

> Vá para a página de [**Releases**](https://github.com/cientstaaa/volleybound/releases) e baixe o arquivo para sua plataforma.

---

## 🎮 Controles

### PC

| Ação | Jogador 1 | Jogador 2 |
|------|-----------|-----------|
| Mover | `A` / `D` | `←` / `→` |
| Pular | `W` | `↑` |
| Recepção | `S` | `↓` |
| Peixinho | `Q` | `Ctrl Dir` |
| Bloqueio / Ataque | `Espaço` | `Shift Dir` |
| Pausar | `ESC` ou `P` | — |

### Android (Touch)
- **Joystick** horizontal na esquerda
- **Botões contextuais** na direita:
  - No chão: **Peixinho**, **Pular**, **Recepção**
  - No ar: **Atacar**, **Set**

---

## 🏆 Modos de Jogo

### Partida Rápida
Jogue uma partida contra a CPU ou com um amigo no mesmo dispositivo.

### Torneio
Enfrente uma sequência de adversários cada vez mais fortes. Vença todas as rodadas para ser o campeão!

---

## ⚙️ Mecânicas

- Cada time tem até **3 toques** para devolver a bola
- **Saque**: segure Pular para carregar a força, solte para sacar
- **Saque de Viagem**: segure por mais tempo — a bola sobe e o jogador pula pra cortar!
- **Recepção**: defenda a bola levantando-a pro seu lado
- **Peixinho**: mergulhe pra salvar bolas difíceis
- **Ataque**: pule perto da rede e corte a bola pro lado adversário
- **Set**: no ar, levante a bola pro atacante finalizar
- Primeiro a **25 pontos** (com 2 de diferença) vence o set
- Melhor de **3 sets** vence a partida

---

## 🛠️ Para Desenvolvedores

### Estrutura do Projeto
```
volleybound/
├── bola.py              # Lógica da bola (compartilhado)
├── jogador.py           # Lógica do jogador (compartilhado)
├── constantes.py        # Constantes do jogo (compartilhado)
├── assets/              # Sprites, sons e fundos
├── android/             # Versão Android
│   ├── main_android.py
│   ├── buildozer.spec
│   └── icon.png
├── pc/                  # Versão PC
│   ├── main.py
│   ├── COMO_JOGAR.txt
│   └── VolleyballGame.spec
└── .github/workflows/
    └── build_apk.yml    # Build automático do APK
```

### Rodar no PC (desenvolvimento)
```bash
# Requer Python 3.10+ e pygame
pip install pygame-ce
python pc/main.py
```

### Gerar executável Windows
```bash
pip install pyinstaller
python -m PyInstaller pc/VolleyballGame.spec
```

### Gerar APK Android
O APK é gerado automaticamente pelo **GitHub Actions** a cada push no branch `master`.

---

## 📄 Licença

Projeto pessoal de estudo e diversão.
