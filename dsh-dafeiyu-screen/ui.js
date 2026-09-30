const $=id=>document.getElementById(id);
const token=document.querySelector('meta[name=dafeiyu-token]').content;
let loaded=false,busy=false,timer,toastTimer,closed=false;
function toast(message){$('toast').textContent=message;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').textContent='',4500);}
function paint(s){
  $('amount').textContent=s.value??'--';$('balance').textContent=s.value===null?'等待更新':`¥ ${s.value}`;
  $('source').textContent=s.source;$('updated').textContent=s.updatedAt?new Date(s.updatedAt).toLocaleString('zh-CN'):'尚未读取';
  $('error').textContent=s.screen.error||s.balanceError||'';
  $('previewTime').textContent=s.updatedAt?`${s.balanceError?'STALE':'UPDATED'} / ${new Date(s.updatedAt).toLocaleTimeString('en-GB',{hour12:false})}`:'WAITING FOR BALANCE';
  $('screenStatus').textContent=s.screen.playing?'屏幕正在显示':s.screen.error?'屏幕连接异常':'未连接屏幕';
  $('dot').classList.toggle('on',s.screen.playing);
  $('exit').hidden=s.mode==='dsh';
  $('start').textContent=s.screen.playing?'已在显示':'开始显示';
  if(!loaded){$('interval').value=s.settings.pollSeconds;$('autoStart').checked=s.settings.autoStart;loaded=true;}
  for(const b of document.querySelectorAll('button'))b.disabled=busy||s.busy;
  $('start').disabled=busy||s.busy||s.screen.playing;
}
async function api(op,data){
  const r=await fetch(`/api/${op}`,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Dafeiyu-Token':token},body:JSON.stringify(data)});
  const s=await r.json();if(!r.ok)throw new Error(s.error||'操作失败');return s;
}
async function action(op,data={},message){
  if(busy)return;busy=true;for(const b of document.querySelectorAll('button'))b.disabled=true;
  try{const s=await api(op,data);busy=false;paint(s);if(message)toast(message);}
  catch(e){toast(e.message);$('error').textContent=e.message;}
  finally{busy=false;}
}
for(const op of ['start','stop','restore','refresh','clearKey'])$(op).onclick=()=>action(op,{},({start:'动画已发送到屏幕，余额将自动更新',stop:'已释放连接；屏幕后续显示取决于待机设置',restore:'已恢复原显示',clearKey:'已移除 Key，重新读取 DSH 凭证'})[op]);
$('save').onclick=()=>action('settings',{pollSeconds:Number($('interval').value),autoStart:$('autoStart').checked},'设置已保存');
$('keyForm').onsubmit=e=>{e.preventDefault();const key=$('key').value.trim();if(!key)return;$('key').value='';void action('saveKey',{key},'Key 已由 Windows 加密保存');};
$('exit').onclick=async()=>{try{await api('exit',{});closed=true;clearTimeout(timer);$('screenStatus').textContent='控制台已退出';toast('控制台已退出，可以关闭页面');for(const b of document.querySelectorAll('button'))b.disabled=true;}catch(e){toast(e.message);}};
async function poll(){if(closed)return;try{if(!busy)paint(await api('status'));}catch{$('screenStatus').textContent='控制台未连接';}finally{if(!closed)timer=setTimeout(poll,2000);}}
void poll();
