#!/usr/bin/env python3
"""AI DISPATCH 漫画i2vライン: 完成4コマ漫画(1枚)→ i2vで「アニメのように滑らかに動かす」単発動画。

連結なし・1発生成。video_gen の active provider(xai, grok-imagine-video-1.5) を確定引数で直接呼ぶ
（hermes -z 非経由）。motion は焼き込みテロップ/コマ割りを保持しつつ滑らかなアニメ風微動を指示。
返り値 video URL は短時間で失効するため即DL。プロンプト全文/引数/モデル/時刻をログ保存。

実行: $HERMES/venv/bin/python gen_i2v_manga.py --image <720x1280.png> --duration 10 --outdir <dir> --tag v1
"""
import argparse, datetime, json, os, sys

HERMES_ROOT = "/home/ashviri/.hermes/hermes-agent"
if HERMES_ROOT not in sys.path:
    sys.path.insert(0, HERMES_ROOT)

# 焼き込み文字・コマ割りを保持したまま、アニメのように滑らかに動かす motion 指示（verbatim）
DEFAULT_MOTION = (
    "4コマ漫画のページ全体を、アニメのように非常に滑らかに動かす。"
    "各コマのキャラクター(藍みなみ)に、ごく自然で滑らかなアニメ風の微動を加える："
    "呼吸による胸と肩のわずかな上下、髪のやわらかいなびき、自然なまばたき、わずかな視線と表情の揺れ。"
    "動きは高フレームレートのアニメのようになめらかで、カクつきのない連続的な動き。"
    "コマ割り(パネルの枠線)・吹き出し・焼き込まれた文字(日本語テロップ、BREAKING NEWS、To be continued 等)は"
    "一切変形・再描画・移動・追加せず、元の位置・形・文字をそのまま完全に保持する。"
    "新しい文字・ロゴ・記号・透かしを描き加えない。"
    "背景はごく控えめな光のゆらめき・パーティクル程度に留め、レイアウトと全体構図は固定する。"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="入力 720x1280 4コマ漫画")
    ap.add_argument("--duration", type=int, default=10)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--tag", default="v1", help="出力識別子 (v1/v2/v3)")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--resolution", default="720p")
    ap.add_argument("--motion", default=DEFAULT_MOTION)
    args = ap.parse_args()

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

    print(f"[gen_i2v_manga] tag={args.tag} dur={args.duration} provider={pname} image={args.image}", file=sys.stderr)
    result = prov.generate(
        args.motion,
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
        f.write("=== manga i2v gen log ===\n")
        f.write(f"timestamp: {now.isoformat()}\ntag: {args.tag}\nprovider: {pname}\nmodel: {model}\n")
        f.write(f"duration_req: {args.duration}\naspect: {args.aspect}\nresolution: {args.resolution}\n")
        f.write(f"image_in: {args.image}\nvideo_url: {video_ref}\nvideo_out: {out_mp4}\nsuccess: {ok}\n")
        if dl_err: f.write(f"download_error: {dl_err}\n")
        if not result.get("success"):
            f.write(f"error: {result.get('error')}\nerror_type: {result.get('error_type')}\n")
        f.write("\n--- MOTION PROMPT (verbatim) ---\n" + args.motion + "\n")
        f.write("\n--- RAW RESULT ---\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"success": ok, "tag": args.tag, "video_out": out_mp4, "model": model,
                      "duration_req": args.duration, "log": logpath}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
