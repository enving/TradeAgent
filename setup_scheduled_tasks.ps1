# PowerShell script to setup Windows Task Scheduler for automated trading
# Run as Administrator: Right-click -> "Run with PowerShell"

$ProjectPath = "C:\Users\t.wilms\Documents\german_ai_cookbook\german_ai_cookbook\projects\TradeAgent"

Write-Host "Setting up automated trading tasks..." -ForegroundColor Green
Write-Host ""

# Create logs directory if it doesn't exist
$LogsPath = Join-Path $ProjectPath "logs"
if (-not (Test-Path $LogsPath)) {
    New-Item -ItemType Directory -Path $LogsPath | Out-Null
    Write-Host "Created logs directory: $LogsPath" -ForegroundColor Yellow
}

# Task 1: Morning Pre-Market Scan (7:00 AM Berlin)
Write-Host "Creating Task 1: Morning Pre-Market Scan (7:00 AM daily)..." -ForegroundColor Cyan
$Action1 = New-ScheduledTaskAction -Execute "$ProjectPath\schedule_morning_scan.bat"
$Trigger1 = New-ScheduledTaskTrigger -Daily -At "07:00AM"
$Settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal1 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited

try {
    Unregister-ScheduledTask -TaskName "TradeAgent_MorningScan" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName "TradeAgent_MorningScan" -Action $Action1 -Trigger $Trigger1 -Settings $Settings1 -Principal $Principal1 -Description "Pre-market momentum scan (7:00 AM Berlin)" | Out-Null
    Write-Host "  SUCCESS: Morning scan scheduled" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to create morning scan task" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
}

# Task 2: Pre-Open Scan (15:00 Berlin / 9:00 AM ET)
Write-Host "Creating Task 2: Pre-Open Scan (3:00 PM daily)..." -ForegroundColor Cyan
$Action2 = New-ScheduledTaskAction -Execute "$ProjectPath\schedule_preopen_scan.bat"
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "03:00PM"
$Settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal2 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited

try {
    Unregister-ScheduledTask -TaskName "TradeAgent_PreOpenScan" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName "TradeAgent_PreOpenScan" -Action $Action2 -Trigger $Trigger2 -Settings $Settings2 -Principal $Principal2 -Description "Pre-open momentum scan (3:00 PM Berlin)" | Out-Null
    Write-Host "  SUCCESS: Pre-open scan scheduled" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to create pre-open scan task" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
}

# Task 3: Market Hours Scan (16:00 Berlin / 10:00 AM ET)
Write-Host "Creating Task 3: Market Hours Scan (4:00 PM daily)..." -ForegroundColor Cyan
$Action3 = New-ScheduledTaskAction -Execute "$ProjectPath\schedule_market_scan.bat"
$Trigger3 = New-ScheduledTaskTrigger -Daily -At "04:00PM"
$Settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal3 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited

try {
    Unregister-ScheduledTask -TaskName "TradeAgent_MarketScan" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName "TradeAgent_MarketScan" -Action $Action3 -Trigger $Trigger3 -Settings $Settings3 -Principal $Principal3 -Description "Market hours momentum scan (4:00 PM Berlin)" | Out-Null
    Write-Host "  SUCCESS: Market scan scheduled" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to create market scan task" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
}

# Task 4: Daily ML Trade Labeling (18:00 Berlin / 12:00 PM ET)
Write-Host "Creating Task 4: ML Trade Labeling (6:00 PM daily)..." -ForegroundColor Cyan
$Action4 = New-ScheduledTaskAction -Execute "$ProjectPath\schedule_label_trades.bat"
$Trigger4 = New-ScheduledTaskTrigger -Daily -At "06:00PM"
$Settings4 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal4 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited

try {
    Unregister-ScheduledTask -TaskName "TradeAgent_LabelTrades" -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName "TradeAgent_LabelTrades" -Action $Action4 -Trigger $Trigger4 -Settings $Settings4 -Principal $Principal4 -Description "Daily ML trade labeling (6:00 PM Berlin)" | Out-Null
    Write-Host "  SUCCESS: ML labeling scheduled" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to create labeling task" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SCHEDULED TASKS SETUP COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Daily Schedule (Berlin Time):" -ForegroundColor Yellow
Write-Host "  07:00 - Morning Pre-Market Scan" -ForegroundColor White
Write-Host "  15:00 - Pre-Open Scan (30 min before US market)" -ForegroundColor White
Write-Host "  16:00 - Market Hours Scan (during US market)" -ForegroundColor White
Write-Host "  18:00 - ML Trade Labeling" -ForegroundColor White
Write-Host ""
Write-Host "To view tasks: Open Task Scheduler -> Task Scheduler Library" -ForegroundColor Yellow
Write-Host "To disable: Right-click task -> Disable" -ForegroundColor Yellow
Write-Host "To remove all: Run 'Remove-ScheduledTask -TaskName TradeAgent_* -Confirm:$false'" -ForegroundColor Yellow
Write-Host ""
Write-Host "Logs will be saved to: $LogsPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
