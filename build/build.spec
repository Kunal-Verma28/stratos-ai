# Hand Gesture Control — PyInstaller Build Spec
# Run: pyinstaller build/build.spec
# Output: dist/AeroPointer.exe (standalone, no console window)

block_cipher = None

a = Analysis(
    ['../app/main.py'],
    pathex=['../'],
    binaries=[],
    datas=[
        ('../assets', 'assets'),
        ('../config', 'config'),
    ],
    hiddenimports=[
        'mediapipe',
        'cv2',
        'PySide6',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'keyboard',
        'win32api',
        'win32con',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Stratos',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No console window (GUI only)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/app_icon.ico',
)
