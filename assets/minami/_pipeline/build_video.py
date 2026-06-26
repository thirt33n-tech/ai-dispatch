#!/usr/bin/env python3
"""AI DISPATCH 動画ライン タスク4+5: 日本語テロップ焼き込み → 連結。

各i2vカットに plan_video.json の telop_ja を ffmpeg drawtext で焼き（半透明帯＋白文字＋縁取り、
Noto Sans CJK JP、自動フォントサイズ＋折り返し）、3カットを concat で連結（映像/音声=ネイティブ音声そのまま, 方針あ）。
mjpegカバーストリームは map で除外。system ffmpeg(/usr/bin/ffmpeg)使用。
"""
import argparse, json, os, subprocess, sys, tempfile
from PIL import ImageFont

FONT = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"
FFMPEG = "/usr/bin/ffmpeg"
W = 720


def wrap_and_size(text, max_w=620, max_px=46, min_px=26):
    """日本語テロップを1〜2行に折り返し、収まる最大フォントサイズを返す。"""
    def lines_at(px, lines):
        f = ImageFont.truetype(FONT, px)
        return max(f.getlength(l) for l in lines)
    # まず1行で入るか
    for px in range(max_px, min_px - 1, -1):
        f = ImageFont.truetype(FONT, px)
        if f.getlength(text) <= max_w:
            return [text], px
    # 2行に分割（読点優先、なければ中央）
    split = None
    if "、" in text:
        idx = text.index("、") + 1
        # 中央に最も近い読点を選ぶ
        best = None
        for i, ch in enumerate(text):
            if ch == "、":
                if best is None or abs((i + 1) - len(text) / 2) < abs(best - len(text) / 2):
                    best = i + 1
        split = best
    if split is None:
        split = len(text) // 2
    lines = [text[:split], text[split:]]
    for px in range(max_px, min_px - 1, -1):
        if lines_at(px, lines) <= max_w:
            return lines, px
    return lines, min_px


def telop_cut(infile, telop, outfile):
    lines, px = wrap_and_size(telop)
    tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    tf.write("\n".join(lines)); tf.close()
    # 下部中央、半透明帯(box)＋白文字＋黒縁。複数行は line_spacing。
    draw = (
        f"drawtext=fontfile={FONT}:textfile={tf.name}:"
        f"fontcolor=white:fontsize={px}:line_spacing=12:"
        f"borderw=3:bordercolor=black@0.9:"
        f"box=1:boxcolor=black@0.5:boxborderw=22:"
        f"x=(w-text_w)/2:y=h-text_h-72"
    )
    cmd = [FFMPEG, "-y", "-i", infile,
           "-map", "0:v:0", "-map", "0:a:0",
           "-vf", draw,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k",
           outfile]
    r = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(tf.name)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1500:])
        raise RuntimeError(f"drawtext failed for {infile}")
    return {"lines": lines, "fontsize": px}


def concat(files, outfile):
    inputs = []
    for f in files:
        inputs += ["-i", f]
    n = len(files)
    streams = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n))
    fc = f"{streams}concat=n={n}:v=1:a=1[v][a]"
    cmd = [FFMPEG, "-y", *inputs, "-filter_complex", fc,
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", outfile]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1500:])
        raise RuntimeError("concat failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--i2vdir", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    os.makedirs(args.workdir, exist_ok=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    telop_files, report = [], []
    for cut in sorted(plan["cuts"], key=lambda c: c["cut"]):
        n = cut["cut"]
        infile = os.path.join(args.i2vdir, f"i2v_cut{n}_{args.date}.mp4")
        if not os.path.isfile(infile):
            print(f"ERROR: missing {infile}", file=sys.stderr); return 2
        outfile = os.path.join(args.workdir, f"telop_cut{n}_{args.date}.mp4")
        meta = telop_cut(infile, cut["telop_ja"], outfile)
        telop_files.append(outfile)
        report.append({"cut": n, "telop": cut["telop_ja"], **meta})
        print(f"[telop] cut{n}: {meta['lines']} size={meta['fontsize']}", file=sys.stderr)

    concat(telop_files, args.out)
    print(json.dumps({"success": True, "out": args.out, "telop": report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
