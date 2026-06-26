#!/usr/bin/env python3
"""AI DISPATCH 動画ライン 案A: ズーム完全禁止版（no-zoom / noom）。

判明した崩れ原因＝i2vがコマ3にズームインしズーム時に日本語テキストを崩す
（俯瞰=崩れゼロ、ズーム後=崩壊）。本版は「ズームイン/アウト・パン・カメラ移動・寄り・
回り込み一切禁止／4コマ全体の俯瞰ショットを10秒間 同じ大きさ・同じ位置で固定維持」を
冒頭と末尾で反復強調する。動かすのは各コマ内の表情・口パク・髪・瞳・効果のみ。
文脈＋セリフ＋音声指示（道B）はそのまま維持＝発話音声を保つ。

既存 gen_i2v_manga_ctx.py / _fixed.py は温存。本版は動き記述のみ最強化した変種。
確定引数・URL即DL・プロンプト全文/引数/モデル/時刻をログ保存（hermes -z 非経由）。

実行: $HERMES/venv/bin/python gen_i2v_manga_ctx_noom.py --image <マスク済み720x1280.png> --outdir <dir> --tag noom_prod
"""
import argparse, datetime, json, os, sys

HERMES_ROOT = "/home/ashviri/.hermes/hermes-agent"
if HERMES_ROOT not in sys.path:
    sys.path.insert(0, HERMES_ROOT)

# --- 固定の構造値（毎日不変・コード保持）。当日の news/セリフ は --script-json で外部供給 ---
# CLI化前は NEWS/CHARACTER/PANELS をここに直書きしていた（当日値混入で再現不能だった）。
# news と各コマ speech は script-json から供給。CHARACTER と各コマの「役割」描写は毎日不変の
# 構造値なのでデフォルトとしてコード保持する（--character-json で上書き可）。
# 未指定時デフォルトが旧直書きと一致するため、旧 news/panels を渡せば旧出力と完全一致する。
DEFAULT_CHARACTER = "藍みなみ（黒〜シルバーのウェーブロングヘア、金/琥珀色の瞳、明るい女性の声）"
DEFAULT_ROLES = [
    "驚き（スマホで速報を見る）",
    "強い驚き・叫び（顔のアップ）",
    "ナレーション・状況解説",
    "考察・オチ",
]


def load_character(character_json=None) -> str:
    """CHARACTER文字列を返す。未指定なら DEFAULT_CHARACTER（回帰時はこれで旧出力と一致）。

    config/character_minami.json 等を渡した場合は name＋appearance＋声特徴から組み立てる。
    """
    if not character_json:
        return DEFAULT_CHARACTER
    with open(character_json, encoding="utf-8") as f:
        c = json.load(f)
    name = c.get("name", "主人公")
    appearance = (c.get("appearance") or "").strip()
    return f"{name}（{appearance}、明るい女性の声）" if appearance else name


