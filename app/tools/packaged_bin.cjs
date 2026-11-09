'use strict';
// Prints the path of the unpacked packaged executable for the current OS (used by CI E2E).
const fs=require('node:fs');const path=require('node:path');
const pkg=require('../package.json');const dist=path.join(__dirname,'..','dist');
const exe=pkg.build.win?.executableName||pkg.build.linux?.executableName||pkg.name;
function macBins(){
  const out=[];
  for(const d of ['mac-arm64','mac','mac-universal']){
    const dir=path.join(dist,d);if(!fs.existsSync(dir))continue;
    for(const app of fs.readdirSync(dir).filter(f=>f.endsWith('.app'))){
      const macos=path.join(dir,app,'Contents','MacOS');
      if(fs.existsSync(macos))for(const f of fs.readdirSync(macos))out.push(path.join(macos,f));
    }
  }
  // prefer the native architecture build
  return out.sort((a,b)=>(b.includes(process.arch==='arm64'?'mac-arm64':'/mac/')?1:0)-(a.includes(process.arch==='arm64'?'mac-arm64':'/mac/')?1:0));
}
const candidates={
  linux:[path.join(dist,'linux-unpacked',exe)],
  win32:[path.join(dist,'win-unpacked',exe+'.exe'),path.join(dist,'win-unpacked',pkg.build.productName+'.exe')],
  darwin:macBins()
}[process.platform]||[];
const hit=candidates.find(f=>fs.existsSync(f));
if(!hit){console.error('packaged executable not found; tried:\n'+(candidates.join('\n')||'(no .app bundles under dist/)'));process.exit(1);}
process.stdout.write(hit);
