@echo off
REM Prism DNS Server Startup Script for Windows (SCRUM-18)
REM Cross-platform startup script for production deployment

setlocal EnableDelayedExpansion

REM Script directory and project root
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%\..

REM Default configuration
set DEFAULT_CONFIG=%PROJECT_ROOT%\config\server.yaml
set DEFAULT_VENV=%PROJECT_ROOT%\venv

REM Initialize variables
set CONFIG_FILE=%DEFAULT_CONFIG%
set VENV_PATH=%DEFAULT_VENV%
set DAEMON_MODE=false
set PID_FILE=

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="-c" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--config" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-v" (
    set VENV_PATH=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--venv" (
    set VENV_PATH=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-d" (
    set DAEMON_MODE=true
    shift
    goto :parse_args
)
if "%~1"=="--daemon" (
    set DAEMON_MODE=true
    shift
    goto :parse_args
)
if "%~1"=="-p" (
    set PID_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--pid" (
    set PID_FILE=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help

echo Unknown option: %~1
goto :show_help

:args_done

REM Function to show help
:show_help
echo Prism DNS Server Startup Script for Windows
echo.
echo USAGE:
echo     %~nx0 [OPTIONS]
echo.
echo OPTIONS:
echo     -c, --config FILE    Configuration file path (default: %DEFAULT_CONFIG%)
echo     -v, --venv PATH      Virtual environment path (default: %DEFAULT_VENV%)
echo     -d, --daemon         Run as background service
echo     -p, --pid FILE       PID file for daemon mode
echo     -h, --help           Show this help message
echo.
echo EXAMPLES:
echo     %~nx0                                         # Start with default configuration
echo     %~nx0 -c C:\prism\server.yaml                # Start with custom config
echo     %~nx0 -d -p C:\temp\prism-server.pid         # Start as background service
echo.
echo ENVIRONMENT VARIABLES:
echo     PRISM_SERVER_TCP_PORT     Override TCP server port
echo     PRISM_SERVER_API_PORT     Override API server port
echo     PRISM_DATABASE_PATH       Override database file path
echo     PRISM_LOGGING_LEVEL       Override logging level
echo.
exit /b 0

REM Function to log messages
:log
echo [%date% %time%] %~1
goto :eof

REM Function to check prerequisites
:check_prerequisites
call :log "Checking prerequisites..."

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required but not installed
    exit /b 1
)

REM Check virtual environment
if not exist "%VENV_PATH%" (
    echo Error: Virtual environment not found at %VENV_PATH%
    echo Please create it with: python -m venv %VENV_PATH%
    exit /b 1
)

REM Check configuration file
if not exist "%CONFIG_FILE%" (
    if "%CONFIG_FILE%"=="%DEFAULT_CONFIG%" (
        call :log "Configuration file not found, using defaults"
    ) else (
        echo Error: Configuration file not found: %CONFIG_FILE%
        exit /b 1
    )
) else (
    call :log "Using configuration: %CONFIG_FILE%"
)

call :log "Prerequisites check passed"
goto :eof

REM Function to activate virtual environment
:activate_venv
call :log "Activating virtual environment..."

call "%VENV_PATH%\Scripts\activate.bat"
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    exit /b 1
)

REM Check if server module is available
python -c "import server.main" >nul 2>&1
if errorlevel 1 (
    echo Error: Server module not found. Please install dependencies:
    echo   pip install -r requirements.txt
    exit /b 1
)

call :log "Virtual environment activated"
goto :eof

REM Function to start server
:start_server
cd /d "%PROJECT_ROOT%"

set CMD=python -m server.main

REM Add config file if it exists
if exist "%CONFIG_FILE%" (
    set CMD=!CMD! --config "%CONFIG_FILE%"
)

if "%DAEMON_MODE%"=="true" (
    call :log "Starting Prism DNS Server as background service..."
    
    set LOG_FILE=%PROJECT_ROOT%\server_daemon.log
    
    if not "%PID_FILE%"=="" (
        REM Start as background service with PID file
        start /b "" !CMD! > "!LOG_FILE!" 2>&1
        call :log "Server started as background service"
        call :log "PID file: %PID_FILE%"
        call :log "Log file: !LOG_FILE!"
    ) else (
        REM Start as background service without PID file
        start /b "" !CMD! > "!LOG_FILE!" 2>&1
        call :log "Server started as background service"
        call :log "Log file: !LOG_FILE!"
    )
) else (
    call :log "Starting Prism DNS Server..."
    call :log "Press Ctrl+C to stop"
    
    REM Start in foreground
    !CMD!
)

goto :eof

REM Main execution
call :log "Prism DNS Server Startup Script for Windows"
call :log "Project root: %PROJECT_ROOT%"

call :check_prerequisites
if errorlevel 1 exit /b 1

call :activate_venv
if errorlevel 1 exit /b 1

call :start_server