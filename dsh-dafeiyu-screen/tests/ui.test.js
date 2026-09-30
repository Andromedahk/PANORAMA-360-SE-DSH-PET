import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';

test('web controls submit presets and custom intervals, and reject invalid input',async()=>{
  const elements=new Map(),posts=[];
  const make=()=>({value:'30',checked:true,classList:{toggle(){}},setAttribute(){},reportValidity(){return Number.isInteger(Number(this.value))&&this.value>=10&&this.value<=3600;}});
  const element=id=>{if(!elements.has(id))elements.set(id,make());return elements.get(id);};
  const presets=[10,30,60,300].map(seconds=>({...make(),dataset:{seconds:String(seconds)}}));
  let settings={pollSeconds:30,autoStart:true};
  const snapshot=()=>({value:null,screen:{},settings,busy:false,mode:'dsh',source:'test',nextRefreshAt:null});
  const context={document:{getElementById:element,querySelector:()=>({content:'token'}),querySelectorAll:s=>s==='[data-seconds]'?presets:[]},setTimeout:()=>1,clearTimeout(){},Date,fetch:async(url,options)=>{
    if(options.method==='POST'){const data=JSON.parse(options.body);posts.push({url,data});settings=data;}
    return {ok:true,json:async()=>snapshot()};
  }};
  runInNewContext(await readFile(new URL('../ui.js',import.meta.url),'utf8'),context);
  const settle=()=>new Promise(resolve=>setImmediate(resolve));
  await settle();presets[2].onclick();await settle();
  assert.equal(posts.at(-1).data.pollSeconds,60);
  element('interval').value='45';await element('save').onclick();
  assert.equal(posts.at(-1).data.pollSeconds,45);
  element('interval').value='9';await element('save').onclick();assert.equal(posts.length,2);
});
