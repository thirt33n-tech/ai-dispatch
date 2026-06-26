#!/usr/bin/env python3
"""AI DISPATCH 動画ライン: カット静止画生成（確定引数・ログ保存・hermes -z非経由）。

plan_video.json の各カット(background_desc/expression)から決定的にプロンプトを組み、
XAIImageGenProvider.generate() を確定引数で直接呼ぶ。画像内に文字は描かせない
（テロップは後段でffmpeg drawtext）。プロンプト全文/引数/モデル/時刻をログ保存。

実行: $HERMES/venv/bin/python gen_still.py --plan <plan_video.json> --cut 1 --ref <ref> --outdir <dir>
"""
import argparse, datetime, json, os, shutil, sys

HERMES_ROOT = "/home/ashviri/.hermes/hermes-agent"
if HERMES_ROOT not in sys.path:
    sys.path.insert(0, HERMES_ROOT)

CHARACTER = ("藍みなみ：黒〜シルバーのグラデのウェーブロングヘア、金/琥珀色の瞳、"
             "白いリブのクロップトップ、黒のダメージデニムショート、スリム体型")

POSE_BY_CUT = {
    1: "スマートフォンを両手で持ち画面を見ている。手はフレーム端に寄せる。",
    2: "カメラへ軽く前のめりになり、熱を込めて語りかけている。",
    3: "カメラへ小さく振り向き、やわらかく微笑んで小首をかしげている。",
}


def build_still_prompt(cut: dict) -> str:
    n = cut["cut"]
    pose = POSE_BY_CUT.get(n, "自然な立ち姿。")
    return (
        f"縦9:16の1枚イラスト。主役は{CHARACTER}。\n"
        f"表情: {cut['expression']}\n"
        f"ポーズ・構図: 上半身〜胸上の安定した構図。{pose}\n"
        f"背景: {cut['background_desc']}\n"
        f"画風: フルカラー漫画、アニメ塗り、セル画風、鮮やかな配色、繊細な線画、週刊少年漫画の演出。\n"
        f"キャラの顔・髪型・髪色・瞳の色・服装・体型を参照画像と完全に一致させる（再設計・年齢/性別変更は不可）。\n"
        f"最重要: 画像内に文字・ロゴ・記号・吹き出し・透かしを一切描かない（no text, no letters, no logos, no speech bubble, no watermark）。"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--cut", type=int, required=True)
    ap.add_argument("--ref", default=os.path.expanduser("~/ai-dispatch/assets/minami/reference/minami_fullbody.png"))
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--aspect", default="9:16")
    args = ap.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    cut = next((c for c in plan["cuts"] if c["cut"] == args.cut), None)
    if cut is None:
        print(f"ERROR: cut {args.cut} not in plan", file=sys.stderr); return 2
    if not os.path.isfile(args.ref):
        print(f"ERROR: ref not found {args.ref}", file=sys.stderr); return 2
    os.makedirs(args.outdir, exist_ok=True)

    prompt = build_still_prompt(cut)
    now = datetime.datetime.now(); date = now.strftime("%Y%m%d"); ts = now.strftime("%Y%m%d_%H%M%S")

    from hermes_cli.plugins import _ensure_plugins_discovered
    _ensure_plugins_discovered(force=True)
    from agent.image_gen_registry import get_active_provider
    prov = get_active_provider()
    if prov is None:
        print("ERROR: no active image provider", file=sys.stderr); return 3
    pname = getattr(prov, "name", "?")

    print(f"[gen_still] cut={args.cut} provider={pname} ref={args.ref}", file=sys.stderr)
    result = prov.generate(prompt=prompt, aspect_ratio=args.aspect, image_url=args.ref)
    if isinstance(result, str):
        try: result = json.loads(result)
        except Exception: result = {"raw": result}

    model = result.get("model", "?"); img_src = result.get("image")
    ok = bool(result.get("success", img_src))
    out_img = None
    if ok and img_src and os.path.isfile(str(img_src)):
        ext = os.path.splitext(str(img_src))[1] or ".png"
        out_img = os.path.join(args.outdir, f"still_cut{args.cut}_{date}{ext}")
        shutil.copy(str(img_src), out_img)

    logpath = os.path.join(args.outdir, f"log_still_cut{args.cut}_{ts}.txt")
    with open(logpath, "w", encoding="utf-8") as f:
        f.write("=== still gen log ===\n")
        f.write(f"timestamp: {now.isoformat()}\ncut: {args.cut}\nprovider: {pname}\nmodel: {model}\n")
        f.write(f"aspect: {args.aspect} (注: xAI編集経路では非送信)\nref: {args.ref}\n")
        f.write(f"image_src: {img_src}\nimage_out: {out_img}\nsuccess: {ok}\n")
        if not ok:
            f.write(f"error: {result.get('error')}\nerror_type: {result.get('error_type')}\n")
        f.write("\n--- PROMPT (verbatim) ---\n" + prompt + "\n")
        f.write("\n--- RAW RESULT ---\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"success": ok, "cut": args.cut, "image_out": out_img, "model": model, "log": logpath}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
