#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICON_SCALABLE_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON_256_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$BIN_DIR" "$APPS_DIR" "$ICON_SCALABLE_DIR" "$ICON_256_DIR"
chmod +x "$APP_DIR/main.py" "$APP_DIR/src/execution/privileged_worker.py"

ln -sf "$APP_DIR/main.py" "$BIN_DIR/origin-uninstaller"
ln -sf "$APP_DIR/main.py" "$BIN_DIR/desinstalador-apps"

# Copia ícones
if [ -f "$APP_DIR/assets/origin-uninstaller.svg" ]; then
    cp -f "$APP_DIR/assets/origin-uninstaller.svg" "$ICON_SCALABLE_DIR/origin-uninstaller.svg"
    cp -f "$APP_DIR/assets/origin-uninstaller.svg" "$ICON_SCALABLE_DIR/br.com.chrystian.OriginUninstaller.svg"
fi

if [ -f "$APP_DIR/assets/origin-uninstaller.png" ]; then
    cp -f "$APP_DIR/assets/origin-uninstaller.png" "$ICON_256_DIR/origin-uninstaller.png"
    cp -f "$APP_DIR/assets/origin-uninstaller.png" "$ICON_256_DIR/br.com.chrystian.OriginUninstaller.png"
fi

# Cria o arquivo .desktop integrado ao ambiente de trabalho (GNOME / Wayland)
cat > "$APPS_DIR/br.com.chrystian.OriginUninstaller.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Origin Uninstaller (Desinstalador de Apps)
Comment=Desinstale aplicativos e limpe completamente suas configurações, caches e pastas residuais
Exec=/usr/bin/python3 $APP_DIR/main.py
Icon=$APP_DIR/assets/origin-uninstaller.svg
Terminal=false
Categories=System;Utility;PackageManager;GTK;
StartupNotify=true
StartupWMClass=br.com.chrystian.OriginUninstaller
EOF

chmod +x "$APPS_DIR/br.com.chrystian.OriginUninstaller.desktop"

# Atualiza caches do sistema gráfico
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "✔ Origin Uninstaller instalado com sucesso no sistema!"
echo "• Atalhos criados: $BIN_DIR/origin-uninstaller e $BIN_DIR/desinstalador-apps"
echo "• Lançador no menu de aplicativos do GNOME configurado."
