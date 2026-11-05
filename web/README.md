# VolleyBound — Versão Web 🌐

Versão do VolleyBound que roda direto no **navegador**, compilada com [Pygbag](https://pygame-web.github.io/) (Python + WebAssembly).

## Controles (teclado)

| Jogador Esquerda | Jogador Direita |
|-----------------|-----------------|
| **W** — Pular    | **↑** — Pular    |
| **A** — Esquerda | **←** — Esquerda |
| **D** — Direita  | **→** — Direita  |
| **S** — Mergulho | **↓** — Mergulho |
| **Q** — Ataque   | **P** — Ataque   |
| **E** — Bloqueio | **O** — Bloqueio |

## Testar localmente

```bash
pip install pygbag

# Da raiz do projeto:
cp bola.py web/
cp jogador.py web/
cp constantes.py web/
cp -r assets web/

python -m pygbag web/main.py
# Abre em: http://localhost:8000
```

## Deploy automático (GitHub Pages)

O workflow `.github/workflows/deploy_web.yml` faz o build e deploy automaticamente a cada push na branch `master` que altere arquivos do jogo.

### Habilitar GitHub Pages (fazer uma vez)
1. Vá em **Settings → Pages** no repositório
2. Em **Source**, selecione **GitHub Actions**
3. Salve — o próximo push fará o deploy automaticamente

A URL do jogo será: `https://cientstaaa.github.io/volleybound/`
