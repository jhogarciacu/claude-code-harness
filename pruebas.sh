#!/usr/bin/env bash
# Corre todas las verificaciones del arnés: estructura, pruebas de cada plugin y sintaxis de scripts.
# Uso: ./pruebas.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PYTHONDONTWRITEBYTECODE=1

echo "== Estructura del marketplace y los plugins"
python3 herramientas/validar.py

echo "== Pruebas"
total=0
# Cada carpeta con archivos test_*.py, en herramientas/ y en cualquier parte de plugins/.
while IFS= read -r carpeta; do
    if ! salida=$(python3 -m unittest discover -s "$carpeta" 2>&1); then
        echo "$salida"
        echo "✗ fallan las pruebas de $carpeta"
        exit 1
    fi
    corridas=$(echo "$salida" | sed -n 's/^Ran \([0-9]*\) test.*/\1/p')
    echo "-- $carpeta: ${corridas:-0} pruebas"
    total=$((total + ${corridas:-0}))
done < <(find herramientas plugins -name 'test_*.py' -printf '%h\n' 2>/dev/null | sort -u)

if [ "$total" -eq 0 ]; then
    echo "✗ no se ejecutó ninguna prueba"
    exit 1
fi

echo "== Sintaxis de scripts"
for script in ./*.sh; do
    bash -n "$script"
done
echo "✓ todo en verde ($total pruebas)"
