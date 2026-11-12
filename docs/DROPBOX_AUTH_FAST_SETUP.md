# Dropbox OAuth 自動登録（数学研究用 GitHub）

数学研究リポジトリ csta24055-sys/- の **main** ブランチに追加した認証処理です。
iPhoneのショートカット不要。認証コードを Dropbox API で交換し、
Dropbox実書き込み・Dropbox content_hash照合に成功後、
取得した refresh_token を暗号化して GitHub Actions Secret に自動登録します。
認証コード・トークンそのものはログ、Gitコミット、GitHub Artifactへ出しません。

## 最初に一回だけ準備する

GitHub Actions Secrets: https://github.com/csta24055-sys/-/settings/secrets/actions

- DROPBOX_APP_KEY — 使用するDropbox既存アプリのApp key
- DROPBOX_APP_SECRET — 同じアプリのApp secret
- GH_SECRETS_TOKEN — GitHub fine-grained Personal Access Token。
  https://github.com/settings/personal-access-tokens/new で生成。
  Repository access: Only select repositories -> csta24055-sys/- だけ選択。
  Repository permissions: Secrets -> Read and write。
  それ以外の権限は追加しない。短期有効期限が推奨。
  このトークンを「GitHub Actions Secret」の値へ直接登録する。
  （既定の GITHUB_TOKEN はリポジトリSecretsの作成・更新ができません。）

## 事前チェック（コード失効を防ぐため先に行う）

https://github.com/csta24055-sys/-/actions/workflows/dropbox-auth.yml

Actions > Dropbox OAuth auto-registration > Run workflow で
branch: main / mode: preflight を選択し実行する。
エラーがなく「Preflight OK」で完了したことを確認する。
ただしトークンのWRITE権限は exchange 実行時に初めて検証される。

## そのあと認証コードを取る

DropboxアプリのApp keyで APP_KEY を置き換えて、ブラウザで開く：

https://www.dropbox.com/oauth2/authorize?client_id=APP_KEY&response_type=code&token_access_type=offline

Dropboxで「許可」を押し、認証コードを取得する。
この認証コードは短時間で失効し、使用できるのは一回きり。
必ず新しいコードを発行する。以前のコードを使い回さない。

GitHub Secretsの「New repository secret」から
DROPBOX_AUTH_CODE にその認証コードを登録する。

## 直ちに交換・自動保存

Actions > Dropbox OAuth auto-registration > Run workflow
branch: main / mode: exchange を選択して実行する。

成功時に:
- Dropbox /GitHubActions/auth-check-RUN-ATTEMPT.txt が保存され、
  サイズとハッシュが一致することを検証する。
- 新しい DROPBOX_REFRESH_TOKEN が GitHub Secrets に自動保存される。

成功後、不要な一時Secrets DROPBOX_AUTH_CODE と GH_SECRETS_TOKEN を削除する。
（後者のGitHub Personal Access Tokenも失効可能。）
残す3つのSecrets:
DROPBOX_APP_KEY / DROPBOX_APP_SECRET / DROPBOX_REFRESH_TOKEN

注意: 認証コードやApp secret、GitHubトークンをChatGPTの会話、Issueや公開ファイルに貼らない。

## 既存の数学研究システムとの関係

この認証ワークフローは main に追加され、ほかの数学計算ワークフローは変更しません。
Dropboxへの実計算結果自動転送版は claude/dropbox-artifact-free ブランチにあります。
認証成功後、そのブランチの dropbox-smoke-test.yml を再実行して接続確認し、
数学ワークフローを main に統合する工程が別途必要です。
