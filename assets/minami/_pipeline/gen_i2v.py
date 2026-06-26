#!/usr/bin/env python3
"""AI DISPATCH 動画ライン: i2v生成（確定引数・URL即DL・ログ保存・hermes -z非経由）。

plan_video.json の各カット motion_desc をプロンプトに、静止画を image_url で渡して
video_gen の active provider(xai, grok-imagine-video-1.5) を確定引数で呼ぶ。
返り値の video URL は短時間で失効するため即ダウンロードして保存する。
"""
import argparse, datetime, json, os, sys

HERMES_ROOT = "/home/ashviri/.hermes/hermes-agent"
if HERMES_ROOT not in sys.path:
    sys.path.insert(0, HERMES_ROOT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--cut", type=int, required=True)
    ap.add_argument("--image", required=True, help="入力静止画パス")
    ap.add_argument("--duration", type=int, required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--resolution", default="720p")
    args = ap.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    cut = next((c for c in plan["cuts"] if c["cut"] == args.cut), None)
    if cut is None:
        print(f"ERROR: cut {args.cut} not in plan", file=sys.stderr); return 2
    if not os.path.isfile(args.image):
        print(f"ERROR: still not found {args.image}", file=sys.stderr); return 2
    os.makedirs(args.outdir, exist_ok=True)

    motion = cut["motion_desc"]
    now = datetime.datetime.now(); date = now.strftime("%Y%m%d"); ts = now.strftime("%Y%m%d_%H%M%S")

    from hermes_cli.plugins import _ensure_plugins_discovered
    _ensure_plugins_discovered(force=True)
    from agent.video_gen_registry import get_active_provider
    prov = get_active_provider()
    if prov is None:
        print("ERROR: no active video provider", file=sys.stderr); return 3
    pname = getattr(prov, "name", "?")

    print(f"[gen_i2v] cut={args.cut} dur={args.duration} provider={pname} image={args.image}", file=sys.stderr)
    result = prov.generate(
        motion,
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
        out_mp4 = os.path.join(args.outdir, f"i2v_cut{args.cut}_{date}.mp4")
        try:
            if os.path.isfile(str(video_ref)):
                import shutil; shutil.copy(str(video_ref), out_mp4)
            else:
                import requests
                r = requests.get(str(video_ref), timeout=120); r.raise_for_status()
                with open(out_mp4, "wb") as fh:
                    fh.write(r.content)
        except Exception as exc:
            dl_err = str(exc); out_mp4 = None; ok = False

    logpath = os.path.join(args.outdir, f"log_i2v_cut{args.cut}_{ts}.txt")
    with open(logpath, "w", encoding="utf-8") as f:
        f.write("=== i2v gen log ===\n")
        f.write(f"timestamp: {now.isoformat()}\ncut: {args.cut}\nprovider: {pname}\nmodel: {model}\n")
        f.write(f"duration_req: {args.duration}\naspect: {args.aspect}\nresolution: {args.resolution}\n")
        f.write(f"image_in: {args.image}\nvideo_url: {video_ref}\nvideo_out: {out_mp4}\nsuccess: {ok}\n")
        if dl_err: f.write(f"download_error: {dl_err}\n")
        if not result.get("success"):
            f.write(f"error: {result.get('error')}\nerror_type: {result.get('error_type')}\n")
        f.write("\n--- MOTION PROMPT (verbatim) ---\n" + motion + "\n")
        f.write("\n--- RAW RESULT ---\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"success": ok, "cut": args.cut, "video_out": out_mp4, "model": model,
                      "duration_req": args.duration, "log": logpath}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
