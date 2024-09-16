
## WikiDiffReporter
指定したWikipediaの記事のURLとユーザー名に基づいて、そのユーザーがその記事に対して行った編集内容を取得し、差分をHTML形式で出力するスクリプトです。

## ダウンロード
```
git clone git@github.com:remokasu/WikiDiffReporter.git
```

## Pythonバージョン
Python3.10以上

## 依存ライブラリのインストール
```
pip install requests jinja2
```

## 使い方
```
python diff.py -url https://ja.wikipedia.org/wiki/記事名 -user ユーザー名
```

結果がhtmlファイルとして出力されます。

## 結果
結果は差分のみが表示されます。赤字(-)は削除された部分、緑字(+)は追加された部分です。

## 免責事項
細かい動作確認はしていません。このスクリプトを使用したことによる如何なる損害に対しても作者は責任を負いません。
