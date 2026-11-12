param(
    [Parameter(Mandatory=$true)][int]$ParentProcessId,
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$ExpectedHash,
    [Parameter(Mandatory=$true)][string]$Application
)
$ErrorActionPreference = 'Stop'
$Log = "$Installer.update.log"
try {
    try { $Parent = [System.Diagnostics.Process]::GetProcessById($ParentProcessId) }
    catch [System.ArgumentException] { $Parent = $null }
    if ($Parent -and -not $Parent.WaitForExit(120000)) { throw 'La aplicacion sigue abierta.' }
    $Running = Get-Process -Name 'TuleVenta' -ErrorAction SilentlyContinue
    if ($Running) { throw 'Hay otra instancia de TuleVenta abierta.' }
    if ((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash -ne $ExpectedHash) {
        throw 'SHA-256 incorrecto antes de instalar.'
    }
    $Directory = [System.IO.Path]::GetDirectoryName($Application)
    $Arguments = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /UPDATEONLY /DIR="' + $Directory + '" /LOG="' + $Log + '"'
    $Setup = Start-Process -FilePath $Installer -ArgumentList $Arguments -PassThru -Wait
    if ($Setup.ExitCode -ne 0) { throw "Instalador fallo: $($Setup.ExitCode)" }
    Start-Process -FilePath $Application
} catch {
    $_.Exception.Message | Out-File -LiteralPath $Log -Append -Encoding utf8
    exit 1
}