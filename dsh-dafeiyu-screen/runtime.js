import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const exec=promisify(execFile),root=dirname(fileURLToPath(import.meta.url));
let pending;
export async function ensurePython() {
  if (process.platform!=='win32') throw new Error('此插件需要 Windows 10/11 x64');
  if (!pending) pending=exec('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',join(root,'scripts','dependencies.ps1'),'-Component','Python'],{windowsHide:true,timeout:600000,maxBuffer:1024*1024}).then(({stdout})=>{
    const line=stdout.trim().split(/\r?\n/).at(-1),result=JSON.parse(line);
    if (!result.python) throw new Error('Python 路径不可用');
    return result.python;
  }).catch(e=>{pending=null;throw new Error(`Python 准备失败，请检查网络后重试或运行依赖安装脚本：${e.message.slice(0,300)}`);});
  return pending;
}
