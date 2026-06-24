# AI DISPATCH — デプロイ用パッケージ（単一HTML + JSON）

Vercel等にそのまま載せられる静的サイトです。`index.html` が `top-news.json` を読み込んで描画します。

## ファイル構成
```
deploy/
├── index.html        全デザイン込み（HTML+CSS+JS）。top-news.json を fetch
├── top-news.json     ★ニュースデータ（ここだけ編集すれば内容が変わる）
├── news/
│   ├── kof_manga.jpg       ヒーロー左の固定漫画
│   ├── top1_manga.png      TOP1の漫画（ヒーロー中央＋TOP1記事）
│   └── top1/poster.png     TOP1動画クリック前のサムネ
└── README.md
```

## デプロイ手順（Vercel）
1. この `deploy/` フォルダの中身をリポジトリのルート（または公開ディレクトリ）に置く
2. Vercelにインポート（フレームワークプリセット: **Other / 静的サイト**でOK。ビルドコマンド不要）
3. 公開。`index.html` がそのまま表示されます

> ローカル確認は、`deploy/` 内で簡易サーバを立てて開いてください（`fetch` はファイル直開き `file://` では動かないため）。
> 例: `npx serve deploy` または `python -m http.server`（deploy内で実行）

## ニュースの差し替え（top-news.json）
このファイルだけ書き換えて再デプロイ（git push）すれば更新完了です。

| キー | 内容 |
|---|---|
| `fixedMangaUrl` | ヒーロー左の固定漫画パス（ニュースと独立） |
| `heroVideoUrl` | ヒーロー右のアニメ動画URL（YouTube/Shorts/Vimeo 通常URLでOK） |
| `breakingNews` | 速報ティッカーの配列（行を足し引き。ループ複製は自動） |
| `news[]` | TOP1〜3の記事配列 |

### news[] の各フィールド
| フィールド | 内容 |
|---|---|
| `rank` | 順位（バッジ "TOP n"） |
| `category` | カテゴリ（任意・データ保持） |
| `time` | 日時テキスト |
| `title` | 見出し |
| `summary` | 要約 |
| `source_url` | 出典URL（任意） |
| `manga_url` | 漫画画像パス。空文字 `""` なら非表示 |
| `video_url` | 動画URL。空文字 `""` なら「▶ 動画を見る」非表示 |
| `poster_url` | （TOP1のみ）動画サムネ |

### 動画URLについて
- 通常URLをそのまま貼ればOK：`youtube.com/watch?v=…` / `youtu.be/…` / `youtube.com/shorts/…` / `vimeo.com/…`
- JS（`toEmbed`）が自動で埋め込みURLへ変換
- **クリックされるまでiframeを読み込まない**（パフォーマンス対策）
- Shorts（縦型）はモーダル/フレームを自動で9:16表示
- mp4等の直リンクは `<video>` で再生

### 画像の差し替え
`news/` に画像を置き、`top-news.json` のパスを合わせる（または同名で上書き）。

## 将来の自動更新（参考）
`top-news.json` を外部に分離してあるので、将来 HermesAgent / Claude などで
「RSS取得 → 要約 → top-news.json を上書き → git push」を定期実行すれば、
**ページ本体（index.html）を一切変更せず**ニュースだけ自動更新できます。
