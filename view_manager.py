import streamlit as st
import pandas as pd
import glob
import os
import json
import time
import check_db
import export_review
import import_review

def render(locked):
    st.header("📊 データ管理")
    
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "data")
    report_path = os.path.join(data_dir, "csv_review", "reported.csv")
    
    # ------------------------------------------------
    # 1. ユーザー報告セクション (内容の不備)
    # ------------------------------------------------
    st.subheader("📢 ユーザーからの報告 (内容の不備)")
    st.caption("模擬試験（練習モード）中にユーザーから報告された問題の一覧です。CSVエクスポートを行って内容を修正することをお勧めします。")
    
    # ファイルの有無を確認
    if os.path.exists(report_path):
        # 読み込み処理と表示
        try:
            df_report = pd.read_csv(report_path)
            if not df_report.empty:
                st.error(f"⚠️ **{len(df_report)} 件の報告があります**")
                st.dataframe(df_report, use_container_width=True)
                
                # 履歴クリアボタン
                if st.button("🗑️ 報告履歴を全て消去", type="secondary"):
                    os.remove(report_path)
                    st.success("履歴を消去しました。画面を更新します...")
                    time.sleep(1)
                    st.rerun()
            else:
                st.info("✅ 現在、報告された問題はありません。")
        except Exception as e:
            # st.rerun() による中断はここでキャッチしないように注意が必要だが
            # Streamlitの仕様上、rerunは例外を投げるため、意図しないエラー表示を防ぐ
            if "scriptrunner.script_runner.StopException" not in str(type(e)):
                st.warning(f"ファイルの読み込み中にエラーが発生しました: {e}")
    else:
        st.info("✅ 現在、報告された問題はありません。")

    st.divider()

    # ------------------------------------------------
    # 2. データ整合性エラーセクション (システム的な不備)
    # ------------------------------------------------
    st.subheader("⚠️ データ整合性チェック (システムの不備)")
    st.caption("ファイルの破損や必須項目の欠落など、システム的な不備を診断した結果です。")

    # ファイル数の集計
    files = glob.glob(os.path.join(data_dir, "db_*.json"))
    files = [f for f in files if "db_status.json" not in f]
    total_q_count = 0
    for f in files:
        try:
            with open(f,'r',encoding='utf-8') as fp: total_q_count += len(json.load(fp))
        except: pass
    
    m1, m2, m3 = st.columns(3)
    m1.metric("📁 総ファイル数", f"{len(files)} ファイル")
    m2.metric("📝 総問題数", f"{total_q_count} 問")

    msg = st.session_state.maintenance_msg
    if msg:
        if msg['type'] == 'success': st.success(msg['content'])
        elif msg['type'] == 'warning': st.warning(msg['content'])

    if st.session_state.db_errors:
        st.error(f"⚠️ **{len(st.session_state.db_errors)} 件のデータ不備があります**")
        df_err = pd.DataFrame(st.session_state.db_errors)
        st.dataframe(df_err, use_container_width=True)
    else:
        st.success("✅ データ構造に問題はありません。")
        
    st.markdown("---")
    
    # ------------------------------------------------
    # 3. ツールセクション
    # ------------------------------------------------
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🛠️ 診断・修復")
        st.caption("データの整合性をチェックします。")
        if st.button("診断を実行 (Check)", disabled=locked):
            logs, count, errors = check_db.check_and_clean(silent=True)
            st.session_state.db_errors = errors
            if errors:
                txt = f"⚠️ **診断完了**: {len(errors)}件の不備が見つかりました。"
                st.session_state.maintenance_msg = {'type': 'warning', 'content': txt}
            else:
                txt = f"✅ **診断完了**: 異常はありません。\n(※ {count}件の自動修復を行いました)"
                st.session_state.maintenance_msg = {'type': 'success', 'content': txt}
            st.rerun()

    with c2:
        st.subheader("📤 CSVエクスポート")
        st.caption("編集用に全データを出力します。")
        if st.button("出力を実行 (Export)", disabled=locked):
            fc, qc, path = export_review.run_export()
            if fc > 0:
                txt = f"✅ **完了**: {fc}ファイル ({qc}問)\n保存先: {path}"
                st.session_state.maintenance_msg = {'type': 'success', 'content': txt}
            else:
                st.session_state.maintenance_msg = {'type': 'warning', 'content': "⚠️ データがありません。"}
            st.rerun()

    with c3:
        st.subheader("📥 CSVインポート")
        st.caption("編集後のCSVを取り込みます。")
        if st.button("取込を実行 (Import)", disabled=locked):
            fc, uc = import_review.run_import()
            if fc > 0:
                logs, count, errors = check_db.check_and_clean(silent=True)
                st.session_state.db_errors = errors
                if not errors:
                    txt = f"✅ **完了**: {uc}件更新。不備は解消されました！"
                    st.session_state.maintenance_msg = {'type': 'success', 'content': txt}
                else:
                    txt = f"⚠️ **完了**: {uc}件更新しましたが、{len(errors)}件の不備があります。"
                    st.session_state.maintenance_msg = {'type': 'warning', 'content': txt}
            else:
                st.session_state.maintenance_msg = {'type': 'warning', 'content': "⚠️ CSVが見つかりません。"}
            st.rerun()