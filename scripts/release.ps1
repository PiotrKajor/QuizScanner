# Wydanie nowej wersji QuizScannera (Windows).
#
# Buduje plik .exe, sprawdza aplikację, wyciąga opis z CHANGELOG.md i publikuje
# wydanie na GitHubie. Numer wersji pochodzi z quizscanner/__init__.py — to
# jedyne miejsce, w którym się go podnosi.
#
# Wymagania: Python 3.10+, pip install -r requirements.txt pyinstaller, gh auth login
#
# Użycie:
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1 -DryRun
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1 -SkipTests

param(
    [switch]$DryRun,       # zbuduj i pokaż, co poszłoby na GitHuba, ale nie publikuj
    [switch]$SkipTests,    # pomiń tools/selftest.py (tylko gdy wiesz, co robisz)
    [switch]$UpdateNotes   # nadpisz opis istniejącego wydania tekstem z CHANGELOG.md
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Krok($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host $text -ForegroundColor Red; exit 1 }

# --- 1. Numer wersji ---------------------------------------------------------
$init = Get-Content "quizscanner\__init__.py" -Raw
if ($init -notmatch 'VERSION\s*=\s*"([^"]+)"') {
    Fail "Nie mogę odczytać VERSION z quizscanner\__init__.py"
}
$Version = $Matches[1]
$Tag = "v$Version"
$Name = "QuizScanner-v$Version"
$Exe = "dist\$Name.exe"
Write-Host "Wydanie QuizScanner $Version (tag $Tag)" -ForegroundColor Green

# --- 2. Narzędzia ------------------------------------------------------------
foreach ($cmd in @("python", "gh")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Fail "Brak polecenia '$cmd'. Zainstaluj je i spróbuj ponownie."
    }
}
gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "Nie jesteś zalogowany do GitHuba. Uruchom: gh auth login" }

# --- 3. Stan repozytorium ----------------------------------------------------
Krok "Sprawdzam repozytorium"
if ((git status --porcelain) -and -not $DryRun) {
    Fail "Są niezatwierdzone zmiany. Zrób commit i push przed wydaniem."
}
if (git tag --list $Tag) {
    Write-Host "Tag $Tag już istnieje — wydanie zostanie zaktualizowane." -ForegroundColor Yellow
}

# --- 4. Opis wydania z CHANGELOG.md -----------------------------------------
Krok "Wyciągam opis z CHANGELOG.md"
$changelog = Get-Content "CHANGELOG.md" -Raw
# Sekcja od "## [wersja]" do następnego nagłówka "## [".
$pattern = "(?ms)^## \[" + [regex]::Escape($Version) + "\][^\r\n]*\r?\n(.*?)(?=^## \[|\z)"
$m = [regex]::Match($changelog, $pattern)
if (-not $m.Success) {
    Fail "CHANGELOG.md nie ma sekcji '## [$Version]'. Dopisz ją przed wydaniem."
}
$Notes = $m.Groups[1].Value.Trim()
$NotesFile = Join-Path $env:TEMP "quizscanner-release-$Version.md"
$Notes | Set-Content $NotesFile -Encoding UTF8
Write-Host "Opis: $($Notes.Split("`n").Count) linii"

# --- 5. Sprawdzenie aplikacji -----------------------------------------------
if (-not $SkipTests) {
    Krok "Szybkie sprawdzenie, czy wszystko działa"
    python tools\check_polish.py
    if ($LASTEXITCODE -ne 0) { Fail "Kontrola polskich znaków nie przeszła." }
    python tools\selftest.py
    if ($LASTEXITCODE -ne 0) { Fail "tools\selftest.py nie przeszedł — nie wydaję." }
}

# --- 6. Budowanie .exe -------------------------------------------------------
Krok "Buduję $Name.exe"
& "$PSScriptRoot\build_exe.ps1"
if (-not (Test-Path $Exe)) { Fail "Nie powstał plik $Exe." }
$mb = (Get-Item $Exe).Length / 1MB
Write-Host ("Gotowe: $Exe ({0:N1} MB)" -f $mb) -ForegroundColor Green

# Program musi w ogóle wstawać — .exe sprawdzamy trybem serwerowym.
Krok "Sprawdzam zbudowany plik"
$proc = Start-Process -FilePath $Exe -ArgumentList "--serve", "--port", "8123", "--no-camera", "--no-browser" -PassThru
try {
    Start-Sleep -Seconds 8
    $resp = Invoke-WebRequest "http://127.0.0.1:8123/api/state" -UseBasicParsing -TimeoutSec 10
    if ($resp.StatusCode -ne 200) { Fail "Zbudowany .exe nie odpowiada na /api/state." }
    Write-Host "Zbudowany .exe odpowiada poprawnie." -ForegroundColor Green
} finally {
    # Jednoplikowy .exe uruchamia proces potomny — zabicie samego rodzica
    # zostawia go przy życiu, a on trzyma plik i blokuje kolejny build.
    if ($proc -and -not $proc.HasExited) {
        taskkill /PID $proc.Id /T /F 2>&1 | Out-Null
    }
    Start-Sleep -Seconds 1
}

# --- 7. Publikacja -----------------------------------------------------------
if ($DryRun) {
    Krok "DryRun — nie publikuję"
    Write-Host "Poszłoby na GitHuba:"
    Write-Host "  tag:   $Tag"
    Write-Host "  tytuł: QuizScanner $Version"
    Write-Host "  plik:  $Exe"
    Write-Host "  opis:  $NotesFile"
    exit 0
}

Krok "Publikuję wydanie na GitHubie"
gh release view $Tag 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    # Wydanie (także szkic) już istnieje: dokładamy plik i publikujemy.
    # Opisu NIE ruszamy — skoro szkic istnieje, ktoś napisał go świadomie.
    # Nadpisanie tekstem z CHANGELOG.md: przełącznik -UpdateNotes.
    gh release upload $Tag $Exe --clobber
    if ($UpdateNotes) {
        gh release edit $Tag --title "QuizScanner $Version" --notes-file $NotesFile --draft=false --latest
    } else {
        gh release edit $Tag --title "QuizScanner $Version" --draft=false --latest
    }
} else {
    gh release create $Tag $Exe --title "QuizScanner $Version" --notes-file $NotesFile --latest
}
if ($LASTEXITCODE -ne 0) { Fail "Publikacja wydania nie powiodła się." }

Write-Host "`nWydanie $Tag opublikowane." -ForegroundColor Green
gh release view $Tag --web
