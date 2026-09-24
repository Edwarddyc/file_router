@echo off
setlocal

set "PI_CODING_AGENT_DIR=%~dp0.pi-agent"
set "PI_MONO_ROOT=%~dp0pi-mono"
set "PI_CLI=%PI_MONO_ROOT%\packages\coding-agent\dist\bundle\cli.js"
set "NODE_EXE=D:\Program Files\nodejs\node.exe"

if not exist "%NODE_EXE%" (
  echo [pi-mono] Node.js not found: %NODE_EXE%
  exit /b 1
)

if not exist "%PI_CLI%" (
  echo [pi-mono] Compiled Pi CLI not found: %PI_CLI%
  echo [pi-mono] Build pi-mono before starting it.
  exit /b 1
)

pushd "%PI_MONO_ROOT%"
"%NODE_EXE%" "%PI_CLI%" --offline %*
set "PI_EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %PI_EXIT_CODE%
