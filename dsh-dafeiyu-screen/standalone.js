import { spawn } from 'node:child_process';
import { ScreenService,serve,PORT } from './service.js';

const open=()=>spawn('rundll32.exe',['url.dll,FileProtocolHandler',`http://127.0.0.1:${PORT}/`],{windowsHide:true,stdio:'ignore'}).unref();
const service=new ScreenService();
await service.init();
let server;
async function close(){server?.close();server?.closeAllConnections();await service.dispose();process.exit(0);}
try {
  server=await serve(service,{onExit:close});
  process.on('SIGINT',close);process.on('SIGTERM',close);
  if (!process.argv.includes('--no-open')) open();
  if (service.settings.autoStart) void service.action('start').catch(e=>{service.state.screen.error=e.message;});
  console.log(`大肥鱼控制台：http://127.0.0.1:${PORT}/`);
} catch(e) {
  await service.dispose();
  if(e.code==='EADDRINUSE') {if (!process.argv.includes('--no-open'))open();}
  else {console.error(e.message);process.exitCode=1;}
}
