#!/usr/bin/env python3
"""AI DISPATCH 動画ライン 道B: 完成4コマ漫画(1枚)＋文脈プロンプトをi2vに渡し音声再現を検証。

仮説: video_gen(xai) は payload に prompt を送る（実装確認済み・audio/modeフラグは無効）。
画像のみだと環境音しか出ないが、prompt にニュース文脈＋各コマのセリフ＋音声指示を埋めれば、
手動(grok.com)の「文脈保持つき動画化」に近い発話/効果音が出る可能性を検証する。

既存 gen_i2v_manga.py は温存。本スクリプトは prompt を文脈リッチ版に差し替えただけ。
確定引数・URL即DL・プロンプト全文/引数/モデル/時刻をログ保存（hermes -z 非経由）。

実行: $HERMES/venv/bin/python gen_i2v_manga_ctx.py --image <720x1280.png> --outdir <dir> --tag ctx_test
"""
import argparse, datetime, json, os, sys

HERMES_ROOT = "/home/ashviri/.hermes/hermes-agent"
if HERMES_ROOT not in sys.path:
    sys.path.insert(0, HERMES_ROOT)

# --- 当日データ（today-news.json TOP1 ＋ 完成漫画の吹き出し正本） ---
NEWS = "OpenAIがBroadcomと共同で初の自社向けカスタムAIチップ「Jalapeno」を発表。計算コストと供給難の解決を狙う、AIインフラの新時代。"
CHARACTER = "藍みなみ（黒〜シルバーのウェーブロングヘア、金/琥珀色の瞳、明るい女性の声）"
PANELS = [
    ("1", "驚き（スマホで速報を見る）", "えっ…!?"),
    ("2", "強い驚き・叫び（顔のアップ）", "まじで!?"),
    ("3", "ナレーション・状況解説", "計算コストと供給難に頭を抱えていた業界。OpenAIとBroadcomが新チップ『Jalapeno』で解決を狙う！"),
    ("4", "考察・オチ", "ふむ…供給網の再編か、来週はどう動く？"),
]


def build_ctx_prompt() -> str:
    serif_lines = "\n".join(
        f"コマ{n}（{role}）: 「{line}」" for n, role, line in PANELS
    )
    return (
        "この縦長4コマ漫画ニュースを、日本のテレビアニメのように滑らかに動かして。"
        "AIニュースの解説リアクション漫画です。\n"
        f"ニュース: {NEWS}\n"
        f"主人公: {CHARACTER}。彼女が各コマで下記のセリフを日本語の声で実際に喋る。\n\n"
        "各コマのセリフ（上から下へ順に、キャラがこの声で話す）:\n"
        f"{serif_lines}\n\n"
        "動き: 4コマのページ全体を保ったまま、各コマで表情・口パク・髪・瞳が滑らかに動く。"
        "口はセリフに合わせてリップシンクする。軽いカメラのダリーイン、背景エフェクトが少し動く。"
        "コマ割り(枠線)・吹き出し・焼き込まれた文字(日本語テロップ、BREAKING NEWS、To be continued)は"
        "変形・再描画・移動・追加せず、原位置のまま完全に保持する。新しい文字を描き加えない。\n"
        "音声（最重要）: 藍みなみが上記のセリフを明るい女性の声で日本語ではっきり喋る。"
        "コマ1で『ハッ』という驚きの効果音、全体に軽快なニュース速報感のBGMを付ける。\n"
        "スタイル: 日本のテレビアニメ調、セル画、なめらかな中割り、高フレームレート。"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="入力 720x1280 4コマ漫画")
    ap.add_argument("--duration", type=int, default=10)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--tag", default="ctx_test")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--resolution", default="720p")
    ap.add_argument("--print-prompt", action="store_true", help="プロンプトを表示して終了（生成しない）")
    args = ap.parse_args()

    prompt = build_ctx_prompt()
    if args.print_prompt:
        print(prompt)
        return 0

    if not os.path.isfile(args.image):
        print(f"ERROR: image not found {args.image}", file=sys.stderr); return 2
    os.makedirs(args.outdir, exist_ok=True)
    now = datetime.datetime.now(); date = now.strftime("%Y%m%d"); ts = now.strftime("%Y%m%d_%H%M%S")

    from hermes_cli.plugins import _ensure_plugins_discovered
    _ensure_plugins_discovered(force=True)
    from agent.video_gen_registry import get_active_provider
    prov = get_active_provider()
    if prov is None:
        print("ERROR: no active video provider", file=sys.stderr); return 3
    pname = getattr(prov, "name", "?")

    print(f"[gen_i2v_manga_ctx] tag={args.tag} dur={args.duration} provider={pname} image={args.image}", file=sys.stderr)
    result = prov.generate(
        prompt,
        image_url=args.image,
        duration=args.duration,
        aspect_ratio=args.aspect,
        resolution=args.resolution,
    )
    if isinstance(result, str):
        try: result = json.loads(result)
        except Exception: result = {"raw": result}

    ok = bool(result.get("success"))
    video_ref = result.get("video")
    model = result.get("model", "?")
    out_mp4 = None
    dl_err = None
    if ok and video_ref:
        out_mp4 = os.path.join(args.outdir, f"manga_i2v_{args.tag}_{date}.mp4")
        try:
            if os.path.isfile(str(video_ref)):
                import shutil; shutil.copy(str(video_ref), out_mp4)
            else:
                import requests
                r = requests.get(str(video_ref), timeout=180); r.raise_for_status()
                with open(out_mp4, "wb") as fh:
                    fh.write(r.content)
        except Exception as exc:
            dl_err = str(exc); out_mp4 = None; ok = False

    logpath = os.path.join(args.outdir, f"log_manga_i2v_{args.tag}_{ts}.txt")
    with open(logpath, "w", encoding="utf-8") as f:
        f.write("=== manga i2v (context/道B) gen log ===\n")
        f.write(f"timestamp: {now.isoformat()}\ntag: {args.tag}\nprovider: {pname}\nmodel: {model}\n")
        f.write(f"duration_req: {args.duration}\naspect: {args.aspect}\nresolution: {args.resolution}\n")
        f.write(f"image_in: {args.image}\nvideo_url: {video_ref}\nvideo_out: {out_mp4}\nsuccess: {ok}\n")
        if dl_err: f.write(f"download_error: {dl_err}\n")
        if not result.get("success"):
            f.write(f"error: {result.get('error')}\nerror_type: {result.get('error_type')}\n")
        f.write("\n--- CONTEXT PROMPT (verbatim) ---\n" + prompt + "\n")
        f.write("\n--- RAW RESULT ---\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"success": ok, "tag": args.tag, "video_out": out_mp4, "model": model,
                      "duration_req": args.duration, "log": logpath}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
