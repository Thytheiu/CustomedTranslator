#define MyAppVersion "1.0.0"

[Setup]
AppId={{A0EBBE38-4F68-40FC-B8F8-9D348C55EAD1}
AppName=译间
AppVersion={#MyAppVersion}
AppPublisher=Thytheiu
AppPublisherURL=https://github.com/Thytheiu/CustomedTranslator
AppSupportURL=https://github.com/Thytheiu/CustomedTranslator/issues
DefaultDirName={localappdata}\Programs\TranslatorByGPT
DefaultGroupName=译间
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=TranslatorByGPT-Setup-{#MyAppVersion}-x64
SetupIconFile=..\assets\translator.ico
UninstallDisplayIcon={app}\TranslatorByGPT.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "..\dist\TranslatorByGPT.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\译间"; Filename: "{app}\TranslatorByGPT.exe"
Name: "{autodesktop}\译间"; Filename: "{app}\TranslatorByGPT.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TranslatorByGPT.exe"; Description: "启动译间"; Flags: nowait postinstall skipifsilent

[Messages]
chinesesimplified.WelcomeLabel2=安装程序将在您的电脑上安装 [name/ver]。%n%n安装前，请通过托盘菜单退出正在运行的译间。%n%n使用翻译功能需要 Microsoft Edge WebView2 运行时，以及您自己的 DeepSeek API Key。
