@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo ELG Downloader V1.4 - Gerando executaveis com icone
echo ============================================================
echo.

py -3.11 -m pip install --upgrade pip
if errorlevel 1 goto :erro

py -3.11 -m pip install --upgrade "yt-dlp[default,curl-cffi]" yt-dlp-ejs pyinstaller
if errorlevel 1 goto :erro

echo.
echo [1/2] Gerando ELG_YTDLP_Helper.exe...
py -3.11 -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name "ELG_YTDLP_Helper" ^
  ELG_YTDLP_Helper.py
if errorlevel 1 goto :erro

echo.
echo [2/2] Gerando ELG_Downloader.exe com icone ELG...
py -3.11 -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "ELG_Downloader" ^
  --icon "assets\ELG_Downloader.ico" ^
  ELG_Downloader_PC_V1.4.py
if errorlevel 1 goto :erro

echo.
echo ============================================================
echo EXECUTAVEIS CRIADOS
echo ============================================================
echo dist\ELG_Downloader.exe
echo dist\ELG_YTDLP_Helper.exe
echo.
exit /b 0

:erro
echo.
echo ERRO durante a compilacao.
pause
exit /b 1
