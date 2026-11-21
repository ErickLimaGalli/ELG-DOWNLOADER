@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo ELG Downloader V1.4 - BUILD COMPLETO + SETUP
echo ============================================================
echo.

call build_windows.bat
if errorlevel 1 goto :erro

set "ISCC="

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
        set "ISCC=%%I"
        goto :found
    )
)

:found
if not defined ISCC (
    echo Inno Setup 6 nao encontrado.
    echo Tentando instalar via winget...
    winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :sem_inno

    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
)

if not defined ISCC goto :sem_inno

echo.
echo Compilando Setup...
"%ISCC%" "installer\ELG_Downloader_Setup.iss"
if errorlevel 1 goto :erro

echo.
echo ============================================================
echo SETUP CRIADO COM SUCESSO
echo ============================================================
echo.
echo Arquivo:
echo Setup_Output\ELG_Downloader_Setup_V1.4.exe
echo.
echo O icone ELG foi aplicado ao aplicativo e ao instalador.
echo.
pause
exit /b 0

:sem_inno
echo.
echo Nao foi possivel localizar/instalar o Inno Setup 6.
echo Instale manualmente com:
echo winget install --id JRSoftware.InnoSetup -e
echo Depois execute este arquivo novamente.
pause
exit /b 1

:erro
echo.
echo Ocorreu um erro durante o build.
pause
exit /b 1
