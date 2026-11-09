'use strict';
// Prints the path of the unpacked packaged executable for the current OS (used by CI E2E).
const fs=require('node:fs');const path=require('node:path');
const pkg=require('../package.json');const dist=path.join(__dirname,'..','dist');
const name=pkg.build.productName;const exe=pkg.build.executableName;
const candidates={
  linux:[path.join(dist,'linux-unpacked',exe)],
  win32:[path.join(dist,'win-unpacked',exe+'.exe'),path.join(dist,'win-unpacked',name+'.exe')],
  darwin:['mac-arm64','mac','mac-universal'].map(d=>path.join(dist,d,name+'.app','Contents','MacOS',name))
}[process.platform]||[];
const hit=candidates.find(f=>fs.existsSync(f));
if(!hit){console.error('packaged executable not found; tried:\n'+candidates.join('\n'));process.exit(1);}
process.stdout.write(hit);
