<#
setup_ssh_ev3.ps1

PowerShell helper to automate SSH key setup for an EV3 brick.

What it does:
- Ensures you have an SSH key (ed25519) in $env:USERPROFILE\.ssh\id_ed25519
- Copies the public key to the EV3 (uses scp; you'll enter the password once)
- Appends the public key into /home/robot/.ssh/authorized_keys on the brick
- Fixes permissions on the brick (.ssh -> 700, authorized_keys -> 600)
- Optionally chmod +x the routine scripts on the brick (/home/robot/rutina_botella.py and rutina_caja.py)

Usage:
1. Edit the $EV3_USER and $EV3_HOST variables below if needed.
2. Open PowerShell in this repo folder and run:
<#
setup_ssh_ev3.ps1

PowerShell helper to automate SSH key setup for an EV3 brick.

What it does:
- Ensures you have an SSH key (ed25519) in $env:USERPROFILE\.ssh\id_ed25519
- Copies the public key to the EV3 (uses scp; you'll enter the password once)
- Appends the public key into /home/robot/.ssh/authorized_keys on the brick
- Fixes permissions on the brick (.ssh -> 700, authorized_keys -> 600)
- Optionally chmod +x the routine scripts on the brick (/home/robot/rutina_botella.py and rutina_caja.py)

Usage:
1. Edit the $EV3_USER and $EV3_HOST variables below if needed.
2. Open PowerShell in this repo folder and run:
   powershell -ExecutionPolicy Bypass -File .\setup_ssh_ev3.ps1

Note: This script will prompt for the EV3 password once (to run scp/ssh). It does not store passwords.
#>

param(
    [string]$EV3_USER = 'robot',
    [string]$EV3_HOST = 'ev3dev.local',
    [string]$KeyFile = "$env:USERPROFILE\.ssh\id_ed25519",
    [switch]$MakeRoutinesExecutable
)

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m)  { Write-Host "[ERROR] $m" -ForegroundColor Red }

# Ensure .ssh directory exists locally
$sshDir = Join-Path $env:USERPROFILE '.ssh'
if (-not (Test-Path $sshDir)) {
    Write-Info "Creando directorio $sshDir"
    New-Item -ItemType Directory -Path $sshDir | Out-Null
}

# Ensure key exists
$pubKey = "$KeyFile.pub"
if (-not (Test-Path $KeyFile)) {
    Write-Info "No se encontró clave SSH en $KeyFile. Generando nueva clave ed25519 (sin passphrase)."
    ssh-keygen -t ed25519 -f $KeyFile -N "" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "ssh-keygen falló (exit $LASTEXITCODE). Revisa tu instalación de OpenSSH."
        exit 1
    }
} else {
    Write-Info "Se encontró clave privada en $KeyFile"
}

if (-not (Test-Path $pubKey)) {
    Write-Err "Clave pública no encontrada ($pubKey)."; exit 1
}

# Copy public key to EV3 (temporary file)
$tempRemote = "/home/$EV3_USER/temp_pubkey_$((Get-Random)).pub"
Write-Info "Copiando clave pública a $EV3_USER@$EV3_HOST:$tempRemote (se pedirá la contraseña del brick)"

# Using & to run external commands; PowerShell sets $LASTEXITCODE
& scp $pubKey "$EV3_USER@$EV3_HOST:$tempRemote"
if ($LASTEXITCODE -ne 0) {
    Write-Err "scp falló con exit code $LASTEXITCODE. No se pudo copiar la clave al brick."
    exit 1
}

# Append public key into authorized_keys and fix perms
$sshCmds = @(
    "mkdir -p /home/$EV3_USER/.ssh",
    "touch /home/$EV3_USER/.ssh/authorized_keys",
    "cat $tempRemote >> /home/$EV3_USER/.ssh/authorized_keys",
    "rm -f $tempRemote",
    "chmod 700 /home/$EV3_USER/.ssh",
    "chmod 600 /home/$EV3_USER/.ssh/authorized_keys",
    "chown -R $EV3_USER:$EV3_USER /home/$EV3_USER/.ssh"
)
$sshFull = $sshCmds -join "; "
Write-Info "Ejecutando comandos remotos para instalar la clave y ajustar permisos (se pedirá la contraseña una vez más si es necesario)"
& ssh "$EV3_USER@$EV3_HOST" "$sshFull"
if ($LASTEXITCODE -ne 0) {
    Write-Err "ssh falló con exit code $LASTEXITCODE. Revisa la conectividad y credenciales."
    exit 1
}

Write-Info "Clave pública añadida a /home/$EV3_USER/.ssh/authorized_keys y permisos corregidos."

# Optionally make routines executable
if ($MakeRoutinesExecutable.IsPresent) {
    $routines = @('/home/robot/rutina_botella.py', '/home/robot/rutina_caja.py')
    foreach ($r in $routines) {
        Write-Info "Intentando marcar $r como ejecutable en el brick"
        $cmd = "if [ -f $r ]; then chmod +x $r; ls -l $r; else echo 'NO_EXISTE $r'; fi"
        & ssh "$EV3_USER@$EV3_HOST" "$cmd"
    }
    Write-Info "Hecho (nota: se mostrará salida para cada archivo)."
}

Write-Info "Configuración completada. Prueba: ssh $EV3_USER@$EV3_HOST (no debería pedir contraseña)."
Write-Info "Si aún pide contraseña, revisa /var/log/auth.log en el brick o confirma permisos de ~/.ssh y authorized_keys."

# Optional: print sample ~/.ssh/config entry
Write-Host "`nPuedes añadir esto a tu $env:USERPROFILE\.ssh\config para facilitar el acceso:" -ForegroundColor Green
Write-Host "Host ev3" -ForegroundColor Green
Write-Host "    HostName $EV3_HOST" -ForegroundColor Green
Write-Host "    User $EV3_USER" -ForegroundColor Green
Write-Host "    IdentityFile $KeyFile`n" -ForegroundColor Green

Write-Info "Listo."
