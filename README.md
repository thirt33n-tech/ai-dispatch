# AI DISPATCH — デプロイ用パッケージ（v2 / 単一HTML + JSON）

「地下AI通信社」デザイン（v2）の静的サイトです。`index.html` が `top-news.json` を読み込んで描画します。Vercel等にそのまま載せられます。

## ファイル構成
```
deploy/
├── index.html        全デザイン込み（HTML+CSS+JS）。top-news.json を fetch
├── top-news.json     ★毎日ここだけ編集すれば内容が変わる
├── ogp/147.png       OGP（SNSシェア画像。差し替えたら og:image のパスも合わせる）
├── news/             漫画・サムネ画像
└── README.md
```

## デプロイ手順（Vercel + GitHub）
1. `deploy/` の中身をリポジトリ（https://github.com/thirt33n-tech）のルートに置く
2. Vercelでインポート（フレームワーク: **Other / 静的サイト**、ビルドコマンド不要）
3. 公開。以後は **git push するだけで自動デプロイ**

> ローカル確認は簡易サーバ経由で（`fetch` は `file://` 直開きでは動きません）。
> 例: `npx serve deploy` または deploy内で `python -m http.server`

## 毎朝の更新（top-news.json だけ編集）
| キー | 内容 |
|---|---|
| `dispatchNo` | 日刊ナンバー（毎朝 +1） |
| `dateLabel` | 日付（例 2026.06.25） |
| `githubUrl` | フッターのGitHubリンク |
| `top1` | 本日のリード（title/lead1/lead2/manga_url/video_url） |
| `heroVideoUrl` | おまけアニメの動画URL |
| `editorsDesk` | 編集部おすすめ＋おまけアニメ |
| `breaking` | 速報ティッカー（TOP4-10。配列） |
| `topCards` | TOP2-3カード |
| `topList` | TOP4-10リスト |
| `archive` | 漫画アーカイブ（過去ディスパッチ） |

### 動画URL
通常URLをそのまま貼ればOK（`youtube.com/watch` / `youtu.be` / `youtube.com/shorts` / `vimeo.com`）。
JSが自動でembed変換。Shorts（縦型）はモーダルを9:16表示。アニメ・動画はクリックで読み込み（事前ロードしない）。

### 画像
`news/` に置いて、各 `*_url` / `img` のパスを合わせる（または同名で上書き）。
漫画サムネ・編集部おすすめ・アーカイブはクリックで拡大ポップアップ表示。

## アーカイブの運用（前日分の追加）
毎朝、`archive` 配列の**先頭に当日のTOP1を1件追加**します：
```json
{ "no": 148, "kind": "📖 漫画", "date": "06.25", "img": "news/0625_manga.png" }
```
古い項目は下に残るので、過去ディスパッチが自然に積み上がります。

## OGP画像
`ogp/147.png`（1200×630）。新しい日のものに差し替えたら、`index.html` の
`<meta property="og:image" content="ogp/147.png">` のパスも合わせてください。

## 将来の自動更新
`top-news.json` を分離してあるので、HermesAgent / Claude などで
「ニュース取得 → 要約 → 当日のTOP1作成 → 前日分をarchiveへ追加 → JSON更新 → git push」
を定期実行すれば、`index.html` を一切触らずニュースだけ自動更新できます。
