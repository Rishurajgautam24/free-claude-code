@echo off
setlocal EnableExtensions

title Free Claude Code Launcher Installer

echo.
echo ============================================================
echo       FREE CLAUDE CODE LAUNCHER INSTALLER
echo ============================================================
echo.

:: ------------------------------------------------------------
:: Resolve paths explicitly
:: ------------------------------------------------------------

set "INSTALLER_DIR=%~dp0"

for %%I in ("%INSTALLER_DIR%..") do (
    set "PROJECT_DIR=%%~fI"
)

echo Installer directory:
echo   %INSTALLER_DIR%
echo.

echo Project directory:
echo   %PROJECT_DIR%
echo.

:: ------------------------------------------------------------
:: Check required FCC files
:: ------------------------------------------------------------

echo Checking FCC installation...
echo.

if not exist "%PROJECT_DIR%\.venv\Scripts\fcc-server.exe" (
    echo [ERROR] fcc-server.exe was not found.
    echo.
    echo Expected:
    echo   %PROJECT_DIR%\.venv\Scripts\fcc-server.exe
    echo.
    pause
    exit /b 1
)

echo [OK] fcc-server.exe found.

if not exist "%PROJECT_DIR%\.venv\Scripts\fcc-claude.exe" (
    echo [ERROR] fcc-claude.exe was not found.
    echo.
    echo Expected:
    echo   %PROJECT_DIR%\.venv\Scripts\fcc-claude.exe
    echo.
    pause
    exit /b 1
)

echo [OK] fcc-claude.exe found.
echo.

:: ------------------------------------------------------------
:: Check templates
:: ------------------------------------------------------------

if not exist "%INSTALLER_DIR%Start-FCC.template" (
    echo [ERROR] Start-FCC.template was not found.
    echo.
    echo Expected:
    echo   %INSTALLER_DIR%Start-FCC.template
    echo.
    pause
    exit /b 1
)

echo [OK] Start-FCC.template found.

if not exist "%INSTALLER_DIR%Stop-FCC.template" (
    echo [ERROR] Stop-FCC.template was not found.
    echo.
    echo Expected:
    echo   %INSTALLER_DIR%Stop-FCC.template
    echo.
    pause
    exit /b 1
)

echo [OK] Stop-FCC.template found.
echo.

:: ------------------------------------------------------------
:: Generate launcher files
:: ------------------------------------------------------------

echo Creating Start-FCC.bat...

copy /Y "%INSTALLER_DIR%Start-FCC.template" "%INSTALLER_DIR%Start-FCC.bat" >nul

if errorlevel 1 (
    echo [ERROR] Failed to create Start-FCC.bat.
    echo.
    pause
    exit /b 1
)

echo [OK] Start-FCC.bat created.
echo.

echo Creating Stop-FCC.bat...

copy /Y "%INSTALLER_DIR%Stop-FCC.template" "%INSTALLER_DIR%Stop-FCC.bat" >nul

if errorlevel 1 (
    echo [ERROR] Failed to create Stop-FCC.bat.
    echo.
    pause
    exit /b 1
)

echo [OK] Stop-FCC.bat created.
echo.

:: ------------------------------------------------------------
:: Final verification
:: ------------------------------------------------------------

echo ============================================================
echo                    INSTALLATION COMPLETE
echo ============================================================
echo.

if exist "%INSTALLER_DIR%Start-FCC.bat" (
    echo [OK] Start-FCC.bat
) else (
    echo [FAILED] Start-FCC.bat
)

if exist "%INSTALLER_DIR%Stop-FCC.bat" (
    echo [OK] Stop-FCC.bat
) else (
    echo [FAILED] Stop-FCC.bat
)

echo.
echo Launcher directory:
echo   %INSTALLER_DIR%
echo.

echo You can now run:
echo   Start-FCC.bat
echo.
echo or:
echo   Stop-FCC.bat
echo.

echo ============================================================
echo.

pause
exit /b 0