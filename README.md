# <img src="assets/origin-uninstaller.svg" width="38" valign="middle" alt="Origin Uninstaller Logo" /> Origin Uninstaller (`origin-uninstaller`)

**Desinstalador Nativo & Central de Limpeza Profunda para Linux (GTK4 / Libadwaita)** que localiza todos os aplicativos instalados no sistema, remove seus pacotes e elimina completamente pastas residuais, arquivos de configurações (`~/.config`), caches (`~/.cache`), sandboxes Flatpak e dados locais.

---

## ✨ Principais Funcionalidades

1. **Varredura Completa Multi-Fonte no Sistema**:
   - **Pacotes Nativos APT / DEB**: mapeia arquivos `.desktop` em `/usr/share/applications` para seus respectivos pacotes via `dpkg`, listando os programas e aplicativos gráficos reais do usuário.
   - **Flatpak (Flathub)**: identifica e lista aplicativos Flatpak (escopo de sistema e de usuário), com tamanhos instalados e sandboxes.
   - **Snap / Standalone / /opt**: detecta aplicativos locais instalados manualmente em `/opt` e atalhos em `~/.local/share/applications`.

2. **Detector de Resíduos & Limpeza Profunda (*Deep Clean*)**:
   - Ao selecionar um aplicativo para remoção, o sistema vasculha inteligentemente o disco calculando o tamanho exato de:
     - `~/.config/<nome_do_app>` *(Configurações e perfis do usuário)*
     - `~/.cache/<nome_do_app>` *(Caches acumulados e dados temporários)*
     - `~/.local/share/<nome_do_app>` *(Dados e extensões locais)*
     - `~/.local/state/<nome_do_app>` *(Estado e histórico do aplicativo)*
     - `~/.<nome_do_app>` *(Diretórios legados na home, ex: ~/.dbeaver4, ~/.anydesk)*
     - `~/.var/app/<app_id>` *(Sandboxes isoladas de aplicativos Flatpak)*
     - `/etc/<app>` e `/opt/<app>` *(Arquivos de configuração e instalação no sistema)*
   - Exibe a lista completa de resíduos com caixas de seleção (*checkboxes*), permitindo que você escolha exatamente o que apagar.

3. **Confirmação Dupla com Alerta de Segurança (Prevenção de Acidentes)**:
   - **Etapa 1 (Revisão)**: Janela modal detalhada com o comando exato (`apt-get purge --autoremove -y` ou `flatpak uninstall --delete-data -y`), cálculo dinâmico do espaço total liberado em MB/GB e seleção de pastas.
   - **Etapa 2 (Confirmação Definitiva)**: Diálogo de alerta destrutivo reforçado antes de qualquer ação ser executada na máquina.

4. **Salvaguarda de Integridade do Sistema (*Safety Guard*)**:
   - Trava de proteção automática contra a remoção acidental de pacotes vitais da distribuição Debian/Linux (ex: `systemd`, `linux-image`, `libc6`, `sudo`, `coreutils`, `gnome-shell`, `apt`, `dpkg`).
   - Bloqueio estrito contra exclusão de diretórios de sistema protegidos (`/`, `/usr`, `/var/lib/dpkg`, `/home`, etc.).

5. **Interface Nativa Moderna GTK4 + Libadwaita**:
   - Design moderno alinhado com o GNOME e com o **Origin Updater**.
   - Cards de filtro rápido: *Todos os Apps*, *APT / DEB*, *Flatpak* e *Snap & Outros*.
   - Barra de pesquisa instantânea em tempo real.
   - Visualização dedicada com barra de progresso e **terminal de log em tempo real** (via PTY) para acompanhar a execução de ponta a ponta.

---

## 🖥️ Instalação e Integração ao Sistema

Para instalar o Origin Uninstaller, criar os atalhos no terminal e integrar o ícone ao menu do GNOME:

```bash
cd /home/chrystian/origin-uninstaller
./install.sh
```

Isso disponibilizará os comandos no terminal:
- `origin-uninstaller`
- `desinstalador-apps`

E criará o lançador **"Origin Uninstaller (Desinstalador de Apps)"** na sua Área de Trabalho e na Busca do GNOME / Wayland.

---

## 🚀 Uso Rápido via Terminal

Para listar todos os aplicativos instalados diretamente no terminal sem abrir a interface gráfica:

```bash
origin-uninstaller --list
```

Para abrir a interface gráfica completa:

```bash
origin-uninstaller
```

---

## 📂 Estrutura do Projeto

```
origin-uninstaller/
├── main.py                     # Ponto de entrada Desktop (GTK4 / Libadwaita)
├── install.sh                  # Script de instalação com atalho .desktop e ícone
├── assets/                     # Identidade visual (SVG e PNG em alta resolução)
│   ├── origin-uninstaller.svg
│   └── origin-uninstaller.png
├── src/
│   ├── models.py               # Modelos de dados (InstalledApp, ResidualItem, AppType)
│   ├── scanners/               # Mecanismos de varredura
│   │   ├── desktop_resolver.py # Mapeamento de .desktop e índices dpkg
│   │   ├── apt_scanner.py      # Varredura de pacotes APT/DEB
│   │   ├── flatpak_scanner.py  # Varredura de aplicativos Flatpak
│   │   ├── snap_scanner.py     # Varredura de Snaps (se disponíveis)
│   │   ├── standalone_scanner.py # Varredura de apps locais em /opt e ~/.local
│   │   └── __init__.py         # Orquestrador unificado SystemScanner
│   ├── cleaner/                # Localizador e salvaguardas de limpeza profunda
│   │   ├── residual_finder.py  # Localizador inteligente de pastas do app
│   │   └── safety_guard.py     # Lista de proteção de pacotes e caminhos vitais
│   ├── execution/              # Motores de execução
│   │   ├── uninstaller_engine.py # Coordenação em background thread
│   │   └── privileged_worker.py  # Worker autenticado via pkexec
│   └── ui/                     # Interface do Usuário (GTK4 / Libadwaita)
│       ├── window.py           # Janela principal com cards de resumo e busca
│       ├── app_row.py          # Linha de aplicativo com badges e botão de ação
│       ├── confirm_dialog.py   # Modal de confirmação dupla e seleção de pastas
│       └── log_view.py         # Terminal monospaçado de logs em tempo real
└── tests/                      # Suite de testes unitários automatizados
    ├── test_models.py
    ├── test_safety_guard.py
    ├── test_scanners.py
    └── test_residual_finder.py
```

---

## 🛡️ Licença

Desenvolvido para compor o ecossistema Origin junto ao **Origin Updater**. Distribuído sob a licença MIT.
