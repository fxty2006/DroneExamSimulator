@echo off
cd /d %~dp0
title ドローン試験システム

:: --- 1. Pythonインストールチェック ---
python --version >nul 2>&1
if %errorlevel% equ 0 goto VENV_CHECK

:: --- Pythonが見つからない場合の処理 ---
cls
echo ========================================================
echo  Pythonが見つかりませんでした
echo ========================================================
echo.
echo  このアプリを実行するには Python (3.10以上) が必要です。
echo  今すぐインストールしますか？
echo  ※ 「y」を押すとインストーラーが起動します
echo.
set /p install_choice="インストールしますか？ (y/n) > "

if /i "%install_choice%"=="y" goto INSTALL_PYTHON
echo.
echo  インストールをキャンセルしました。
echo  アプリを実行できません。終了します。
timeout /t 5
exit

:INSTALL_PYTHON
echo.
echo  インストーラーを起動しています...
echo  ※ インストール中に「変更を許可しますか？」と聞かれたら「はい」を押してください。
        
:: Wingetを使ってPython 3.12をインストール
winget install -e --id Python.Python.3.12

:: --- Winget失敗時の救済措置 ---
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo  [!] 自動インストールに失敗しました。
    echo  ブラウザを開いてPython公式サイトを表示します。
    echo  手動で「Download Python 3.12」ボタンを押して
    echo  インストールを行ってください。
    echo  ※ インストール時、「Add Python to PATH」にチェックを入れてください！
    echo ========================================================
    timeout /t 5
    start https://www.python.org/downloads/
    pause
    exit
)
        
echo.
echo ========================================================
echo  インストール処理が終了しました。
echo  設定を反映させるため、この画面を一度閉じて、
echo  もう一度 start.bat を起動してください。
echo ========================================================
pause
exit

:: --- 2. 初期セットアップ確認 ---
:VENV_CHECK
if exist ".venv\Scripts\python.exe" goto LAUNCH

cls
echo ========================================================
echo  初回セットアップを実行します
echo ========================================================
echo.
echo  必要なファイルを準備しています...
python -m venv .venv

:: --- ライブラリのインストール (自動修復機能付き) ---
if exist "libs" (
    echo  [オフラインモード] libsフォルダからインストールを試みます...
    .venv\Scripts\python.exe -m pip install --no-index --find-links=libs -r requirements.txt
    
    :: エラー判定: もしlibsからのインストールに失敗したら
    if errorlevel 1 (
        echo.
        echo  [!] libsフォルダのファイルが不足しているか、バージョンが合いません。
        echo  [WEB] [オンラインモード] に切り替えてインターネットからダウンロードします...
        .venv\Scripts\python.exe -m pip install -r requirements.txt
    )
) else (
    echo  [WEB] [オンラインモード] インターネットからダウンロードします...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo.
echo  準備が完了しました。
timeout /t 3 >nul

:: --- 3. アプリ起動 ---
:LAUNCH
cls
echo ========================================================
echo  ドローン国家資格 学科試験システム v0.2.1
echo ========================================================
echo.
echo  ブラウザを起動しています...
echo  終了する時はブラウザを閉じて、この画面も閉じてください。
echo.
.venv\Scripts\python.exe -m streamlit run main_ui.py