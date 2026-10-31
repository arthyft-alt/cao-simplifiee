@echo off
rem Lance CAO simplifiee avec le bon Python (environnement conda "cao").
rem Double-cliquer sur ce fichier, ou glisser un document .caop/.caoa/.caom dessus.
set "PYTHON_CAO=%USERPROFILE%\miniforge3\envs\cao\python.exe"
if not exist "%PYTHON_CAO%" (
  echo Python de lenvironnement "cao" introuvable : %PYTHON_CAO%
  pause
  exit /b 1
)
cd /d "%~dp0"
"%PYTHON_CAO%" -m cao %*
if errorlevel 1 pause
