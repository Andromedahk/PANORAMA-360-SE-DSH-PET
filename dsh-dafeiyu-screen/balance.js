import { readFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { parse } from 'yaml';

// Sum decimal wallet values before rounding, without binary floating-point money.
export function money(values) {
  let total = 0n;
  for (const raw of values) {
    const text = String(raw);
    const m = /^([+-]?)(\d+)(?:\.(\d+))?$/.exec(text);
    if (!m || text.length > 60 || (m[3]?.length || 0) > 18) throw new Error('余额格式无效');
    total += (m[1] === '-' ? -1n : 1n) * BigInt(m[2] + (m[3] || '').padEnd(18, '0'));
  }
  const sign = total < 0n ? '-' : '';
  const cents = ((total < 0n ? -total : total) + 5000000000000000n) / 10000000000000000n;
  const result = `${sign}${cents / 100n}.${String(cents % 100n).padStart(2,'0')}`;
  if (result.length > 11) throw new Error('余额超出屏幕显示范围');
  return result;
}

export function walletValues(wallets, key, required = true) {
  if (!Array.isArray(wallets)) {
    if (!required && wallets === undefined) return [];
    throw new Error('余额响应缺少钱包列表');
  }
  const cny = wallets.filter(w => w?.currency === 'CNY');
  if (!cny.length && (required || wallets.length)) throw new Error('账户未返回人民币钱包');
  return cny.map(w => {
    if (typeof w[key] !== 'string' && typeof w[key] !== 'number') throw new Error('钱包金额无效');
    return w[key];
  });
}

export function parseBalance(data, account) {
  if (!account) return money(walletValues(data?.balance_infos, 'total_balance'));
  let body = data;
  for (const [code,key] of [['code','data'],['biz_code','biz_data']]) {
    if (body && (code in body || key in body)) {
      if (body[code] !== 0 || !body[key] || typeof body[key] !== 'object') throw new Error('DSH 账号认证或余额查询失败');
      body = body[key];
    }
  }
  return money([...walletValues(body?.normal_wallets,'balance'), ...walletValues(body?.bonus_wallets,'balance',false)]);
}

function validToken(t) { return typeof t === 'string' && /^[\x21-\x7e]{1,16384}$/.test(t); }
export function accountCredential(payload) {
  if (!payload || !validToken(payload.token) || typeof payload.issuer !== 'string') return null;
  let url;
  try { url = new URL(payload.issuer); } catch { return null; }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || !['platform.deepseek.com','api.deepseek.com'].includes(url.hostname) || !['','/'].includes(url.pathname) || url.port) return null;
  return { token:payload.token, account:true, endpoint:`${url.origin}/api/v0/users/get_user_summary`, source:'DSH 登录账号' };
}

export async function resolveLocalCredential(savedKey) {
  if (validToken(savedKey)) return {token:savedKey,account:false,endpoint:'https://api.deepseek.com/user/balance',source:'已保存的 API Key'};
  const env = process.env.DAFEIYU_API_KEY || process.env.DSHPET_KEY || process.env.DEEPSEEK_API_KEY;
  if (validToken(env)) return {token:env,account:false,endpoint:'https://api.deepseek.com/user/balance',source:'环境变量 API Key'};
  let doc;
  try {
    const raw = await readFile(join(process.env.DSH_HOME || join(homedir(),'.dsh'),'.credentials.yaml'),'utf8');
    if (raw.length > 1048576) throw new Error();
    doc = parse(raw, {maxAliasCount:0});
  } catch { return null; }
  // DSH's published v1 credential-store shape. No scanning unrelated secrets.
  if (doc?.version !== 1) return null;
  const record = doc.records?.['deepseek-account-platform/default'];
  const account = accountCredential(record?.kind === 'grant' ? record.payload : null);
  if (account) return account;
  const key = doc.refs?.DEEPSEEK_API_KEY;
  return validToken(key) ? {token:key,account:false,endpoint:'https://api.deepseek.com/user/balance',source:'DSH API Key'} : null;
}

export async function fetchBalance(credential) {
  let response;
  try {
    response = await fetch(credential.endpoint, {redirect:'error', signal:AbortSignal.timeout(15000), headers:{
      Accept:'application/json', 'User-Agent':'DSHDaFeiYuScreen/1.0',
      ...(credential.account ? {'x-dsh-auth-token':credential.token} : {Authorization:`Bearer ${credential.token}`})
    }});
  } catch { throw new Error('网络连接失败，稍后自动重试'); }
  if (response.status === 429) {
    const retry = response.headers.get('retry-after');
    const seconds = /^\d+$/.test(retry || '') ? Number(retry) : (Date.parse(retry || '') - Date.now()) / 1000;
    const e = new Error('查询过于频繁，已延长刷新间隔'); e.retrySeconds = Math.min(3600,Math.max(60,Number.isFinite(seconds)?seconds:60)); throw e;
  }
  if ([401,403].includes(response.status)) throw new Error('凭证已失效，请重新登录 DSH 或设置 API Key');
  if (!response.ok) throw new Error(`余额服务暂不可用（HTTP ${response.status}）`);
  let length = 0; const chunks = [];
  for await (const c of response.body) {
    length += c.length;
    if (length > 1048576) throw new Error('余额响应过大');
    chunks.push(c);
  }
  let data;
  try { data=JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { throw new Error('余额服务返回了无效数据'); }
  return {value:parseBalance(data,credential.account),source:credential.source};
}
