; ─────────────────────────────────────────────────────────────
; instalador_lazarza.iss  —  Inno Setup 6
; ─────────────────────────────────────────────────────────────
; Descargar Inno Setup: https://jrsoftware.org/isdl.php
; Compilar: Abrir este archivo en Inno Setup y presionar F9
; ─────────────────────────────────────────────────────────────

#define AppName      "Inventario Zarza"
#define AppVersion   "1.8.2"
#define AppPublisher "La Zarza Distribuidora"
#define AppExeName   "InventarioJH.exe"
#define AppIcon      "assets\icon.ico"

; Carpeta de salida de PyInstaller
#define BuildDir     "dist\InventarioJH"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
DefaultDirName={autopf}\InventarioJH
DefaultGroupName={#AppName}
AllowNoIcons=no
OutputDir=installer_output
OutputBaseFilename=Instalador_InventarioJH_v{#AppVersion}
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
; Imagen lateral del instalador (opcional, 164x314 px .bmp)
; WizardImageFile=assets\wizard_banner.bmp

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon";    Description: "Crear acceso directo en el Escritorio"; \
    GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "Crear acceso directo en Inicio rápido"; \
    GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; Todos los archivos del build de PyInstaller
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Menú Inicio
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"

; Escritorio
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

; Inicio rápido
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "Iniciar {#AppName} ahora"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpiar base de datos y config al desinstalar (opcional — comentar si no se quiere)
; Type: filesandordirs; Name: "{localappdata}\InventarioJH"
