# Buduje jednoplikowy plik QuizScanner.exe (Windows).
# Wymaga: Python + zainstalowane zależności + PyInstaller.
#   pip install -r requirements.txt
#   pip install pyinstaller
# Uruchomienie:  powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
#
# WAŻNE: plik wynikowy MA w nazwie numer wersji (np. QuizScanner-v3.0.0.exe).
# Numer bierzemy z quizscanner/__init__.py — jedno miejsce prawdy; wbudowany
# aktualizator porównuje wydanie z GitHuba właśnie z nim.
#
# Ikoną .exe jest zawsze logo programu (assets/logo.ico) — nigdy domyślna
# ikona PyInstallera. Ikonę odtwarza z logo: python tools/make_icon.py

Set-Location (Join-Path $PSScriptRoot "..")

$init = Get-Content "quizscanner\__init__.py" -Raw
if ($init -notmatch 'VERSION\s*=\s*"([^"]+)"') {
    Write-Host "Nie mogę odczytać VERSION z quizscanner\__init__.py" -ForegroundColor Red
    exit 1
}
$Version = $Matches[1]
$Name = "QuizScanner-v$Version"

# Ikona programu. Gdyby jej zabrakło, odtwarzamy ją z logo — .exe nigdy nie
# wychodzi z domyślną ikoną PyInstallera.
$Icon = "assets\logo.ico"
if (-not (Test-Path $Icon)) {
    Write-Host "Brak $Icon — odtwarzam z logo." -ForegroundColor Yellow
    python tools\make_icon.py
    if (-not (Test-Path $Icon)) {
        Write-Host "Nie udało się przygotować ikony — przerywam." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Buduję $Name.exe ..." -ForegroundColor Cyan
# Uwaga: w .exe zasoby leżą płasko — web trafia do <_MEIPASS>\web, dane do <_MEIPASS>\data
# (tak samo jak wylicza je quizscanner/paths.py).
python -m PyInstaller --onefile --noconsole --name $Name `
  --icon $Icon `
  --add-data "assets\logo.ico;assets" `
  --add-data "quizscanner\web;web" `
  --add-data "data\quizzes;data\quizzes" `
  --add-data "data\students.csv;data" `
  --hidden-import quizscanner.cards `
  --hidden-import quizscanner.aruco `
  --hidden-import quizscanner.i18n `
  --hidden-import quizscanner.overlay `
  --hidden-import quizscanner.report `
  --hidden-import quizscanner.updater `
  --noconfirm launcher.py

# Sam Test-Path nie wystarczy: przy błędzie (np. gdy stary .exe jest zajęty
# przez działający program) w dist zostaje poprzedni plik i build wyglądałby
# na udany.
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller zakończył się błędem — plik w dist\ może być stary." -ForegroundColor Red
    exit 1
}

if (Test-Path "dist\$Name.exe") {
    $mb = (Get-Item "dist\$Name.exe").Length / 1MB
    Write-Host ("Gotowe: dist\$Name.exe  ({0:N1} MB)" -f $mb) -ForegroundColor Green
    Write-Host "Wgraj do Releases dokładnie pod tą nazwą (z numerem wersji)." -ForegroundColor Green
    Write-Host "Tag wydania musi brzmieć v$Version — po nim aktualizator poznaje nowszą wersję." -ForegroundColor Green
} else {
    Write-Host "Budowanie nie powiodło się." -ForegroundColor Red
}
