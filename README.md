# VolleyBound 🏐

Jogo de vôlei 2D feito em Python com Pygame.

## Estrutura do Projeto

```
volleyball_game_V2.1/
├── bola.py              # Lógica da bola (compartilhado)
├── jogador.py           # Lógica do jogador (compartilhado)
├── constantes.py        # Constantes do jogo (compartilhado)
├── assets/              # Sprites, sons e fundos
├── android/             # Versão Android (APK via GitHub Actions)
│   ├── main_android.py
│   ├── buildozer.spec
│   └── icon.png
├── pc/                  # Versão PC (executável via PyInstaller)
│   ├── main.py
│   ├── COMO_JOGAR.txt
│   └── VolleyballGame.spec
├── tools/               # Scripts utilitários
└── .github/workflows/
    └── build_apk.yml    # Build automático do APK
```

## Como Jogar

### PC
```bash
python pc/main.py
```
Ou gere o executável:
```bash
cd pc && python -m PyInstaller VolleyballGame.spec
```

Veja `pc/COMO_JOGAR.txt` para controles detalhados.

### Android
O APK é gerado automaticamente pelo GitHub Actions a cada push.
Baixe na aba **Actions** > **Build APK** > **Artifacts**.

## Controles (PC)

| Ação | Jogador 1 | Jogador 2 |
|------|-----------|-----------|
| Mover | A / D | ← / → |
| Pular | W | ↑ |
| Recepção | S | ↓ |
| Peixinho | Q | Ctrl Dir |
| Bloqueio/Ataque | Espaço | Shift Dir |

## Modos de Jogo
- **Partida Rápida** — jogue contra a CPU ou com um amigo
- **Torneio** — enfrente adversários cada vez mais fortes
