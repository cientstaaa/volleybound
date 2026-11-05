# VolleyBound 🏐

Jogo de vôlei 2D feito com Python + Pygame.

## Estrutura do Projeto

```
volleyball_game_V2.1/
├── pc/
│   ├── main.py           # Versão PC (teclado)
│   ├── main_mobile.py    # Versão PC com layout mobile
│   └── VolleyballGame.spec  # Config PyInstaller (gerar .exe)
│
├── android/
│   └── main_android.py   # Versão Android (controles touch)
│
├── tools/
│   ├── serve_mobile.py          # Servidor local para testes web
│   └── converter_sprites_base.py  # Converte sprites para palette swap
│
├── assets/           # Imagens e sons compartilhados
├── bola.py           # Módulo compartilhado: física da bola
├── jogador.py        # Módulo compartilhado: lógica do jogador
├── constantes.py     # Módulo compartilhado: constantes globais
├── buildozer.spec    # Config do build Android
└── .github/
    └── workflows/
        └── build_apk.yml  # GitHub Actions: gera o APK automaticamente
```

## Como Rodar

### PC
```bash
python pc/main.py
```

### Android (APK)
O APK é gerado automaticamente pelo GitHub Actions a cada push na branch `master`.
Acesse **Actions → Build Android APK → Artifacts** para baixar o APK.

## Dependências
- Python 3.11+
- pygame 2.6+
