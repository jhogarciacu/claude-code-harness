#!/usr/bin/env bash
# Enlaza el CLAUDE.md global del arnés a ~/.claude/CLAUDE.md.
# Los agentes se instalan aparte, como plugin (ver README.md).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGEN="$REPO/global/CLAUDE.md"
DESTINO="$HOME/.claude/CLAUDE.md"

mkdir -p "$HOME/.claude"

if [ -L "$DESTINO" ] && [ "$(readlink -f "$DESTINO")" = "$(readlink -f "$ORIGEN")" ]; then
    echo "Ya instalado: $DESTINO → $ORIGEN"
    exit 0
fi

if [ -e "$DESTINO" ] || [ -L "$DESTINO" ]; then
    RESPALDO="$DESTINO.respaldo-$(date +%Y%m%d-%H%M%S)"
    mv "$DESTINO" "$RESPALDO"
    echo "Había un CLAUDE.md global; quedó respaldado en $RESPALDO"
fi

ln -s "$ORIGEN" "$DESTINO"
echo "Instalado: $DESTINO → $ORIGEN"
echo "Siguiente paso, dentro de Claude Code:"
echo "  /plugin marketplace add $REPO"
echo "  /plugin install arnes@claude-code-harness"
