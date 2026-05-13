# Sincronizeaza LAB1..LAB11 din LAB-uri catre clone-ul GitHub, cu commit per folder.
# Rulare din orice loc: powershell -ExecutionPolicy Bypass -File "C:\Users\Andrei\Desktop\SEM_2\IA\LAB-uri\LAB11\_sync_github.ps1"
$ErrorActionPreference = "Stop"
$BASE = (Get-Item (Join-Path $PSScriptRoot "..")).FullName
$REPO = Join-Path $BASE "Artificial-Inteligence_CTI_Laboratories"

Set-Location $BASE
if (-not (Test-Path (Join-Path $REPO ".git"))) {
    git clone "https://github.com/AndreiValeanu22/Artificial-Inteligence_CTI_Laboratories.git" $REPO
}
else {
    Push-Location $REPO
    try { git pull --rebase --autostash 2>$null } catch {}
    Pop-Location
}

Set-Location $REPO

$gitignore = @"
.ipynb_checkpoints/
__pycache__/
*.pyc
.venv/
"@
Set-Content -Path (Join-Path $REPO ".gitignore") -Value $gitignore -Encoding utf8
git add .gitignore
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    cmd /c "git commit -m chore-gitignore-checkpoints"
}

$labs = @(
    @{ d = "LAB1";  m = "LAB1: Introducere Python" },
    @{ d = "LAB2";  m = "LAB2: Cautare - algoritm A*" },
    @{ d = "LAB3";  m = "LAB3: Hill Climbing" },
    @{ d = "LAB4";  m = "LAB4: PCSP" },
    @{ d = "LAB5";  m = "LAB5: MCTS" },
    @{ d = "LAB6";  m = "LAB6: Random Forest" },
    @{ d = "LAB7";  m = "LAB7: Regresie liniara" },
    @{ d = "LAB8";  m = "LAB8: Regresie logistica" },
    @{ d = "LAB9";  m = "LAB9: Introducere MLP" },
    @{ d = "LAB10"; m = "LAB10: Seminar retele Bayesiene" },
    @{ d = "LAB11"; m = "LAB11: Eliminarea variabilelor (inferenta Bayes)" }
)

foreach ($L in $labs) {
    $from = Join-Path $BASE $L.d
    $to = Join-Path $REPO $L.d
    if (-not (Test-Path $from)) {
        Write-Host "SKIP missing: $from"
        continue
    }
    New-Item -ItemType Directory -Force -Path $to | Out-Null
    robocopy $from $to /MIR /XD .ipynb_checkpoints /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed $($L.d) exit $LASTEXITCODE"
    }
    git add -- $L.d
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        $tmp = Join-Path $env:TEMP ("gitmsg_" + [Guid]::NewGuid().ToString("n") + ".txt")
        Set-Content -Path $tmp -Value $L.m -Encoding utf8
        cmd /c "git commit -F `"$tmp`""
        Remove-Item -Force $tmp -ErrorAction SilentlyContinue
    }
    else {
        Write-Host "No changes: $($L.d)"
    }
}

$readmeSrc = Join-Path $BASE "LAB11\README_GITHUB_RO.md"
if (-not (Test-Path $readmeSrc)) {
    throw "Lipseste README sursa: $readmeSrc"
}
Copy-Item -Force $readmeSrc (Join-Path $REPO "README.md")
git add README.md
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    $tmp = Join-Path $env:TEMP ("gitmsg_" + [Guid]::NewGuid().ToString("n") + ".txt")
    Set-Content -Path $tmp -Value "Documentatie: README agregat laboratoare IA (RO)" -Encoding utf8
    cmd /c "git commit -F `"$tmp`""
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
}

git status -sb
git push
