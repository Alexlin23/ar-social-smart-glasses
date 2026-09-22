@echo off
setlocal
set "AR_PYTHON=%~dp0.venv-ar\Scripts\python.exe"
if not exist "%AR_PYTHON%" (
  echo Run setup_ar.ps1 first to create the dedicated environment.
  exit /b 2
)
"%AR_PYTHON%" "%~dp0run_ar_view.py" %*
set "AR_RESULT=%ERRORLEVEL%"
if not "%AR_RESULT%"=="0" echo AR exited with code %AR_RESULT%. See the message above.
exit /b %AR_RESULT%
