# 年金・収入・手取りシミュレーター

日本の年金、給与、副業・事業、家賃、投資などの収入から、所得税・住民税・社会保険料・手取りを概算する静的Webシミュレーターです。

## 公開URL

https://rttRzdf.github.io/nenkin-simulator/

## デプロイ

`main` へのpushを契機に `.github/workflows/pages.yml` がGitHub Pagesへ自動デプロイします。

公開HTMLは `site-payload/part-*` を結合・Base64デコード・gzip展開して生成します。`build-site.sh` は生成した `index.html` のSHA-256を検証し、元ファイルと1バイトでも異なる場合はデプロイを停止します。

期待SHA-256:

`44624826fadd73006a44facdc04e290334d369b0045006a8505476f4d4a1f930`

ローカルで復元する場合:

```bash
bash ./build-site.sh ./_site
```

## 注意

このシミュレーターは生活設計向けの概算です。税務申告、納付、年金請求などの確定判断には公式資料や専門家による個別確認が必要です。
