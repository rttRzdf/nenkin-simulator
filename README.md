# 年金・収入・手取りシミュレーター

日本の年金、給与、副業・事業、家賃、投資などの収入から、所得税・住民税・社会保険料・手取りを概算する静的Webシミュレーターです。

## 公開URL

https://rttRzdf.github.io/nenkin-simulator/

## デプロイ

`main` へのpushを契機に `.github/workflows/pages.yml` がGitHub Pagesへ自動デプロイします。

初回のみ、GitHubの **Settings → Pages → Build and deployment → Source** で **GitHub Actions** を選択してください。その後は `main` への更新だけで自動公開されます。

公開HTMLは圧縮した分割データを `build-site.sh` が復元し、生成した `index.html` のSHA-256を元HTMLと照合します。1バイトでも異なる場合はデプロイを停止します。

期待SHA-256:

`44624826fadd73006a44facdc04e290334d369b0045006a8505476f4d4a1f930`

ローカルで復元する場合:

```bash
bash ./build-site.sh ./_site
```

## 注意

このシミュレーターは生活設計向けの概算です。税務申告、納付、年金請求などの確定判断には公式資料や専門家による個別確認が必要です。
