window.__ModuleLoader__.load({
  id:'dsh-dafeiyu-screen',
  factory(require) {
    const React=require('react'), h=React.createElement;
    return {
      inject:['slots','locale'],
      apply(ctx) {
        const ns='dafeiyu-screen';
        ctx.effect(()=>ctx.locale.register(ns,{zh:{title:'大肥鱼展域屏',open:'打开独立控制台',hint:'连接 USB 的 Windows 电脑提供控制台。',frame:'屏幕显示与余额设置'},en:{title:'DaFeiYu Screen',open:'Open control panel',hint:'The control panel runs on the Windows host connected to USB.',frame:'Screen and balance settings'}}));
        const t=ctx.locale.bind(ns);
        function Panel() {
          const embed=['http:','https:'].includes(window.location.protocol)&&['127.0.0.1','localhost'].includes(window.location.hostname);
          return h('section',null,
            h('p',null,t('hint'),' ',h('a',{href:'http://127.0.0.1:18432/',target:'_blank',rel:'noreferrer'},t('open'))),
            embed?h('iframe',{src:'http://127.0.0.1:18432/',title:t('frame'),style:{width:'100%',height:850,border:0,borderRadius:16}}):null);
        }
        ctx.slots.inject('plugins.bundle.config',()=>ctx.slots.register({name:'plugins.bundle.config',id:'dsh-dafeiyu-screen',label:()=>t('title'),locale:ns},Panel));
      }
    };
  }
});
