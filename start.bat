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
if exist ".venv\Scripts\python.exe" goto MENU

cls
echo ========================================================
echo  初回セットアップを実行します
echo ========================================================
echo.
echo  必要なファイルを準備しています...
python -m venv .venv

:: --- 修正箇所: libsフォルダからインストールする ---
echo  ライブラリをインストール中...
.venv\Scripts\python.exe -m pip install --no-index --find-links=libs -r requirements.txt

echo.
echo  準備が完了しました。
timeout /t 3 >nul

:: --- 3. メインメニュー ---
:MENU
cls
echo ========================================================
echo  ドローン国家資格 学科試験システム
echo ========================================================
if exist "count_status.py" .venv\Scripts\python.exe count_status.py
echo.
echo  [1] 問題を作成する (Generator)
echo      ※ Google Gemini APIキーが必要です
echo.
echo  [2] 試験を始める (App)
echo      ストックされた問題を使って模擬試験を行います。
echo.
echo  [3] データベースをチェックする (ID付与・修復)
echo.
echo  --- メンテナンス ---
echo  [4] レビュー用CSVを出力 (Export)
echo  [5] CSVから修正を取り込み (Import)
echo  [6] APIクオータ・健康診断 (Check Quota)
echo.
echo  [H] APIキーの設定方法 (Help)
echo.
echo  [9] 終了
echo.
echo ========================================================

set /p num="番号を入力してください > "

if /i "%num%"=="1" goto CHECK_KEY
if /i "%num%"=="2" goto APP
if /i "%num%"=="3" goto CHECK
if /i "%num%"=="4" goto EXPORT
if /i "%num%"=="5" goto IMPORT
if /i "%num%"=="6" goto QUOTA
if /i "%num%"=="H" goto HELP
if /i "%num%"=="9" exit
goto MENU

:: --- 各機能へのジャンプ ---
:CHECK_KEY
if exist "apikey.txt" (
    goto GENERATOR
) else (
    goto NO_KEY_ERROR
)

:GENERATOR
cls
echo.
echo 問題作成ツールを起動します...
echo --------------------------------------------------------
if not exist "rules.pdf" (
    echo 警告: rules.pdf が見つかりません。
    echo 教則PDFをこのフォルダに配置してから実行してください。
    pause
    goto MENU
)
.venv\Scripts\python.exe generator.py
pause
goto MENU

:APP
cls
echo.
echo 試験アプリを起動します...
echo --------------------------------------------------------
echo 起動中... (ブラウザが開きます)
echo.
echo ※終了する時は、この黒い画面を閉じるか Ctrl+C を押してください。
.venv\Scripts\python.exe -m streamlit run app.py --browser.gatherUsageStats false
goto MENU

:CHECK
cls
echo.
echo データベース診断ツールを起動します...
echo --------------------------------------------------------
.venv\Scripts\python.exe check_db.py
pause
goto MENU

:EXPORT
cls
echo.
echo CSV出力ツールを起動します...
echo --------------------------------------------------------
.venv\Scripts\python.exe export_review.py
pause
goto MENU

:IMPORT
cls
echo.
echo CSV取込ツールを起動します...
echo --------------------------------------------------------
.venv\Scripts\python.exe import_review.py
pause
goto MENU

:QUOTA
cls
echo.
echo API健康診断ツールを起動します...
echo --------------------------------------------------------
.venv\Scripts\python.exe check_quota.py
pause
goto MENU

:: --- ヘルプ画面 ---
:NO_KEY_ERROR
cls
echo.
echo ========================================================
echo  APIキーが見つかりません
echo ========================================================
echo.
echo  問題を作成するには「Google Gemini APIキー」が必要です。
echo  以下の手順に従って設定してください。
echo.
goto SHOW_INSTRUCTIONS

:HELP
cls
echo ========================================================
echo  APIキーの設定ガイド
echo ========================================================
echo.
:SHOW_INSTRUCTIONS
echo  【1. APIキーとは？】
echo     AIを利用するためのパスワードのようなものです。
echo     Googleアカウントがあれば無料で取得できます。
echo.
echo  【2. 取得方法】
echo     以下のURLから「Create API key」を押して取得してください。
echo     URL: https://aistudio.google.com/app/apikey
echo.
echo  【3. 設置方法】
echo     1. このフォルダに新しいテキストファイルを作ります。
echo     2. 名前を「apikey.txt」に変更します。
echo     3. その中に、取得したキー（AIzaSy...）を貼り付けて保存します。
echo.
echo  --------------------------------------------------------
echo  準備ができたら、もう一度 [1] を選択してください。
echo.
pause
goto MENU