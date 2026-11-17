// 起動の最初（CSS の読み込みより前）に、保存済みのレイアウトと配色を <html> の属性に付ける。
// アプリ本体の JS が動くまでの間も、保存した配色（とくに「ダーク」固定）の背景で描かれるようにするため。
// 色のトークンは data-ui と data-theme だけで決まる（残りの属性は src/ui/UiPrefsContext.tsx が付ける）。
// 配信時の CSP が script-src 'self' なので、index.html に直接書かず外部ファイルにしている。
// 保存値がない・壊れている・未知の値のときは何も付けない（Original・端末の配色で描かれる）。例外は外へ出さない。
(function () {
  try {
    var p = JSON.parse(localStorage.getItem('aqros-ui-prefs-v1') || 'null');
    var a = p && p.version === 1 && p.applied;
    if (!a || typeof a !== 'object') return;
    var e = document.documentElement;
    if (/^(original|research|public|commercial|enterprise)$/.test(a.layout)) e.setAttribute('data-ui', a.layout);
    var t = a.custom && a.custom.theme;
    if (t === 'dark' || t === 'light') e.setAttribute('data-theme', t);
  } catch (_) { /* 保存値が読めない環境（プライベートモード等）・壊れた値: 既定のまま起動する */ }
})();