def build_ctx_prompt(news, panels, character=None) -> str:
    character = character or DEFAULT_CHARACTER
    serif_lines = "\n".join(
        f"コマ{i + 1}（{p.get('role') or (DEFAULT_ROLES[i] if i < len(DEFAULT_ROLES) else '')}）: 「{(p.get('speech') or '').strip()}」"
        for i, p in enumerate(panels)
    )
    NEWS = news
    CHARACTER = character
    return (
        "この縦長4コマ漫画ニュースを、日本のテレビアニメのように動かして。AIニュースの解説リアクション漫画です。\n"
        # --- 冒頭の俯瞰固定強調（最重要） ---
        "【最重要・カメラ固定】ズームイン・ズームアウト・パン・ティルト・カメラ移動・寄り・回り込み・ドリーは一切禁止。"
        "4コマ全体の俯瞰ショット（4コマすべてが常に画面内に見える構図）を、10秒間ずっと同じ大きさ・同じ位置で固定して維持する。"
        "特定のコマに寄ったり拡大したりは絶対にしない。\n"
        f"ニュース: {NEWS}\n"
        f"主人公: {CHARACTER}。彼女が各コマで下記のセリフを日本語の声で実際に喋る。\n\n"
        "各コマのセリフ（上から下へ順に、キャラがこの声で話す）:\n"
        f"{serif_lines}\n\n"
        # --- 動き（ズーム完全禁止・最強版） ---
        "動き: カメラワークは完全禁止。ズームイン・ズームアウト・パン・ティルト・カメラ移動・寄り・回り込み・ドリーを一切してはいけない。"
        "4コマのページ全体を、最初のフレームから最後のフレームまで、画面いっぱいに同じ大きさ・同じ位置で固定表示し続ける。"
        "特定のコマに寄る・拡大することは絶対に禁止。俯瞰の全体ショットを10秒間ずっと維持する。"
        "動かしてよいのは各コマ内の表情・口パク・髪・瞳・効果のみ（その場で小さく微動）。"
        "ページ全体の位置・大きさ・構図は1ミリも動かさない。口はセリフに合わせてリップシンクする。背景エフェクトはごく控えめに動く。"
        "コマ割り(枠線)・吹き出し・焼き込まれた文字(日本語テロップ、BREAKING NEWS、To be continued)は"
        "変形・再描画・移動・追加せず、原位置のまま完全に保持する。新しい文字を描き加えない。\n"
        "音声（最重要）: 藍みなみが上記のセリフを明るい女性の声で日本語ではっきり喋る。"
        "コマ1で『ハッ』という驚きの効果音、全体に軽快なニュース速報感のBGMを付ける。\n"
        "スタイル: 日本のテレビアニメ調、セル画、なめらかな中割り、高フレームレート。\n"
        # --- 末尾の俯瞰固定強調（反復） ---
        "【再度厳守】カメラは絶対に動かさない。ズーム・パン・寄りなし。4コマ全体の俯瞰ショットを同じ構図のまま10秒間維持し続けること。"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="入力 720x1280 4コマ漫画（コマ3マスク済み）")
    ap.add_argument("--duration", type=int, default=10)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--tag", default="noom_prod")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--resolution", default="720p")
    ap.add_argument("--script-json", dest="script_json", required=True,
                    help="当日script.json（news/panels）。CLI化により当日値はここから供給（旧ハードコード撤去）")
    ap.add_argument("--character-json", dest="character_json", default=None,
                    help="キャラ設定json（config/character_minami.json等）。未指定はDEFAULT_CHARACTER")
    ap.add_argument("--print-prompt", action="store_true", help="プロンプトを表示して終了（生成しない）")
    args = ap.parse_args()

    if not os.path.isfile(args.script_json):
        print(f"ERROR: script-json not found {args.script_json}", file=sys.stderr); return 2
    with open(args.script_json, encoding="utf-8") as f:
        script = json.load(f)
    news = script.get("news")
    panels = script.get("panels", [])
    if not news or not panels:
        print("ERROR: script-json は news と panels を含む必要があります", file=sys.stderr); return 2
    character = load_character(args.character_json)

    prompt = build_ctx_prompt(news, panels, character)
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

    print(f"[gen_i2v_manga_ctx_noom] tag={args.tag} dur={args.duration} provider={pname} image={args.image}", file=sys.stderr)
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
        f.write("=== manga i2v (context/道B・ズーム完全禁止版) gen log ===\n")
        f.write(f"timestamp: {now.isoformat()}\ntag: {args.tag}\nprovider: {pname}\nmodel: {model}\n")
        f.write(f"duration_req: {args.duration}\naspect: {args.aspect}\nresolution: {args.resolution}\n")
        f.write(f"script_json: {args.script_json}\ncharacter_json: {args.character_json}\n")
        f.write(f"image_in: {args.image}\nvideo_url: {video_ref}\nvideo_out: {out_mp4}\nsuccess: {ok}\n")
        if dl_err: f.write(f"download_error: {dl_err}\n")
        if not result.get("success"):
            f.write(f"error: {result.get('error')}\nerror_type: {result.get('error_type')}\n")
        f.write("\n--- CONTEXT PROMPT (verbatim, no-zoom) ---\n" + prompt + "\n")
        f.write("\n--- RAW RESULT ---\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"success": ok, "tag": args.tag, "video_out": out_mp4, "model": model,
                      "duration_req": args.duration, "log": logpath}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
