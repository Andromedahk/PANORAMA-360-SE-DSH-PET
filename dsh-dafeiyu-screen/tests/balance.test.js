import test from 'node:test';
import assert from 'node:assert/strict';
import {money,parseBalance,accountCredential} from '../balance.js';
import {validateSettings} from '../service.js';

test('decimal wallets sum before rounding; credit and negative balances',()=>{
  assert.equal(money(['0.1','0.2']),'0.30');
  assert.equal(money(['0.004','0.004']),'0.01');
  assert.equal(money(['-1.005']),'-1.01');
  assert.equal(money(['100','-0.009']),'99.99');
  for (const bad of ['NaN','Infinity','123fake','1e999',null]) assert.throws(()=>money([bad]));
});
test('DSH recharge plus bonus; no currency mixing',()=>{
  const data={code:0,data:{biz_code:0,biz_data:{normal_wallets:[{currency:'CNY',balance:'12.345'},{currency:'USD',balance:'999'}],bonus_wallets:[{currency:'CNY',balance:'0.005'}]}}};
  assert.equal(parseBalance(data,true),'12.35');
  assert.equal(parseBalance({balance_infos:[{currency:'CNY',total_balance:'0.00'}]},false),'0.00');
  assert.throws(()=>parseBalance({code:40003,data:{}},true));
  assert.throws(()=>parseBalance({balance_infos:[{currency:'USD',total_balance:'3'}]},false));
  assert.throws(()=>parseBalance({normal_wallets:[]},true));
});
test('stored token sent only to a validated official HTTPS issuer',()=>{
  assert.equal(accountCredential({issuer:'https://platform.deepseek.com',token:'test-only'}).endpoint,'https://platform.deepseek.com/api/v0/users/get_user_summary');
  for(const issuer of ['http://platform.deepseek.com','https://example.com','https://platform.deepseek.com.evil.test','https://u@platform.deepseek.com','https://platform.deepseek.com/a','https://platform.deepseek.com:44'])assert.equal(accountCredential({issuer,token:'test-only'}),null);
});
test('poll settings bounded and explicit',()=>{
  assert.deepEqual(validateSettings({pollSeconds:30,autoStart:true}),{pollSeconds:30,autoStart:true});
  for(const pollSeconds of [0,9,3601,1.5,'abc'])assert.throws(()=>validateSettings({pollSeconds,autoStart:false}));
});
