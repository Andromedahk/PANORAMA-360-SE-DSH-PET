import { ScreenService, serve } from './service.js';
import { money, walletValues } from './balance.js';

export const name='dafeiyu-screen';

/** Real Cordis host plugin; one service lifetime, no agent/model calls. */
export async function apply(ctx) {
  const service=new ScreenService({mode:'dsh'});
  let server;
  ctx.effect(()=>async()=>{server?.close();server?.closeAllConnections();await service.dispose();});
  // Optional injection keeps a manual API Key usable in minimal profiles too.
  ctx.inject(['deepseekAccount'], accountCtx=>{
    const reader=async()=>{
      const b=await accountCtx.deepseekAccount.getBalance({version:'1.0.4',locale:'zh-CN',timezoneOffsetSeconds:-new Date().getTimezoneOffset()*60});
      if (b===null) return null;
      if (b.status!=='ready') throw new Error('DSH 余额查询失败，稍后重试');
      return {value:money([...walletValues(b.value,'balance'),...walletValues(b.bonusWallets,'balance',false)]),source:'DSH 登录账号'};
    };
    service.accountReader=reader;
    accountCtx.effect(()=>()=>{if(service.accountReader===reader)service.accountReader=null;});
  });
  await service.init();
  try {server=await serve(service);} catch(e) {await service.dispose();throw new Error(e.code==='EADDRINUSE'?'大肥鱼控制台已运行，请先退出独立控制台，再启用插件':e.message);}
  if(service.settings.autoStart) void service.action('start').catch(e=>{service.state.screen.error=e.message;});
}
