# Free Claude Code Launcher

A simple Windows launcher for [Free Claude Code](https://github.com/Alishahryar1/free-claude-code).

This installer generates two convenient launcher scripts:

- `Start-FCC.bat` — starts the FCC Server and FCC Claude in separate Git Bash windows.
- `Stop-FCC.bat` — stops FCC Claude and the FCC Server.

The launcher automatically resolves the Free Claude Code project path, so it does **not** depend on a hard-coded installation directory.

---

## 📁 Structure

Before running the installer:

```text
free-claude-code/
└── installer-launcher/
    ├── Installer-Free-Claude-Code-Launcher.bat
    ├── Start-FCC.template
    ├── Stop-FCC.template
    └── README.md
```

After running the installer:

```text
free-claude-code/
└── installer-launcher/
    ├── Installer-Free-Claude-Code-Launcher.bat
    ├── Start-FCC.template
    ├── Stop-FCC.template
    ├── Start-FCC.bat
    ├── Stop-FCC.bat
    └── README.md
```

`Start-FCC.bat` and `Stop-FCC.bat` are generated automatically from their corresponding template files.

---

## 🚀 Installation

### 1. Clone Free Claude Code

Clone the repository normally:

```bash
git clone https://github.com/Alishahryar1/free-claude-code.git
cd free-claude-code
```

Complete the normal Free Claude Code setup first.

The project should contain:

```text
.venv/
└── Scripts/
    ├── fcc-server.exe
    └── fcc-claude.exe
```

### 2. Open the launcher directory

Navigate to:

```text
installer-launcher/
```

### 3. Run the installer

Double-click:

```text
Installer-Free-Claude-Code-Launcher.bat
```

The installer checks that the required FCC executables exist and then generates:

```text
Start-FCC.bat
Stop-FCC.bat
```

---

## ▶️ Starting Free Claude Code

Run:

```text
Start-FCC.bat
```

The launcher will:

1. Resolve the Free Claude Code project directory.
2. Locate Git Bash.
3. Verify the FCC executables.
4. Start the FCC Server.
5. Wait briefly for the server to initialize.
6. Start FCC Claude in a separate Git Bash window.

Both processes remain visible in their own windows so errors can be inspected if something goes wrong.

---

## 🛑 Stopping Free Claude Code

Run:

```text
Stop-FCC.bat
```

The stop script terminates:

```text
fcc-claude.exe
claude.exe
fcc-server.exe
```

It also checks port `8082` as a fallback and terminates the process listening on that port if necessary.

---

## 📍 Portable Project Path

The launcher does **not** use a hard-coded path such as:

```text
C:\Users\ASUS\free-claude-code
```

Instead, it resolves the project directory relative to the location of the launcher.

For example, all of these installation paths can work:

```text
C:\Users\ASUS\free-claude-code
D:\Projects\free-claude-code
E:\AI\free-claude-code
C:\Users\Someone\Desktop\free-claude-code
```

The important requirement is that the repository structure remains intact:

```text
free-claude-code/
├── .venv/
│   └── Scripts/
│       ├── fcc-server.exe
│       └── fcc-claude.exe
│
└── installer-launcher/
```

---

## ⚙️ Requirements

Before using the launcher, make sure you have:

- Windows
- Git for Windows
- Git Bash
- Free Claude Code configured and working
- FCC virtual environment (`.venv`)
- `fcc-server.exe`
- `fcc-claude.exe`

The launcher is **not** an FCC installer. It only creates convenient start/stop scripts for an existing Free Claude Code installation.

---

## 🔧 Troubleshooting

### `fcc-server.exe was not found`

Make sure the FCC virtual environment exists:

```text
free-claude-code/
└── .venv/
    └── Scripts/
        └── fcc-server.exe
```

### `fcc-claude.exe was not found`

Make sure FCC has been installed correctly and:

```text
.venv/Scripts/fcc-claude.exe
```

exists.

### Git Bash was not found

Install Git for Windows and make sure Git Bash is available.

### FCC closes immediately

Run `Start-FCC.bat` manually and check the Git Bash windows for the actual FCC error. The launcher intentionally keeps the Git Bash window open after FCC exits so errors are visible.

---

## 🧩 How It Works

The installer uses template files instead of generating complex Batch code dynamically.

```text
Start-FCC.template
        │
        ▼
Installer
        │
        ▼
Start-FCC.bat
```

and:

```text
Stop-FCC.template
        │
        ▼
Installer
        │
        ▼
Stop-FCC.bat
```

This keeps the installer simple and avoids complex Batch escaping issues.

---

## 📄 License

This launcher follows the license of the parent Free Claude Code project.