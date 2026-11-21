ELG DOWNLOADER V1.4 — PROJETO DE SETUP

O QUE ESTA PRONTO
=================
- Icone ELG convertido para .ICO multirresolucao.
- Icone aplicado ao ELG_Downloader.exe pelo PyInstaller.
- O mesmo icone aplicado ao Setup.exe.
- Instalador Inno Setup em portugues.
- Instalacao padrao em Program Files\ELG Downloader.
- Atalho no Menu Iniciar.
- Opcao de atalho na Area de Trabalho.
- Desinstalador.
- Opcoes para instalar FFmpeg e Deno via winget.

COMO GERAR O SETUP
==================
No Windows, abra a pasta no PowerShell/CMD e execute:

    build_setup.bat

O script:
1. instala/atualiza as dependencias Python;
2. gera ELG_Downloader.exe;
3. gera ELG_YTDLP_Helper.exe;
4. instala o Inno Setup 6 via winget se necessario;
5. compila o instalador.

RESULTADO
=========
Setup_Output\ELG_Downloader_Setup_V1.4.exe

IMPORTANTE
==========
O Setup.exe final precisa ser compilado no Windows porque Inno Setup e
PyInstaller para Windows geram binarios nativos do Windows.

ARQUIVOS PRINCIPAIS
===================
assets\ELG_Downloader.ico
ELG_Downloader_PC_V1.4.py
ELG_YTDLP_Helper.py
build_windows.bat
build_setup.bat
installer\ELG_Downloader_Setup.iss
