import time
import traceback
import sys

def log(msg, level="INFO"):
    """
    CMDにログを出力する (flush=Trueで即時表示)
    """
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}", flush=True)

def error(e, msg="An error occurred"):
    """
    エラー詳細とスタックトレースを出力する
    """
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [ERROR] {msg}: {str(e)}", flush=True)
    print("--- Error Traceback ---", flush=True)
    traceback.print_exc() 
    print("-----------------------", flush=True)